import { defineConfig, devices } from '@playwright/test';

/**
 * Конфигурация e2e-проверок.
 *
 * Тесты бьют по УЖЕ ЗАПУЩЕННОМУ продукту — своё приложение Playwright не
 * поднимает. Адрес задаётся `BASE_URL`; по умолчанию — тот же интегрированный
 * образ на :8000, который проверяет дымовой тест (`make up` или собранный
 * образ в CI). Для разработки с двумя серверами укажите Vite:
 *
 *   BASE_URL=http://localhost:5173 npm test
 *
 * Почему не `webServer`: продукту нужны БД, миграции и собранная SPA. Поднимать
 * это из Playwright — значит дублировать `compose.yaml` и шаги CI. Дешевле
 * прогнать против того, что уже поднято, — ровно как дымовой тест.
 */
const BASE_URL = process.env.BASE_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './tests',
  // Общая тестовая база у продукта одна, а сценарии заводят компании и
  // сотрудников: параллельные прогоны не конфликтуют (e-mail уникален по
  // времени), но флап от гонок за общими данными ни к чему. На CI — один
  // воркер, локально можно поднять.
  fullyParallel: false,
  workers: process.env.CI ? 1 : undefined,
  // На CI запрещаем `test.only`, случайно оставленный в коммите.
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['github'], ['html', { outputFolder: 'playwright-report', open: 'never' }]]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    // Селекторы вешаются на `data-qa` — тот же атрибут, что требует CLAUDE.md
    // для вёрстки. `page.getByTestId('login-page')` ищет `[data-qa="login-page"]`.
    testIdAttribute: 'data-qa',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    // Пишем видео КАЖДОГО теста, а не только упавших: CI выкладывает их
    // артефактом, чтобы прогон можно было пересмотреть целиком. Видео пишутся
    // в `outputDir` (по умолчанию `test-results/`) по файлу на тест. Дорого
    // держать всегда — если понадобится экономить, поставьте
    // `retain-on-failure`: тогда останутся только видео упавших сценариев.
    video: 'on',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
