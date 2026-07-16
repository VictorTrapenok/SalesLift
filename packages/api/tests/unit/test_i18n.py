"""Проверки локализации."""

from saleslift.i18n import (
    DEFAULT_LOCALE,
    MESSAGES,
    SUPPORTED_LOCALES,
    locale_from_accept_language,
    resolve_locale,
    t,
)


def test_наборы_ключей_всех_локалей_совпадают() -> None:
    """Главный тест этого модуля.

    Пропущенный ключ иначе всплыл бы у пользователя в виде английской строки
    посреди русского интерфейса — и только в том редком сценарии, где эта
    ошибка возникает.
    """
    reference = set(MESSAGES[DEFAULT_LOCALE])
    for locale in SUPPORTED_LOCALES:
        keys = set(MESSAGES[locale])
        assert keys == reference, (
            f"локаль {locale!r} разошлась с {DEFAULT_LOCALE!r}: "
            f"лишние={keys - reference}, недостающие={reference - keys}"
        )


def test_ни_один_перевод_не_пустой() -> None:
    for locale in SUPPORTED_LOCALES:
        for key, value in MESSAGES[locale].items():
            assert value.strip(), f"пустой перевод {locale}:{key}"


def test_resolve_locale_принимает_и_короткий_и_полный_код() -> None:
    assert resolve_locale("ru") == "ru"
    assert resolve_locale("ru-RU") == "ru"
    assert resolve_locale("RU") == "ru"
    assert resolve_locale("en-US") == "en"


def test_resolve_locale_откатывается_на_дефолт() -> None:
    """Неизвестный язык — не ошибка."""
    assert resolve_locale(None) == DEFAULT_LOCALE
    assert resolve_locale("") == DEFAULT_LOCALE
    assert resolve_locale("zz") == DEFAULT_LOCALE
    assert resolve_locale("de-DE") == DEFAULT_LOCALE


def test_accept_language_берёт_первый_язык() -> None:
    assert locale_from_accept_language("ru-RU,ru;q=0.9,en;q=0.8") == "ru"
    assert locale_from_accept_language("en-US,en;q=0.9") == "en"
    assert locale_from_accept_language(None) == DEFAULT_LOCALE


def test_t_возвращает_перевод_на_нужном_языке() -> None:
    assert t("ru", "auth.invalidCredentials") == "Неверный e-mail или пароль"
    assert t("en", "auth.invalidCredentials") == "Invalid email or password"


def test_t_не_падает_на_неизвестном_ключе() -> None:
    """В рантайме показать ключ лучше, чем уронить запрос."""
    assert t("ru", "нет.такого.ключа") == "нет.такого.ключа"


def test_t_откатывается_на_дефолтную_локаль() -> None:
    assert t("zz", "auth.forbidden") == MESSAGES[DEFAULT_LOCALE]["auth.forbidden"]
