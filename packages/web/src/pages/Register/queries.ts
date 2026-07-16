import { gql } from '@/graphql/generated';

/** GraphQL-операции страницы регистрации компании. */
export const REGISTER_MUTATION = gql(`
  mutation Register($input: RegisterInput!) {
    resolverAuthRegister(input: $input) {
      token
      user {
        id
        name
        email
        tenant {
          id
          name
        }
      }
    }
  }
`);
