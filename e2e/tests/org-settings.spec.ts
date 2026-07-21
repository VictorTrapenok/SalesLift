import { expect, test } from '@playwright/test';
import { registerCompany } from './helpers';

/** Настройки компании: изменение названия сохраняется. */
test.describe('Настройки компании', () => {
  test('администратор меняет название компании', async ({ page }) => {
    await registerCompany(page);

    await page.getByTestId('menu-settings').click();
    await expect(page.getByTestId('org-settings-page')).toBeVisible();

    const newName = `Renamed ${Date.now()}`;
    await page.getByTestId('org-settings-name').fill(newName);
    await page.getByTestId('org-settings-submit').click();

    // Перезагружаем — значение приходит с сервера, а не из формы.
    await page.goto('/settings');
    await expect(page.getByTestId('org-settings-name')).toHaveValue(newName);
  });
});
