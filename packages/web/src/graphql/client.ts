import { clearToken, getToken } from '@/utils/auth';
import { ApolloClient, ApolloLink, InMemoryCache, createHttpLink } from '@apollo/client';
import { onError } from '@apollo/client/link/error';

/**
 * Apollo-клиент.
 *
 * Порядок звеньев важен: errorLink должен стоять ПЕРЕД authLink, иначе он не
 * увидит ошибки запросов, которые authLink уже отправил.
 */

/** Операции авторизации сами показывают ошибки в форме — разлогинивать по ним нельзя. */
const AUTH_OPERATIONS = new Set(['Login', 'Register']);

/**
 * Разлогинивает при UNAUTHENTICATED от любого защищённого запроса.
 *
 * Защита от гонки: если за время полёта запроса токен успели заменить (вошли
 * заново в другой вкладке), ошибка относится к УЖЕ устаревшему запросу.
 * Разлогинивать по ней нельзя — это стёрло бы только что полученный рабочий
 * токен. Поэтому сравниваем токен из контекста запроса с текущим.
 */
const errorLink = onError(({ graphQLErrors, networkError, operation }) => {
  // Правило проекта: каждая ошибка логируется, пустых catch не бывает.
  if (networkError) {
    console.error('Сетевая ошибка GraphQL', { operation: operation.operationName, error: networkError });
    return;
  }
  if (!graphQLErrors) return;

  for (const err of graphQLErrors) {
    console.error('Ошибка GraphQL', {
      operation: operation.operationName,
      message: err.message,
      code: err.extensions?.code,
    });
  }

  if (AUTH_OPERATIONS.has(operation.operationName)) return;

  const currentToken = getToken();
  // Токена нет — пользователь вышел сам, редирект не нужен.
  if (!currentToken) return;

  const { requestedWithToken } = operation.getContext() as { requestedWithToken?: string | null };
  if (requestedWithToken !== currentToken) return;

  const hasUnauthenticated = graphQLErrors.some((err) => err.extensions?.code === 'UNAUTHENTICATED');
  if (hasUnauthenticated) {
    clearToken();
    window.location.assign('/login');
  }
});

/**
 * Подставляет Bearer-токен и запоминает, с каким токеном ушёл запрос
 * (см. защиту от гонки в errorLink выше).
 */
const authLink = new ApolloLink((operation, forward) => {
  const token = getToken();
  operation.setContext({
    headers: token ? { authorization: `Bearer ${token}` } : {},
    requestedWithToken: token,
  });
  return forward(operation);
});

/**
 * Относительный URL: бэкенд раздаёт SPA сам, поэтому запросы идут с того же
 * origin и CORS не нужен. В разработке тот же путь проксирует Vite.
 */
const httpLink = createHttpLink({ uri: '/api/v1/graphql' });

export const apolloClient = new ApolloClient({
  link: ApolloLink.from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache(),
});
