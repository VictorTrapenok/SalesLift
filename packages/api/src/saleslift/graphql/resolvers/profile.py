"""Резолверы собственного профиля сотрудника.

Права здесь не проверяются — только аутентификация: сотрудник правит свою же
учётную запись, которую резолвер берёт из контекста. Идентификатора
пользователя в аргументах нет и быть не должно.

Бизнес-логика — в `services/users/profile_service.py`.
"""

import strawberry
from strawberry.types import Info

from saleslift.graphql.context import Context
from saleslift.graphql.types.user import User
from saleslift.services.users import profile_service as profile_module
from saleslift.services.users.user_roles_permission import require_auth


@strawberry.input(description="Изменения профиля")
class UpdateProfileInput:
    """Поля формы профиля. E-mail не меняется: это логин."""

    name: str
    #: `None` — поле не трогаем, пустая строка — очистили.
    bio: str | None = None
    #: Язык серверных сообщений (ISO 639-1). `None` — оставить прежний.
    locale: str | None = None


@strawberry.input(description="Смена собственного пароля")
class ChangePasswordInput:
    """Поля формы смены пароля."""

    current_password: str
    new_password: str


@strawberry.type
class ProfileMutation:
    """Изменение собственного профиля."""

    @strawberry.mutation(description="Изменить свой профиль")
    async def resolver_profile_update(self, info: Info[Context, None], input: UpdateProfileInput) -> User:
        """Сохраняет имя, «о себе» и язык текущего сотрудника."""
        auth = require_auth(info.context)
        user = await profile_module.profile_service.update_profile(
            info.context.session,
            auth.user,
            name=input.name,
            bio=input.bio,
            locale=input.locale,
        )
        return User.from_model(user)

    @strawberry.mutation(description="Сменить свой пароль")
    async def resolver_profile_change_password(
        self,
        info: Info[Context, None],
        input: ChangePasswordInput,
    ) -> User:
        """Меняет пароль текущего сотрудника после проверки текущего.

        Возвращает профиль, а не `Boolean`: единый тип ответа у всех мутаций
        избавляет клиента от особого случая, а Apollo — от лишнего запроса
        ради обновления кэша.
        """
        auth = require_auth(info.context)
        user = await profile_module.profile_service.change_password(
            info.context.session,
            auth.user,
            current_password=input.current_password,
            new_password=input.new_password,
        )
        return User.from_model(user)
