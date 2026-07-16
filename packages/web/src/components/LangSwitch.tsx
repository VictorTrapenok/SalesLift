import { changeLocale, SUPPORTED_LOCALES, type AppLocale } from '@/i18n';
import { GlobalOutlined } from '@ant-design/icons';
import { Dropdown, type MenuProps } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';

/** Подписи языков — на своём же языке, как принято в переключателях. */
const LOCALE_LABELS: Record<AppLocale, string> = {
  'en-US': 'English',
  'ru-RU': 'Русский',
};

/** Переключатель языка интерфейса. */
export default function LangSwitch(): JSX.Element {
  const { i18n } = useTranslation();

  const items: MenuProps['items'] = SUPPORTED_LOCALES.map((locale) => ({
    key: locale,
    label: LOCALE_LABELS[locale],
    'data-qa': `lang-option-${locale}`,
  }));

  const handleClick: MenuProps['onClick'] = ({ key }): void => {
    void changeLocale(key as AppLocale);
  };

  return (
    <Dropdown menu={{ items, onClick: handleClick, selectedKeys: [i18n.language] }} placement="bottomRight">
      <span style={{ cursor: 'pointer', padding: '0 8px' }} data-qa="lang-switch">
        <GlobalOutlined /> {LOCALE_LABELS[i18n.language as AppLocale] ?? i18n.language}
      </span>
    </Dropdown>
  );
}
