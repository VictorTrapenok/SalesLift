"""Сборка GraphQL-схемы.

Корневые Query и Mutation собираются из резолверов отдельных модулей через
наследование — это аналог `extend type Query` из schema-first подхода
прототипа: каждый модуль отвечает за свои поля, а схема их объединяет.

ВАЖНО: импорт этого модуля не должен требовать ни БД, ни прод-секретов —
`strawberry export-schema` импортирует его в Docker-сборке, где нет ни того,
ни другого. Закреплено тестом tests/unit/test_schema_export.py.
"""

import strawberry

from saleslift.graphql.errors import DomainErrorExtension
from saleslift.graphql.resolvers.auth import AuthMutation, AuthQuery
from saleslift.graphql.resolvers.health import HealthQuery


@strawberry.type(description="Корневые запросы")
class Query(HealthQuery, AuthQuery):
    """Все запросы API."""


@strawberry.type(description="Корневые мутации")
class Mutation(AuthMutation):
    """Все мутации API."""


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    # Локализация доменных ошибок. Подключается один раз здесь и действует на
    # все резолверы и гарды — забыть обёртку в отдельном резолвере невозможно.
    extensions=[DomainErrorExtension],
)
