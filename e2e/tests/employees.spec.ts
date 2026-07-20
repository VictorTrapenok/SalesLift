import { expect, test } from '@playwright/test';
import { addEmployee, employeeRow, login, logout, registerCompany } from './helpers';

/**
 * Управление сотрудниками в браузере: заведение, смена роли, отключение,
 * удаление — и то, что за отключением следует запрет входа.
 */
test.describe('Сотрудники', () => {
  test('администратор заводит сотрудника и видит его в списке', async ({ page }) => {
    await registerCompany(page);
    const employee = await addEmployee(page);

    const row = employeeRow(page, employee.email);
    await expect(row).toContainText(employee.name);
    // Новый сотрудник заводится наблюдателем.
    await expect(row.getByTestId('employees-role-viewer')).toBeVisible();
    await expect(row.getByTestId('employees-status-active')).toBeVisible();
  });

  test('администратор меняет роль сотрудника', async ({ page }) => {
    await registerCompany(page);
    const employee = await addEmployee(page);
    const row = employeeRow(page, employee.email);

    // AntD-Select: открыть и выбрать «Manager» в выпадающем списке (портал).
    await row.locator('[data-qa^="employees-role-select-"]').click();
    await page.getByText('Manager', { exact: true }).click();

    await expect(row.getByTestId('employees-role-manager')).toBeVisible();
  });

  test('отключённый сотрудник не может войти', async ({ page }) => {
    await registerCompany(page);
    const employee = await addEmployee(page);
    const row = employeeRow(page, employee.email);

    await row.locator('[data-qa^="employees-toggle-status-"]').click();
    await expect(row.getByTestId('employees-status-suspended')).toBeVisible();

    await logout(page);

    // Вход отключённого отклоняется.
    await page.goto('/login');
    await page.getByTestId('login-email').fill(employee.email);
    await page.locator('[data-qa="login-password"] input, input[data-qa="login-password"]').first().fill(employee.password);
    await page.getByTestId('login-submit').click();

    await expect(page.getByTestId('login-error')).toBeVisible();
    await expect(page.getByTestId('employees-page')).toHaveCount(0);
  });

  test('администратор удаляет сотрудника', async ({ page }) => {
    await registerCompany(page);
    const employee = await addEmployee(page);
    const row = employeeRow(page, employee.email);

    // Кнопка-корзина в строке; подтверждение — в портале Popconfirm.
    await row.locator('[data-qa^="employees-delete-"]').click();
    await page.locator('[data-qa^="employees-delete-confirm-"]').click();

    await expect(employeeRow(page, employee.email)).toHaveCount(0);
  });

  test('наблюдатель не видит кнопку добавления', async ({ page }) => {
    await registerCompany(page);
    const employee = await addEmployee(page);
    await logout(page);

    // Наблюдатель видит список, но управляющих контролов у него нет.
    await login(page, employee.email, employee.password);
    await expect(page.getByTestId('employees-table')).toBeVisible();
    await expect(page.getByTestId('employees-add-button')).toHaveCount(0);
  });
});
