import { Card, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';

const { Title } = Typography;

/**
 * Список сотрудников компании.
 *
 * TODO(шаг 8): заменить заглушку на реальную таблицу. Требует резолвера
 * resolver_users_list на бэкенде.
 */
export default function EmployeesPage(): JSX.Element {
  const { t } = useTranslation();

  return (
    <Card data-qa="employees-page">
      <Title level={4}>{t('employees.title')}</Title>
    </Card>
  );
}
