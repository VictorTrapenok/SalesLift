import type enUS from './en-US';

/**
 * Русская локаль.
 *
 * Тип берётся из en-US: пропущенный или лишний ключ — ОШИБКА КОМПИЛЯЦИИ.
 * Это фронтенд-аналог теста согласованности локалей на бэкенде, только
 * бесплатный: его проверяет tsc, а не отдельный прогон.
 */
const ruRU: typeof enUS = {
  // ── Общее ──────────────────────────────────────────────────────────────
  'common.loading': 'Загрузка…',
  'common.save': 'Сохранить',
  'common.cancel': 'Отмена',
  'common.saved': 'Сохранено',
  'common.language': 'Язык',
  'common.logout': 'Выйти',

  // ── Меню ───────────────────────────────────────────────────────────────
  'menu.employees': 'Сотрудники',
  'menu.settings': 'Настройки компании',
  'menu.profile': 'Профиль',

  // ── Вход ───────────────────────────────────────────────────────────────
  'auth.login.title': 'Вход',
  'auth.login.subtitle': 'Аналитика звонков для отдела продаж',
  'auth.login.email': 'E-mail',
  'auth.login.emailRequired': 'Введите e-mail',
  'auth.login.password': 'Пароль',
  'auth.login.passwordRequired': 'Введите пароль',
  'auth.login.submit': 'Войти',
  'auth.login.noAccount': 'Ещё нет аккаунта?',
  'auth.login.registerLink': 'Зарегистрировать компанию',

  // ── Регистрация ────────────────────────────────────────────────────────
  'auth.register.title': 'Регистрация компании',
  'auth.register.subtitle': 'Вы станете администратором',
  'auth.register.companyName': 'Название компании',
  'auth.register.companyNameRequired': 'Введите название компании',
  'auth.register.adminName': 'Ваше имя',
  'auth.register.adminNameRequired': 'Введите имя',
  'auth.register.email': 'E-mail',
  'auth.register.emailRequired': 'Введите e-mail',
  'auth.register.emailInvalid': 'Введите корректный e-mail',
  'auth.register.password': 'Пароль',
  'auth.register.passwordRequired': 'Введите пароль',
  'auth.register.passwordTooShort': 'Пароль должен быть не короче 8 символов',
  'auth.register.submit': 'Создать компанию',
  'auth.register.hasAccount': 'Уже есть аккаунт?',
  'auth.register.loginLink': 'Войти',

  // ── Сотрудники ─────────────────────────────────────────────────────────
  'employees.title': 'Сотрудники',
  'employees.columnName': 'Имя',
  'employees.columnEmail': 'E-mail',
  'employees.columnRole': 'Роль',
  'employees.columnLastLogin': 'Последний вход',
  'employees.neverLoggedIn': 'Ни разу',
  'employees.add': 'Добавить сотрудника',
  'employees.addTitle': 'Новый сотрудник',
  'employees.addSuccess': 'Сотрудник добавлен',
  'employees.roleAdmin': 'Администратор',
  'employees.roleManager': 'Менеджер',
  'employees.roleViewer': 'Наблюдатель',
  'employees.columnStatus': 'Статус',
  'employees.columnActions': 'Действия',
  'employees.statusActive': 'Активен',
  'employees.statusSuspended': 'Отключён',
  'employees.suspend': 'Отключить',
  'employees.activate': 'Включить',
  'employees.suspended': 'Сотрудник отключён',
  'employees.activated': 'Сотрудник включён',
  'employees.roleChanged': 'Роль изменена',
  'employees.delete': 'Удалить',
  'employees.deleted': 'Сотрудник удалён',
  'employees.deleteConfirm': 'Удалить сотрудника?',
  'employees.selfDisabled': 'Свою учётную запись здесь менять нельзя',

  // ── Настройки компании ─────────────────────────────────────────────────
  'orgSettings.title': 'Настройки компании',
  'orgSettings.companyName': 'Название компании',
  'orgSettings.companyNameRequired': 'Введите название компании',
  'orgSettings.country': 'Страна',
  'orgSettings.countryPlaceholder': 'Двухбуквенный код, например RU',
  'orgSettings.website': 'Сайт',
  'orgSettings.contactPhone': 'Контактный телефон',
  'orgSettings.saved': 'Настройки сохранены',

  // ── Профиль ────────────────────────────────────────────────────────────
  'profile.title': 'Профиль',
  'profile.name': 'Имя',
  'profile.email': 'E-mail',
  'profile.bio': 'О себе',
  'profile.bioPlaceholder': 'Несколько слов о себе',
  'profile.bioSaved': 'Профиль обновлён',
  'profile.changePassword': 'Сменить пароль',
  'profile.currentPassword': 'Текущий пароль',
  'profile.currentPasswordRequired': 'Введите текущий пароль',
  'profile.newPassword': 'Новый пароль',
  'profile.newPasswordRequired': 'Введите новый пароль',
  'profile.passwordChanged': 'Пароль изменён',

  // ── Ошибки ─────────────────────────────────────────────────────────────
  'error.notFound': 'Страница не найдена',
  'error.goHome': 'На главную',
  'error.unknown': 'Что-то пошло не так. Попробуйте ещё раз.',
};

export default ruRU;
