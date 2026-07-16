import { Card, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';

const { Title } = Typography;

/**
 * Профиль сотрудника: смена пароля и bio.
 *
 * TODO(шаг 8): заменить заглушку на реальные формы. Требует резолверов
 * resolver_profile_changePassword и resolver_profile_update на бэкенде.
 */
export default function ProfilePage(): JSX.Element {
  const { t } = useTranslation();

  return (
    <Card data-qa="profile-page">
      <Title level={4}>{t('profile.title')}</Title>
    </Card>
  );
}
