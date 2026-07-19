import { gql } from '@/graphql/generated';

/** GraphQL-операции страницы настроек компании. */

/**
 * Настройки компании.
 *
 * Отдельный запрос, хотя компания есть и в `resolverAuthMe`: страница гейтится
 * правом `Permission_org_settings_see`, и право проверяется там же, где
 * отдаются данные.
 */
export const ORG_SETTINGS_QUERY = gql(`
  query OrgSettings {
    resolverOrgSettingsGet {
      id
      name
      country
      website
      contactPhone
    }
  }
`);

/**
 * Сохранение настроек.
 *
 * Возвращает те же поля, что и запрос: Apollo обновит кэш по `id` сам, и
 * название компании в шапке поменяется без перезапроса.
 */
export const UPDATE_ORG_SETTINGS_MUTATION = gql(`
  mutation UpdateOrgSettings($input: UpdateOrgSettingsInput!) {
    resolverOrgSettingsUpdate(input: $input) {
      id
      name
      country
      website
      contactPhone
    }
  }
`);
