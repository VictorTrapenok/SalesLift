{{/*
Общие вычисления чарта. Здесь собрано всё, что иначе размножилось бы по
манифестам: имена, метки, координаты базы и ссылки на секреты.

Главное правило этого файла: значение секрета вычисляется РОВНО В ОДНОМ месте —
в secret.yaml. Поды и Job'ы ссылаются на секрет через secretKeyRef и самих
значений не видят. Иначе `randAlphaNum` отработал бы в каждом шаблоне заново и
разошёлся бы сам с собой.
*/}}

{{- define "saleslift.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "saleslift.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "saleslift.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "saleslift.labels" -}}
helm.sh/chart: {{ include "saleslift.chart" . }}
{{ include "saleslift.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "saleslift.selectorLabels" -}}
app.kubernetes.io/name: {{ include "saleslift.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Образ приложения. Пустой tag означает «версия из Chart.yaml». */}}
{{- define "saleslift.image" -}}
{{- printf "%s:%s" .Values.image.repository (default .Chart.AppVersion .Values.image.tag) }}
{{- end }}

{{/* ── Координаты базы ──────────────────────────────────────────────────── */}}

{{- define "saleslift.dbHost" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" (include "saleslift.fullname" .) -}}
{{- else -}}
{{- required "externalDatabase.host обязателен, когда postgresql.enabled=false" .Values.externalDatabase.host -}}
{{- end -}}
{{- end }}

{{- define "saleslift.dbPort" -}}
{{- if .Values.postgresql.enabled -}}5432{{- else -}}{{ .Values.externalDatabase.port }}{{- end -}}
{{- end }}

{{- define "saleslift.dbName" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.database -}}
{{- else -}}
{{- .Values.externalDatabase.database -}}
{{- end -}}
{{- end }}

{{- define "saleslift.dbUser" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.username -}}
{{- else -}}
{{- .Values.externalDatabase.username -}}
{{- end -}}
{{- end }}

{{/* ── Секреты ──────────────────────────────────────────────────────────── */}}

{{/* Secret, который создаёт сам чарт. */}}
{{- define "saleslift.secretName" -}}
{{- printf "%s-secrets" (include "saleslift.fullname" .) -}}
{{- end }}

{{- define "saleslift.dbExistingSecret" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.existingSecret -}}
{{- else -}}
{{- .Values.externalDatabase.existingSecret -}}
{{- end -}}
{{- end }}

{{- define "saleslift.dbSecretName" -}}
{{- $existing := include "saleslift.dbExistingSecret" . -}}
{{- if $existing -}}{{ $existing }}{{- else -}}{{ include "saleslift.secretName" . }}{{- end -}}
{{- end }}

{{- define "saleslift.dbSecretKey" -}}
{{- if include "saleslift.dbExistingSecret" . -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.existingSecretKey -}}
{{- else -}}
{{- .Values.externalDatabase.existingSecretKey -}}
{{- end -}}
{{- else -}}db-password{{- end -}}
{{- end }}

{{- define "saleslift.jwtSecretName" -}}
{{- if .Values.app.jwt.existingSecret -}}
{{- .Values.app.jwt.existingSecret -}}
{{- else -}}{{ include "saleslift.secretName" . }}{{- end -}}
{{- end }}

{{- define "saleslift.jwtSecretKey" -}}
{{- if .Values.app.jwt.existingSecret -}}
{{- .Values.app.jwt.existingSecretKey -}}
{{- else -}}jwt-secret{{- end -}}
{{- end }}

{{/*
Значение секрета: заданное вручную → уже сохранённое в кластере → новое.

Чтение из кластера через `lookup` — не украшение, а обязательное условие:
без него каждый `helm upgrade` генерировал бы новый JWT-секрет и разлогинивал
всех сотрудников, а новый пароль БД просто не совпал бы с тем, с которым
PostgreSQL инициализировалась. При `helm template` и `--dry-run` кластера нет,
lookup вернёт пусто и в выводе окажется случайное значение — это нормально,
оно никуда не применяется.

Вызывать ТОЛЬКО из secret.yaml.
*/}}
{{- define "saleslift.resolveSecret" -}}
{{- $existing := lookup "v1" "Secret" .root.Release.Namespace (include "saleslift.secretName" .root) -}}
{{- $stored := "" -}}
{{- if and $existing $existing.data -}}
{{- $stored = index $existing.data .key | default "" -}}
{{- end -}}
{{- if .value -}}
{{- .value -}}
{{- else if $stored -}}
{{- $stored | b64dec -}}
{{- else -}}
{{- randAlphaNum .length -}}
{{- end -}}
{{- end }}

{{/* ── Общее для подов приложения ───────────────────────────────────────── */}}

{{/*
Ожидание базы перед стартом. Приложение не переживает недоступную базу
изящно, а k8s перезапустит упавший под с нарастающей задержкой — проще
подождать здесь, чем читать CrashLoopBackOff при каждой установке.
*/}}
{{- define "saleslift.waitForDatabase" -}}
- name: wait-for-db
  image: {{ include "saleslift.image" . }}
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  command:
    - python
    - -c
    - |
      import os, socket, sys, time
      host, port = os.environ["DB_HOST"], int(os.environ["DB_PORT"])
      deadline = time.monotonic() + {{ .Values.waitForDatabaseTimeout }}
      while time.monotonic() < deadline:
          try:
              socket.create_connection((host, port), timeout=3).close()
              print(f"База {host}:{port} принимает соединения")
              sys.exit(0)
          except OSError as err:
              print(f"Жду базу {host}:{port}: {err}")
              time.sleep(2)
      sys.exit(f"База {host}:{port} не ответила за {{ .Values.waitForDatabaseTimeout }} с")
  env:
    - name: DB_HOST
      value: {{ include "saleslift.dbHost" . | quote }}
    - name: DB_PORT
      value: {{ include "saleslift.dbPort" . | quote }}
  securityContext:
    {{- include "saleslift.containerSecurityContext" . | nindent 4 }}
{{- end }}

{{/*
Переменные окружения приложения. Несекретное приходит из ConfigMap через
envFrom, пароли — поimённо через secretKeyRef: так работает и подставленный
снаружи Secret с произвольными именами ключей.
*/}}
{{- define "saleslift.appEnv" -}}
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "saleslift.dbSecretName" . }}
      key: {{ include "saleslift.dbSecretKey" . }}
- name: JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "saleslift.jwtSecretName" . }}
      key: {{ include "saleslift.jwtSecretKey" . }}
{{- with .Values.extraEnv }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{- define "saleslift.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
