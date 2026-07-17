import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

/**
 * Конфигурация ESLint для фронтенда (flat config, ESLint 9).
 *
 * Правила подобраны так, чтобы линтер стерёг договорённости из CLAUDE.md,
 * которые не проверяет `tsc`: явные типы возврата, отсутствие «немых» catch,
 * запрет `any`. То, что уже ловит компилятор, здесь не дублируется.
 */
export default tseslint.config(
  {
    // Сгенерированный кодогенерацией код правим не мы, а codegen: он же
    // прогоняет по нему prettier. Линтовать его бессмысленно — правила всё
    // равно применить некуда. Каталога нет в git, он появляется на `npm run
    // codegen` перед сборкой и перед линтером в CI.
    ignores: ['src/graphql/generated/**', 'dist/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // Vite обновляет модуль без перезагрузки страницы, только если файл
      // экспортирует одни компоненты. Экспорт константы рядом с компонентом
      // молча ломает hot reload — предупреждаем, но сборку не роняем.
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],

      // CLAUDE.md: «Всегда указывай явный тип возвращаемого значения» —
      // включая колбэки и стрелочные функции. Аргументы-выражения исключены:
      // требовать аннотацию у `onClick={() => setOpen(true)}` — шум.
      '@typescript-eslint/explicit-function-return-type': [
        'error',
        {
          allowExpressions: false,
          allowTypedFunctionExpressions: true,
          allowHigherOrderFunctions: true,
        },
      ],

      // CLAUDE.md: строгая типизация везде. `any` протаскивает мимо tsc любую
      // ошибку, ради которой typescript и заводили.
      '@typescript-eslint/no-explicit-any': 'error',

      // CLAUDE.md: «Каждый catch логирует ошибку». Пустой блок сюда не
      // пролезет; если ошибку правда можно проигнорировать — нужен коммент,
      // и правило это принимает.
      'no-empty': ['error', { allowEmptyCatch: false }],

      // Неиспользуемая переменная — обычно забытый кусок рефакторинга.
      // Осознанно выброшенное значение помечается подчёркиванием.
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    // router.tsx экспортирует таблицу маршрутов, а не компоненты, поэтому
    // hot reload к нему неприменим в принципе, и правило только шумит.
    // Гарды маршрутов живут рядом с таблицей осознанно: они её часть.
    files: ['src/router.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
);
