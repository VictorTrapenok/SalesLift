import type { ApolloError } from '@apollo/client';

/**
 * Разбор ошибок бэкенда для показа в формах.
 *
 * Контракт ошибок задан на бэкенде (`graphql/errors.py`): `message` уже
 * локализован по Accept-Language, `extensions.code` — тип ошибки,
 * `extensions.field` — поле формы, если ошибка относится к конкретному инпуту.
 */

export interface ParsedGraphQLError {
  /** Готовое к показу сообщение (локализовано бэкендом) */
  message: string;
  /** Код: BAD_USER_INPUT, UNAUTHENTICATED, FORBIDDEN, NOT_FOUND */
  code?: string;
  /** Имя поля формы, к которому относится ошибка */
  field?: string;
}

/** Разбирает ошибку Apollo в структуру для формы. */
export function parseGraphQLError(error: ApolloError | undefined): ParsedGraphQLError | null {
  if (!error) return null;

  const graphQLError = error.graphQLErrors[0];
  if (!graphQLError) {
    // Сетевая ошибка: бэкенд не ответил, локализованного сообщения нет.
    return { message: error.message };
  }

  return {
    message: graphQLError.message,
    code: graphQLError.extensions?.code as string | undefined,
    field: graphQLError.extensions?.field as string | undefined,
  };
}
