import { Card, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';

const { Title } = Typography;

/**
 * Настройки компании.
 *
 * TODO(шаг 8): заменить заглушку на форму названия компании. Требует резолвера
 * resolver_orgSettings_update на бэкенде.
 */
export default function OrgSettingsPage(): JSX.Element {
  const { t } = useTranslation();

  return (
    <Card data-qa="org-settings-page">
      <Title level={4}>{t('orgSettings.title')}</Title>
    </Card>
  );
}
