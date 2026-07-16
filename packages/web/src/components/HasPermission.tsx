import type { UserPermissions } from '@/graphql/generated/graphql';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import type { JSX, ReactNode } from 'react';

/**
 * Условный рендер по правам текущего сотрудника.
 *
 * Источник истины — `effectivePermissions` из запроса Me, развёрнутые бэкендом.
 * Строковые ключи берутся из enum `UserPermissions`, который приезжает из
 * GraphQL-схемы через codegen: опечатка в праве — ошибка компиляции.
 *
 * Использовать для отдельных кнопок и контролов. Для гейтинга целых страниц —
 * проп `permission` у `ProtectedRoute` в router.tsx.
 *
 * ВАЖНО: это только UI. Скрытая кнопка не защищает данные — настоящую проверку
 * делает `require_permission` в резолвере. Здесь мы лишь не показываем то, чем
 * пользователь всё равно не сможет воспользоваться.
 *
 * Пример:
 *
 *   <HasPermission permission={UserPermissions.Permission_users_create}>
 *     <Button>Добавить сотрудника</Button>
 *   </HasPermission>
 */
interface HasPermissionProps {
  permission: UserPermissions;
  children: ReactNode;
  /** Что показать вместо детей, если права нет. По умолчанию — ничего. */
  fallback?: ReactNode;
}

export default function HasPermission({ permission, children, fallback = null }: HasPermissionProps): JSX.Element {
  const { hasPermission } = useCurrentUser();
  return <>{hasPermission(permission) ? children : fallback}</>;
}
