import { expect, type Locator, type Page } from '@playwright/test';

/**
 * Учётные данные компании, заведённой тестом.
 *
 * Каждый прогон создаёт свою компанию: общая тестовая база живёт между
 * прогонами, а e-mail глобально уникален, поэтому фиксированный адрес рано или
 * поздно столкнулся бы с оставшимся от прошлого прогона.
 */
export interface Company {
  company: string;
  adminName: string;
  email: string;
  password: string;
}

let counter = 0;

/** Уникальный набор данных для новой компании. */
export function uniqueCompany(): Company {
  counter += 1;
  const suffix = `${Date.now()}-${counter}`;
  return {
    company: `E2E Company ${suffix}`,
    adminName: 'E2E Admin',
    email: `e2e-${suffix}@example.com`,
    password: 'e2ePassw0rd',
  };
}

/**
 * Поле пароля.
 *
 * Пароли выводятся через AntD `Input.Password`, который оборачивает настоящий
 * `<input>` в span. `data-qa` может оказаться и на обёртке, и на инпуте,
 * поэтому целимся в инпут любым из двух путей.
 */
export function passwordField(page: Page, qa: string): Locator {
  return page.locator(`input[data-qa="${qa}"], [data-qa="${qa}"] input`).first();
}

/**
 * Регистрирует новую компанию через UI и дожидается кабинета.
 *
 * Возвращает учётные данные, чтобы тест мог потом выйти и войти заново.
 */
export async function registerCompany(page: Page): Promise<Company> {
  const data = uniqueCompany();

  await page.goto('/register');
  await page.getByTestId('register-company-name').fill(data.company);
  await page.getByTestId('register-admin-name').fill(data.adminName);
  await page.getByTestId('register-email').fill(data.email);
  await passwordField(page, 'register-password').fill(data.password);
  await page.getByTestId('register-submit').click();

  // Успешная регистрация уводит в кабинет.
  await expect(page.getByTestId('employees-page')).toBeVisible();
  return data;
}

/** Выходит из кабинета через меню пользователя в шапке. */
export async function logout(page: Page): Promise<void> {
  await page.getByTestId('user-menu').click();
  await page.getByTestId('user-menu-logout').click();
  await expect(page.getByTestId('login-page')).toBeVisible();
}

/** Данные заводимого сотрудника. */
export interface Employee {
  name: string;
  email: string;
  password: string;
}

/** Уникальный сотрудник для теста. */
export function uniqueEmployee(namePrefix = 'Employee'): Employee {
  counter += 1;
  const suffix = `${Date.now()}-${counter}`;
  return {
    name: `${namePrefix} ${suffix}`,
    email: `emp-${suffix}@example.com`,
    password: 'e2ePassw0rd',
  };
}

/**
 * Заводит сотрудника через модальное окно на странице сотрудников.
 *
 * Роль оставляет по умолчанию (`viewer`): взаимодействие с AntD-Select через
 * портал хрупко, а роль всё равно проверяется отдельным сценарием смены роли.
 * Возвращает данные заведённого сотрудника.
 */
export async function addEmployee(page: Page, namePrefix?: string): Promise<Employee> {
  const employee = uniqueEmployee(namePrefix);

  await page.getByTestId('employees-add-button').click();
  await expect(page.getByTestId('employees-add-modal')).toBeVisible();
  await page.getByTestId('employees-add-name').fill(employee.name);
  await page.getByTestId('employees-add-email').fill(employee.email);
  await passwordField(page, 'employees-add-password').fill(employee.password);
  await page.getByTestId('employees-add-submit').click();

  // После успеха окно закрывается, а сотрудник появляется в таблице.
  await expect(page.getByTestId('employees-add-modal')).toBeHidden();
  await expect(employeeRow(page, employee.email)).toBeVisible();
  return employee;
}

/** Строка таблицы сотрудников по e-mail. */
export function employeeRow(page: Page, email: string): Locator {
  return page.locator('tr', { hasText: email });
}

/** Входит по e-mail и паролю и дожидается кабинета. */
export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.getByTestId('login-email').fill(email);
  await passwordField(page, 'login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await expect(page.getByTestId('employees-page')).toBeVisible();
}
