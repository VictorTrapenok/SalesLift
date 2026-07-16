import type { CodegenConfig } from '@graphql-codegen/cli';

/**
 * Кодогенерация типов из GraphQL-схемы бэкенда.
 *
 * Это ключевой механизм проекта, а не удобство: все шаблоны gql`...` в
 * компонентах валидируются против схемы. Переименовали поле на бэкенде и
 * забыли поправить фронтенд — `npm run codegen` упадёт ДО запуска приложения,
 * а в Docker-сборке образ просто не соберётся и не уедет в registry.
 */
const config: CodegenConfig = {
  overwrite: true,
  // По умолчанию читаем SDL-ФАЙЛ, а не запущенный сервер: кодогенерация должна
  // работать в CI и в Docker-сборке, где поднимать бэкенд с базой негде.
  // Живая интроспекция при необходимости:
  //   CODEGEN_SCHEMA_URL=http://localhost:8000/api/v1/graphql npm run codegen
  schema: process.env.CODEGEN_SCHEMA_URL ?? '../api/schema.graphql',
  // Сканируем запросы прямо в компонентах — отдельные .graphql файлы не нужны.
  documents: 'src/**/*.{ts,tsx}',
  generates: {
    'src/graphql/generated/': {
      preset: 'client',
      presetConfig: {
        gqlTagName: 'gql',
        fragmentMasking: { unmaskFunctionName: 'getFragmentData' },
      },
      config: {
        // Имена значений enum'ов оставляем как в схеме. По умолчанию codegen
        // переименовал бы Permission_users_see → PermissionUsersSee, и одно и
        // то же право называлось бы по-разному в Python и в TypeScript —
        // грепом такую пару не найти. Значения совпадали бы, но смысл единого
        // источника истины в том, чтобы совпадали и имена.
        namingConvention: { enumValues: 'keep' },
      },
    },
  },
  hooks: {
    afterAllFileWrite: ['prettier --write'],
  },
};

export default config;
