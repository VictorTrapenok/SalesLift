# Helm-чарт SalesLift

Разворачивает продукт в Kubernetes или k3s: под с HTTP, под фоновых задач,
миграции и — по желанию — встроенную PostgreSQL.

```bash
helm install saleslift oci://ghcr.io/victortrapenok/charts/saleslift \
  --namespace saleslift --create-namespace \
  --set ingress.host=saleslift.example.com
```

Больше ничего задавать не нужно: база поднимется внутри кластера, а JWT-секрет
и пароль к ней чарт сгенерирует сам. Полный список параметров — в
[values.yaml](values.yaml), там каждый прокомментирован.

## Что разворачивается

| Объект                     | Зачем                                                       |
| -------------------------- | ----------------------------------------------------------- |
| Deployment `-web`          | HTTP: GraphQL, REST и раздача интерфейса (`APP_MODE=web`)   |
| Deployment `-worker`       | Фоновые задачи, HTTP не слушает (`APP_MODE=worker`)          |
| Job `-migrate`             | `alembic upgrade head` одним запуском                        |
| StatefulSet `-postgresql`  | Встроенная база, если `postgresql.enabled=true`              |
| Service, Ingress           | Вход снаружи                                                 |
| ConfigMap, Secret          | Окружение приложения                                         |

Образ один на всё — и на web, и на worker, и на миграции. Отличается только
`APP_MODE` и команда: подробнее про режимы — в
[ARCHITECTURE.md](../../../ARCHITECTURE.md).

## Когда накатываются миграции

Job — хук Helm с расписанием `post-install,pre-upgrade`, и обе половины важны:

- **при установке** — только `post-install`: пока Helm не создал StatefulSet,
  базы, к которой можно подключиться, ещё не существует;
- **при обновлении** — `pre-upgrade`, то есть схема накатывается до того, как
  поедет новая версия кода. Так можно потому, что миграции у нас обязаны быть
  совместимы с предыдущей версией кода на один релиз
  ([правило expand-contract](../../../packages/api/src/saleslift/migrations/readme.md)):
  в промежутке между миграцией и выкатом старые поды продолжают работать.

Отсюда единственное известное следствие: **при самой первой установке** web-под
поднимется на несколько секунд раньше, чем появятся таблицы, и в этот
промежуток ответит ошибками. Дальше самолечится; на обновления не влияет.

Миграции — отдельный Job, а не initContainer подов, намеренно: initContainer
выполняется в каждой реплике, и при `web.replicaCount > 1` они бы мигрировали
параллельно и блокировали друг друга на DDL-локах. Ровно та же причина, по
которой в [compose.yaml](../../../compose.yaml) миграции вынесены в отдельный
одноразовый сервис.

Выключается через `migrations.enabled=false` — если схему вы катите своим
конвейером.

## Секреты

JWT-секрет и пароль к встроенной базе генерируются при установке и сохраняются
в Secret `<релиз>-secrets`. При обновлении чарт **читает уже сохранённые
значения из кластера и подставляет их обратно** — иначе каждый `helm upgrade`
менял бы JWT-секрет и разлогинивал всех сотрудников, а новый пароль просто не
совпал бы с тем, с которым PostgreSQL инициализировалась.

Из этого следуют две вещи, о которых стоит знать заранее:

- **Secret переживает `helm uninstall`** (`helm.sh/resource-policy: keep`).
  Диск встроенной базы — это PVC из `volumeClaimTemplate`, а такие PVC
  Kubernetes при удалении StatefulSet не трогает. Удались вместе с релизом ещё
  и пароль — повторная установка сгенерировала бы новый и не смогла бы войти в
  сохранившуюся базу. Убирается вручную, вместе с PVC.
- **`helm template` и `--dry-run` показывают случайные значения.** Кластера в
  этот момент нет, читать сохранённое неоткуда. В реальной установке значения
  другие.

Своё вместо сгенерированного:

```bash
--set app.jwt.secret="$(openssl rand -hex 32)"
```

Готовый Secret (sealed-secrets, external-secrets и подобное) — через
`app.jwt.existingSecret` и `postgresql.auth.existingSecret`. Если заданы оба,
собственный Secret чарт не создаёт вовсе.

Приложение стартует с `APP_ENV=production`, а в этом режиме оно само
отказывается подниматься с дефолтными секретами — см. `_check_production_secrets`
в [settings.py](../../../packages/api/src/saleslift/config/settings.py). То есть
`--set postgresql.auth.password=saleslift` не «сработает потише», а уронит под с
понятной ошибкой в логе.

## Промышленная эксплуатация

Встроенная PostgreSQL — это одна реплика с диском. Ни резервных копий, ни
реплик, ни отработки отказа в ней нет и не планируется: она существует, чтобы
продукт заработал сразу после установки. Под нагрузку берите управляемую базу:

```bash
helm install saleslift oci://ghcr.io/victortrapenok/charts/saleslift \
  --namespace saleslift --create-namespace \
  --set ingress.host=saleslift.example.com \
  --set postgresql.enabled=false \
  --set externalDatabase.host=db.example.com \
  --set externalDatabase.database=saleslift \
  --set externalDatabase.username=saleslift \
  --set externalDatabase.existingSecret=saleslift-db \
  --set externalDatabase.existingSecretKey=password
```

TLS-сертификатом чарт не занимается: он только проставляет `tls.secretName` в
Ingress. Выпуск — задача cert-manager'а, аннотации ему передаются через
`ingress.annotations`.

`worker.replicaCount` нет и не будет, пока у планировщика фоновых задач не
появится распределённая блокировка: вторая реплика взяла бы те же задачи
второй раз.

## Проверка перед выпуском

```bash
make chart-lint
```

Гоняет `helm lint` и `helm template` на обоих наборах значений из
[ci/](ci/) — «как в README» и «управляемая БД со своими секретами». Тот же шаг
идёт в CI отдельной обязательной проверкой, поэтому сломанный чарт не
доезжает до `main`.

Отдельно, разово и вне `make`, отрендеренные манифесты прогонялись через
`kubeconform -strict` против схем Kubernetes 1.30 — все объекты валидны. В CI
этой проверки нет: она требует тянуть схемы из сети на каждый прогон.

Установка на живой кластер не прогонялась — Kubernetes в среде разработки нет.
Первая настоящая установка и будет первой полной проверкой.
