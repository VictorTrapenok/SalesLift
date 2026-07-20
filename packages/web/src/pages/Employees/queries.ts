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
 * Смена роли сотрудника.
 *
 * Возвращает те же поля, что и список: Apollo обновит запись в кэше по `id`,
 * и таблица перерисуется без перезапроса.
 */
export const CHANGE_ROLE_MUTATION = gql(`
  mutation ChangeRole($input: ChangeRoleInput!) {
    resolverUsersChangeRole(input: $input) {
      id
      name
      email
      role
      status
      lastLoginAt
    }
  }
`);

/** Отключение или включение сотрудника. Поля ответа — как у списка. */
export const SET_STATUS_MUTATION = gql(`
  mutation SetUserStatus($input: SetStatusInput!) {
    resolverUsersSetStatus(input: $input) {
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
 * Удаление сотрудника.
 *
 * Возвращает лишь `id`: строка мягко удалена и из списка исчезнет, поэтому
 * обновлять её поля в кэше незачем — мутация вызывается с `refetchQueries`.
 */
export const DELETE_EMPLOYEE_MUTATION = gql(`
  mutation DeleteEmployee($input: DeleteEmployeeInput!) {
    resolverUsersDelete(input: $input) {
      id
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
