/**
 * Английская локаль — ЭТАЛОН.
 *
 * Набор ключей этого файла является источником истины: ru-RU.ts типизирован
 * как `typeof enUS`, поэтому пропущенный или лишний ключ там — ошибка
 * компиляции. Отдельный тест на согласованность локалей не нужен, это делает tsc.
 *
 * Ключи плоские, dot-namespaced, и используются в коде ЦЕЛИКОМ, одной
 * строкой-литералом. Собирать ключ из фрагментов нельзя: такой ключ не найти
 * грепом и его теряют при рефакторинге.
 */
const enUS = {
  // ── Общее ──────────────────────────────────────────────────────────────
  'common.loading': 'Loading…',
  'common.save': 'Save',
  'common.cancel': 'Cancel',
  'common.saved': 'Saved',
  'common.language': 'Language',
  'common.logout': 'Sign out',

  // ── Меню ───────────────────────────────────────────────────────────────
  'menu.employees': 'Employees',
  'menu.settings': 'Company settings',
  'menu.profile': 'Profile',

  // ── Вход ───────────────────────────────────────────────────────────────
  'auth.login.title': 'Sign in',
  'auth.login.subtitle': 'Call analytics for your sales team',
  'auth.login.email': 'Email',
  'auth.login.emailRequired': 'Please enter your email',
  'auth.login.password': 'Password',
  'auth.login.passwordRequired': 'Please enter your password',
  'auth.login.submit': 'Sign in',
  'auth.login.noAccount': 'No account yet?',
  'auth.login.registerLink': 'Register your company',

  // ── Регистрация ────────────────────────────────────────────────────────
  'auth.register.title': 'Register your company',
  'auth.register.subtitle': 'You will become the administrator',
  'auth.register.companyName': 'Company name',
  'auth.register.companyNameRequired': 'Please enter the company name',
  'auth.register.adminName': 'Your name',
  'auth.register.adminNameRequired': 'Please enter your name',
  'auth.register.email': 'Email',
  'auth.register.emailRequired': 'Please enter your email',
  'auth.register.emailInvalid': 'Please enter a valid email address',
  'auth.register.password': 'Password',
  'auth.register.passwordRequired': 'Please enter a password',
  'auth.register.passwordTooShort': 'Password must be at least 8 characters',
  'auth.register.submit': 'Create company',
  'auth.register.hasAccount': 'Already have an account?',
  'auth.register.loginLink': 'Sign in',

  // ── Сотрудники ─────────────────────────────────────────────────────────
  'employees.title': 'Employees',
  'employees.columnName': 'Name',
  'employees.columnEmail': 'Email',
  'employees.columnRole': 'Role',
  'employees.columnLastLogin': 'Last sign-in',
  'employees.neverLoggedIn': 'Never',
  'employees.add': 'Add employee',
  'employees.addTitle': 'New employee',
  'employees.addSuccess': 'Employee added',
  'employees.roleAdmin': 'Administrator',
  'employees.roleManager': 'Manager',
  'employees.roleViewer': 'Viewer',

  // ── Настройки компании ─────────────────────────────────────────────────
  'orgSettings.title': 'Company settings',
  'orgSettings.companyName': 'Company name',
  'orgSettings.companyNameRequired': 'Please enter the company name',
  'orgSettings.saved': 'Settings saved',

  // ── Профиль ────────────────────────────────────────────────────────────
  'profile.title': 'Profile',
  'profile.name': 'Name',
  'profile.email': 'Email',
  'profile.bio': 'About me',
  'profile.bioPlaceholder': 'A few words about yourself',
  'profile.bioSaved': 'Profile updated',
  'profile.changePassword': 'Change password',
  'profile.currentPassword': 'Current password',
  'profile.currentPasswordRequired': 'Please enter your current password',
  'profile.newPassword': 'New password',
  'profile.newPasswordRequired': 'Please enter a new password',
  'profile.passwordChanged': 'Password changed',

  // ── Ошибки ─────────────────────────────────────────────────────────────
  'error.notFound': 'Page not found',
  'error.goHome': 'Go to home page',
  'error.unknown': 'Something went wrong. Please try again.',
};

export default enUS;
