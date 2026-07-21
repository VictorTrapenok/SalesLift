import { expect, test } from '@playwright/test';
import { login, logout, passwordField, registerCompany } from './helpers';

/** Профиль: «о себе» сохраняется и переживает перезагрузку; пароль меняется. */
test.describe('Профиль', () => {
  test('сохраняет «о себе» и показывает его после перезагрузки', async ({ page }) => {
    await registerCompany(page);

    await page.getByTestId('menu-profile').click();
    await expect(page.getByTestId('profile-page')).toBeVisible();

    const bio = `Продаю с ${Date.now()}`;
    await page.getByTestId('profile-bio').fill(bio);
    await page.getByTestId('profile-submit').click();

    // Перезагружаем страницу — значение приходит уже с сервера.
    await page.goto('/profile');
    await expect(page.getByTestId('profile-bio')).toHaveValue(bio);
  });

  test('меняет пароль: вход по новому работает', async ({ page }) => {
    const data = await registerCompany(page);
    const newPassword = 'e2eNewPassw0rd';

    await page.getByTestId('menu-profile').click();
    await passwordField(page, 'profile-current-password').fill(data.password);
    await passwordField(page, 'profile-new-password').fill(newPassword);
    await page.getByTestId('profile-password-submit').click();

    await logout(page);
    // Вход по новому паролю проходит.
    await login(page, data.email, newPassword);
    await expect(page.getByTestId('current-user-name')).toHaveText(data.adminName);
  });
});
