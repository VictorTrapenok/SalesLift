import { gql } from '@/graphql/generated';

/**
 * Все GraphQL-операции страницы входа.
 *
 * Держим отдельно от компонента (правило прототипа: index.tsx оркестрирует,
 * queries.ts содержит запросы) — так их видно все сразу.
 */
export const LOGIN_MUTATION = gql(`
  mutation Login($input: LoginInput!) {
    resolverAuthLogin(input: $input) {
      token
      user {
        id
        name
        email
      }
    }
  }
`);
