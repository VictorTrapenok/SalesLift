import { apolloClient } from '@/graphql/client';
import { router } from '@/router';
import { ApolloProvider } from '@apollo/client';
import { App as AntdApp, ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import ruRU from 'antd/locale/ru_RU';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { RouterProvider } from 'react-router';

/** Локали AntD (кнопки пагинации, календари) — отдельно от наших переводов. */
const ANTD_LOCALES = {
  'en-US': enUS,
  'ru-RU': ruRU,
} as const;

/**
 * Корень приложения.
 *
 * Порядок провайдеров: Apollo снаружи (роутер и страницы шлют запросы),
 * ConfigProvider внутри (ему нужен текущий язык из i18n), а внутри него —
 * AntdApp: он раздаёт контекст для `App.useApp()`, через который страницы
 * показывают уведомления. Без него статический `message.success` работает, но
 * игнорирует и тему, и локаль ConfigProvider'а.
 */
export default function App(): JSX.Element {
  const { i18n } = useTranslation();
  const antdLocale = ANTD_LOCALES[i18n.language as keyof typeof ANTD_LOCALES] ?? enUS;

  return (
    <ApolloProvider client={apolloClient}>
      <ConfigProvider locale={antdLocale}>
        <AntdApp>
          <RouterProvider router={router} />
        </AntdApp>
      </ConfigProvider>
    </ApolloProvider>
  );
}
