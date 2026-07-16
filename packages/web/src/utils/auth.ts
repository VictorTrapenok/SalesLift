import { BRAND } from '@/constants/brand';

/**
 * Хранение токена авторизации.
 *
 * Единственное место, которое трогает localStorage: чтобы найти всех, кто
 * работает с токеном, достаточно найти импорты этого модуля.
 *
 * Токен лежит в localStorage, а не в httpOnly-cookie. Размен осознанный:
 * Bearer-токен в заголовке не даёт CSRF и не требует настройки cookie для
 * кросс-доменных сценариев, но уязвим к XSS — скрипт на странице сможет его
 * прочитать. Для SPA без сторонних скриптов это приемлемо; при появлении
 * встраиваемых виджетов решение нужно пересматривать.
 */

const TOKEN_KEY = BRAND.tokenKey;

/** Имя события смены токена. */
export const AUTH_TOKEN_CHANGED_EVENT = 'auth:token-changed';

/**
 * Уведомляет текущую вкладку о смене токена.
 * Браузер шлёт событие `storage` только в ДРУГИЕ вкладки, поэтому своей нужно
 * сообщить отдельно.
 */
function fireTokenChanged(): void {
  window.dispatchEvent(new CustomEvent(AUTH_TOKEN_CHANGED_EVENT));
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  fireTokenChanged();
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  fireTokenChanged();
}
