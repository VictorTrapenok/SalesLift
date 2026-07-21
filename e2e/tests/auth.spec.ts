import { expect, test } from '@playwright/test';
import { login, logout, registerCompany } from './helpers';

/**
 * Базовый сценарий входа — то же, что проверяет дымовой тест, но в браузере:
 * регистрация ведёт в кабинет, выход возвращает на вход, вход пускает обратно.
 */
test.describe('Аутентификация', () => {
  test('регистрация → кабинет → выход → повторный вход', async ({ page }) => {
    const data = await registerCompany(page);

    // В шапке — имя вошедшего администратора.
    await expect(page.getByTestId('current-user-name')).toHaveText(data.adminName);

    await logout(page);
    await login(page, data.email, data.password);

    await expect(page.getByTestId('current-user-name')).toHaveText(data.adminName);
  });

  test('неаутентифицированного не пускают в кабинет', async ({ page }) => {
    await page.goto('/employees');
    // ProtectedRoute редиректит на вход.
    await expect(page.getByTestId('login-page')).toBeVisible();
  });

  test('неверный пароль показывает ошибку и не пускает', async ({ page }) => {
    const data = await registerCompany(page);
    await logout(page);

    await page.goto('/login');
    await page.getByTestId('login-email').fill(data.email);
    await page.locator('[data-qa="login-password"] input, input[data-qa="login-password"]').first().fill('wrongPass1');
    await page.getByTestId('login-submit').click();

    await expect(page.getByTestId('login-error')).toBeVisible();
    await expect(page.getByTestId('employees-page')).toHaveCount(0);
  });
});
