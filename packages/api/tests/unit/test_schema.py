"""Проверки GraphQL-схемы: конвенция именования и экспортируемость."""

import re
import subprocess
import sys

from saleslift.graphql.schema import schema

#: Резолверы обязаны называться `resolverРезолверМетод`, чтобы их можно было
#: найти грепом по префиксу и на бэкенде (`resolver_auth_...`), и на фронтенде
#: (`resolverAuth...`). Исключение — `health`: это техническая проба, а не
#: доменный резолвер.
_FIELD_NAME_RE = re.compile(r"^(resolver[A-Z][a-zA-Z0-9]*|health)$")


def _root_field_names(type_name: str) -> list[str]:
    """Имена полей корневого типа схемы."""
    graphql_type = schema._schema.get_type(type_name)
    assert graphql_type is not None, f"в схеме нет типа {type_name}"
    return list(graphql_type.fields)  # type: ignore[attr-defined]


def test_все_поля_query_следуют_конвенции_именования() -> None:
    for name in _root_field_names("Query"):
        assert _FIELD_NAME_RE.match(name), f"поле Query.{name} нарушает конвенцию именования резолверов"


def test_все_поля_mutation_следуют_конвенции_именования() -> None:
    for name in _root_field_names("Mutation"):
        assert _FIELD_NAME_RE.match(name), f"поле Mutation.{name} нарушает конвенцию именования резолверов"


def test_префикс_resolver_переживает_camelCase() -> None:
    """Ради этого мы и не боремся с автоматическим camelCase Strawberry."""
    assert "resolverAuthLogin" in _root_field_names("Mutation")
    assert "resolverAuthRegister" in _root_field_names("Mutation")
    assert "resolverAuthMe" in _root_field_names("Query")


def test_enum_прав_попадает_в_схему() -> None:
    """Это и есть канал доставки прав на фронтенд.

    Enum уезжает в schema.graphql, а graphql-codegen превращает его в
    TypeScript-enum — отдельная синхронизация файлов не нужна.
    """
    sdl = schema.as_str()
    assert "enum UserPermissions" in sdl
    assert "Permission_users_see" in sdl


def test_пароль_не_протекает_в_схему() -> None:
    """Тип User объявлен явно, а не выведен из ORM-модели, — проверяем, что это так и осталось."""
    sdl = schema.as_str()
    assert "passwordHash" not in sdl
    assert "password_hash" not in sdl


def test_схема_экспортируется_без_бд_и_секретов() -> None:
    """Экспорт схемы обязан работать в Docker-сборке, где нет ни БД, ни секретов.

    Проверяем в отдельном процессе с чистым окружением: в текущем процессе
    настройки уже импортированы и .env.test уже подхвачен, поэтому регрессию
    «схема потянула settings, требующие прод-секретов» здесь не поймать.
    """
    result = subprocess.run(
        [sys.executable, "-c", "from saleslift.graphql.schema import schema; print(schema.as_str())"],
        capture_output=True,
        text=True,
        # Пустое окружение: ни DB_*, ни JWT_SECRET, ни APP_ENV.
        env={"PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert result.returncode == 0, f"импорт схемы упал без окружения:\n{result.stderr}"
    assert "type Query" in result.stdout
