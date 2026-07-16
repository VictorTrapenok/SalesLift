import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import enUS from './locales/en-US';
import ruRU from './locales/ru-RU';

/**
 * Инициализация i18n.
 *
 * Подробности и подводные камни — в readme.md рядом. Коротко: ключи плоские,
 * поэтому keySeparator и nsSeparator ОБЯЗАНЫ быть выключены.
 */

/** Полные теги локалей, которые понимает интерфейс. */
export const SUPPORTED_LOCALES = ['en-US', 'ru-RU'] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: AppLocale = 'en-US';

/** Ключ выбранного языка в localStorage. */
const LOCALE_STORAGE_KEY = 'saleslift_locale';

/**
 * Приводит двухбуквенный код бэкенда (`ru`) к полному тегу интерфейса (`ru-RU`).
 * Бэкенд оперирует ISO 639-1, фронтенд — полными тегами (их требует AntD);
 * это единственное место, где стыкуются две системы.
 */
export function toAppLocale(shortCode: string | null | undefined): AppLocale {
  const found = SUPPORTED_LOCALES.find((locale) => locale.startsWith((shortCode ?? '').slice(0, 2).toLowerCase()));
  return found ?? DEFAULT_LOCALE;
}

/** Обратное преобразование: `ru-RU` → `ru`. Такой код ждёт бэкенд. */
export function toBackendLocale(appLocale: string): string {
  return appLocale.slice(0, 2).toLowerCase();
}

/** Определяет язык: сохранённый выбор → язык браузера → английский. */
function detectLocale(): AppLocale {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored && (SUPPORTED_LOCALES as readonly string[]).includes(stored)) {
    return stored as AppLocale;
  }
  return toAppLocale(navigator.language);
}

/** Меняет язык интерфейса и запоминает выбор. */
export async function changeLocale(locale: AppLocale): Promise<void> {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  await i18n.changeLanguage(locale);
}

void i18n.use(initReactI18next).init({
  resources: {
    'en-US': { translation: enUS },
    'ru-RU': { translation: ruRU },
  },
  lng: detectLocale(),
  fallbackLng: DEFAULT_LOCALE,
  interpolation: {
    // React экранирует сам; двойное экранирование ломает текст с кавычками.
    escapeValue: false,
  },
  // ВАЖНО: обе настройки обязательны и неочевидны.
  // По умолчанию i18next читает точку как разделитель вложенности, а
  // двоеточие — как namespace. Наши ключи плоские и dot-namespaced
  // ('auth.login.title'), поэтому с включёнными разделителями i18next искал бы
  // вложенный объект auth → login → title, не находил и МОЛЧА возвращал бы саму
  // строку ключа. Симптом: в интерфейсе вместо текста видны ключи.
  keySeparator: false,
  nsSeparator: false,
});

export default i18n;
