"""Профиль сотрудника: то, что он меняет сам себе.

Отделено от `users_service.py` намеренно: там администратор действует над
чужими учётными записями и нужны права, здесь сотрудник действует над своей и
достаточно аутентификации. Одна функция «обнови пользователя» на оба случая
неизбежно обрастает флагом «а можно ли», и однажды его забудут передать.

Пользователь приходит сюда уже вычитанным из контекста запроса — искать его по
id не нужно и НЕЛЬЗЯ: id из аргументов резолвера позволил бы поменять чужой
профиль.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.i18n import SUPPORTED_LOCALES
from saleslift.models.user import User
from saleslift.services.auth.auth_service import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from saleslift.utils.errors import ValidationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)

#: Ограничение длины «о себе». Колонка — TEXT без лимита, поэтому это
#: единственное место, где длина проверяется.
MAX_BIO_LENGTH = 1000


class ProfileService:
    """Изменение собственного профиля и смена собственного пароля."""

    async def update_profile(
        self,
        session: AsyncSession,
        user: User,
        name: str,
        bio: str | None,
        locale: str | None,
    ) -> User:
        """Обновляет имя, «о себе» и язык серверных сообщений.

        E-mail здесь не меняется: смена адреса — это смена логина, и без
        подтверждения по почте она превращается в способ потерять доступ.
        Появится вместе с рассылкой.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("auth.nameRequired", field="name")

        # Пустая строка из формы — это «поле очистили», а не «текст из пробелов».
        clean_bio = bio.strip() if bio is not None else None
        if clean_bio is not None and len(clean_bio) > MAX_BIO_LENGTH:
            raise ValidationError("profile.bioTooLong", field="bio")

        if locale is not None:
            # Здесь, в отличие от регистрации, неизвестный язык — ошибка, а не
            # молчаливый откат на английский: пользователь выбрал его явно и
            # ждёт, что выбор применился.
            if locale not in SUPPORTED_LOCALES:
                raise ValidationError("profile.unsupportedLocale", field="locale")
            user.locale = locale

        user.name = clean_name
        user.bio = clean_bio or None

        await session.commit()

        log.info("Профиль обновлён", user_id=str(user.id))
        return user

    async def change_password(
        self,
        session: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> User:
        """Меняет пароль после проверки текущего.

        Текущий пароль спрашивается даже у вошедшего пользователя: чужая
        незаблокированная сессия иначе позволяет забрать аккаунт себе.
        """
        # password_hash пуст у сотрудника, заведённого будущим флоу
        # приглашений: пароля ещё нет, значит и «сменить» его нельзя —
        # такой пользователь проходит через установку пароля по ссылке.
        if user.password_hash is None or not verify_password(current_password, user.password_hash):
            raise ValidationError("auth.wrongCurrentPassword", field="currentPassword")

        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValidationError("auth.passwordTooShort", field="newPassword")

        user.password_hash = hash_password(new_password)
        await session.commit()

        # Выданные токены остаются валидными: инвалидации сессий пока нет —
        # см. ROADMAP.md.
        log.info("Пароль изменён", user_id=str(user.id))
        return user


#: Синглтон сервиса — как и остальные сервисы, без DI-контейнера.
profile_service = ProfileService()
