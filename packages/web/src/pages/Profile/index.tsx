import { useCurrentUser } from '@/hooks/useCurrentUser';
import { Card, Skeleton, Space, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import ChangePasswordForm from './components/ChangePasswordForm';
import ProfileForm from './components/ProfileForm';

const { Title } = Typography;

/**
 * Профиль сотрудника: имя, «о себе» и смена пароля.
 *
 * Прав здесь не проверяется: сотрудник правит свою же учётную запись, которую
 * бэкенд берёт из токена. Идентификатора пользователя нет ни в запросе, ни в
 * адресе страницы — и не должно быть.
 *
 * Две независимые формы, а не одна: сохранение «о себе» не должно требовать
 * ввода пароля, а смена пароля — трогать профиль.
 */
export default function ProfilePage(): JSX.Element {
  const { t } = useTranslation();
  const { currentUser, loading } = useCurrentUser();

  if (loading || !currentUser) {
    return (
      <Card data-qa="profile-page">
        <Skeleton active data-qa="profile-loading" />
      </Card>
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }} data-qa="profile-page">
      <Card>
        <Title level={4}>{t('profile.title')}</Title>
        <ProfileForm currentUser={currentUser} />
      </Card>

      <Card>
        <Title level={4}>{t('profile.changePassword')}</Title>
        <ChangePasswordForm />
      </Card>
    </Space>
  );
}
