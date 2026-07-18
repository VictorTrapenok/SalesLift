import { gql } from '@/graphql/generated';

/** GraphQL-операции страницы профиля. */

/**
 * Сохранение профиля.
 *
 * Возвращает те же поля, что запрашивает `ME_QUERY` из `useCurrentUser`:
 * Apollo обновит кэш по `id`, и имя в шапке поменяется без перезапроса.
 */
export const UPDATE_PROFILE_MUTATION = gql(`
  mutation UpdateProfile($input: UpdateProfileInput!) {
    resolverProfileUpdate(input: $input) {
      id
      name
      email
      bio
      locale
    }
  }
`);

/**
 * Смена собственного пароля.
 *
 * Возвращает профиль, а не флаг: у всех мутаций один тип ответа, и клиенту не
 * нужен особый случай.
 */
export const CHANGE_PASSWORD_MUTATION = gql(`
  mutation ChangePassword($input: ChangePasswordInput!) {
    resolverProfileChangePassword(input: $input) {
      id
    }
  }
`);
