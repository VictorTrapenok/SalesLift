import { gql } from '@/graphql/generated';
import type { MeQuery } from '@/graphql/generated/graphql';
import { UserPermissions } from '@/graphql/generated/graphql';
import { getToken } from '@/utils/auth';
import { useQuery } from '@apollo/client';

/**
 * Запрос профиля текущего сотрудника.
 *
 * Права приходят в `effectivePermissions` уже развёрнутыми: роль разворачивает
 * бэкенд. Фронтенд только проверяет вхождение — дублировать логику ролей на
 * клиенте нельзя, она неизбежно разъедется с сервером.
 */
export const ME_QUERY = gql(`
  query Me {
    resolverAuthMe {
      id
      name
      email
      bio
      locale
      permissions
      effectivePermissions
      tenant {
        id
        name
      }
    }
  }
`);

/** Профиль текущего сотрудника. Тип выведен из GraphQL-схемы. */
export type CurrentUser = MeQuery['resolverAuthMe'];

interface UseCurrentUserResult {
  /** Профиль или null, если не авторизован либо ещё грузится */
  currentUser: CurrentUser | null;
  /** Проверка конкретного разрешения */
  hasPermission: (permission: UserPermissions) => boolean;
  isAdmin: boolean;
  loading: boolean;
}

/**
 * Профиль текущего сотрудника и проверка его прав.
 *
 * Запрос кэшируется Apollo, поэтому вызывать хук в разных компонентах дёшево:
 * сетевого запроса на каждый вызов не будет.
 */
export function useCurrentUser(): UseCurrentUserResult {
  const hasToken = getToken() !== null;
  const { data, loading } = useQuery(ME_QUERY, {
    // Без токена запрос гарантированно вернёт UNAUTHENTICATED — не шлём его.
    skip: !hasToken,
  });

  const currentUser = data?.resolverAuthMe ?? null;
  const permissions = new Set<UserPermissions>(currentUser?.effectivePermissions ?? []);

  return {
    currentUser,
    hasPermission: (permission: UserPermissions): boolean => permissions.has(permission),
    isAdmin: permissions.has(UserPermissions.Admin),
    loading: hasToken ? loading : false,
  };
}
