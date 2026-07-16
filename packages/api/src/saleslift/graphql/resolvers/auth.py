"""Резолверы аутентификации.

Тонкие адаптеры: разбор входа → вызов сервиса → сборка ответа. Бизнес-логика —
в `services/auth/auth_service.py`.

Доменные ошибки НЕ обрабатываются здесь: их перехватывает и локализует
`DomainErrorExtension`, подключённое к схеме. Так работает и для ошибок из
гардов, которые в ручную обёртку никогда не попадали.

Имена резолверов начинаются с `resolver_` и в схему уезжают как
`resolverAuthRegister` (Strawberry применяет camelCase). Префикс переживает
преобразование, поэтому резолверы одинаково грепаются с обеих сторон:
`rg resolver_auth` в Python, `rg resolverAuth` в TypeScript.
"""

import strawberry
from strawberry.types import Info

from saleslift.graphql.context import Context
from saleslift.graphql.types.user import AuthPayload, User
from saleslift.services.auth import auth_service as auth_module
from saleslift.services.users.user_roles_permission import require_auth


@strawberry.input(description="Данные регистрации новой компании")
class RegisterInput:
    """Поля формы регистрации.

    Ни slug'а, ни поддомена: компания определяется по e-mail при входе.
    """

    company_name: str
    admin_name: str
    email: str
    password: str
    locale: str = "en"


@strawberry.input(description="Данные входа")
class LoginInput:
    """Поля формы входа. Компании здесь нет — она выводится из e-mail."""

    email: str
    password: str


@strawberry.type
class AuthQuery:
    """Запросы, связанные с текущей сессией."""

    @strawberry.field(description="Профиль текущего сотрудника")
    async def resolver_auth_me(self, info: Info[Context, None]) -> User:
        """Возвращает профиль вошедшего сотрудника.

        Фронтенд зовёт этот запрос при загрузке, чтобы получить профиль и
        права. Данные всегда свежие: контекст перечитывает их из БД.
        """
        auth = require_auth(info.context)
        return User.from_model(auth.user)


@strawberry.type
class AuthMutation:
    """Регистрация и вход."""

    @strawberry.mutation(description="Зарегистрировать компанию и стать её администратором")
    async def resolver_auth_register(self, info: Info[Context, None], input: RegisterInput) -> AuthPayload:
        """Создаёт компанию; зарегистрировавшийся становится администратором."""
        ctx = info.context
        result = await auth_module.auth_service.register(
            ctx.session,
            auth_module.RegisterInput(
                company_name=input.company_name,
                admin_name=input.admin_name,
                email=input.email,
                password=input.password,
                locale=input.locale,
            ),
            ctx.locale,
        )
        return AuthPayload(token=result.token, user=User.from_model(result.user))

    @strawberry.mutation(description="Войти по e-mail и паролю")
    async def resolver_auth_login(self, info: Info[Context, None], input: LoginInput) -> AuthPayload:
        """Проверяет учётные данные и выдаёт сессионный токен."""
        ctx = info.context
        result = await auth_module.auth_service.login(
            ctx.session,
            auth_module.LoginInput(email=input.email, password=input.password),
            ctx.locale,
        )
        return AuthPayload(token=result.token, user=User.from_model(result.user))
