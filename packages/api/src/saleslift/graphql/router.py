"""Подключение GraphQL к FastAPI."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter

from saleslift.config.settings import settings
from saleslift.db.session import get_session
from saleslift.graphql.context import Context, build_context
from saleslift.graphql.schema import schema

GRAPHQL_PATH = "/api/v1/graphql"


async def get_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> Context:
    """Собирает контекст запроса. Заголовки извлекает FastAPI."""
    return await build_context(session, authorization, accept_language)


def create_graphql_router() -> GraphQLRouter[Context, None]:
    """Создаёт GraphQL-роутер."""
    return GraphQLRouter(
        schema,
        context_getter=get_context,
        path="",  # префикс задаётся при подключении роутера
        # GraphiQL только вне production: в проде это лишняя поверхность атаки,
        # а интроспекция схемы у нас и так есть в виде закоммиченного
        # schema.graphql.
        graphql_ide="graphiql" if settings.app_env != "production" else None,
    )
