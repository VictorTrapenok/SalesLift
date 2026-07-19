import { gql } from '@/graphql/generated';

/** GraphQL-операции страницы сотрудников. */

/**
 * Список сотрудников компании.
 *
 * Компания не передаётся параметром: бэкенд берёт её из токена. Параметр
 * tenantId был бы дырой в изоляции тенантов.
 */
export const EMPLOYEES_QUERY = gql(`
  query Employees {
    resolverUsersList {
      id
      name
      email
      role
      status
      lastLoginAt
    }
  }
`);

/**
 * Заведение сотрудника.
 *
 * Набор полей ответа совпадает с EMPLOYEES_QUERY — иначе Apollo не сможет
 * дописать новую запись в кэш списка и таблица не обновится без перезапроса.
 */
export const CREATE_EMPLOYEE_MUTATION = gql(`
  mutation CreateEmployee($input: CreateEmployeeInput!) {
    resolverUsersCreate(input: $input) {
      id
      name
      email
      role
      status
      lastLoginAt
    }
  }
`);
