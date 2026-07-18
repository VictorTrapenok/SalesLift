/**
 * Базовые роли для показа и выбора в интерфейсе.
 *
 * Роль приходит с бэкенда полем `role` типа `User` — строкой, а не enum'ом:
 * enum в схеме только у прав (`UserPermissions`). Поэтому список ролей здесь
 * задан руками, а не сгенерирован; расхождение с `USER_ROLE_NAMES` на бэкенде
 * ловится тем, что неизвестную роль он отвергает с `users.invalidRole`.
 *
 * ВАЖНО: роль — только для показа. Гейтить UI по ней нельзя, для этого есть
 * `HasPermission` и `effectivePermissions`.
 */
export const ROLE_NAMES = ['admin', 'manager', 'viewer'] as const;

export type RoleName = (typeof ROLE_NAMES)[number];

/**
 * Подписи ролей.
 *
 * Ключи записаны целиком, а не собраны из фрагментов (`employees.role${role}`):
 * собранный ключ не находится грепом и теряется при рефакторинге.
 */
export const ROLE_LABEL_KEYS: Record<RoleName, string> = {
  admin: 'employees.roleAdmin',
  manager: 'employees.roleManager',
  viewer: 'employees.roleViewer',
};

/** Подпись роли по строке с бэкенда. Неизвестная роль показывается как есть. */
export function roleLabelKey(role: string): string | null {
  return role in ROLE_LABEL_KEYS ? ROLE_LABEL_KEYS[role as RoleName] : null;
}
