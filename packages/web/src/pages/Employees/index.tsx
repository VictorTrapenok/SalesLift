import HasPermission from '@/components/HasPermission';
import type { EmployeesQuery } from '@/graphql/generated/graphql';
import { UserPermissions } from '@/graphql/generated/graphql';
import { parseGraphQLError } from '@/utils/graphqlError';
import { PlusOutlined } from '@ant-design/icons';
import { useQuery } from '@apollo/client';
import { Alert, App, Button, Card, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState, type JSX } from 'react';
import { useTranslation } from 'react-i18next';
import AddEmployeeModal from './components/AddEmployeeModal';
import { EMPLOYEES_QUERY } from './queries';
import { roleLabelKey } from './roles';

const { Title } = Typography;

/** Сотрудник в таблице. Тип выведен из GraphQL-схемы. */
type Employee = EmployeesQuery['resolverUsersList'][number];

/** Роль администратора выделена цветом: её носителей должно быть видно сразу. */
const ROLE_COLORS: Record<string, string> = {
  admin: 'gold',
  manager: 'blue',
  viewer: 'default',
};

/**
 * Список сотрудников компании.
 *
 * Компания в запрос не передаётся: бэкенд берёт её из токена
 * (`resolver_users_list`). Кнопка «Добавить» скрыта без права
 * `Permission_users_create` — но это только вежливость, отказ выдаёт резолвер.
 */
export default function EmployeesPage(): JSX.Element {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const [isAddOpen, setIsAddOpen] = useState(false);

  const { data, loading, error } = useQuery(EMPLOYEES_QUERY);
  const parsedError = parseGraphQLError(error);

  /** Дата последнего входа в формате текущей локали. */
  const formatLastLogin = (value: string | null): string => {
    if (!value) {
      return t('employees.neverLoggedIn');
    }
    return new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  };

  const columns: ColumnsType<Employee> = [
    {
      title: t('employees.columnName'),
      dataIndex: 'name',
      render: (name: string, employee): JSX.Element => (
        <span data-qa={`employees-row-name-${employee.id}`}>{name}</span>
      ),
    },
    { title: t('employees.columnEmail'), dataIndex: 'email' },
    {
      title: t('employees.columnRole'),
      dataIndex: 'role',
      render: (role: string): JSX.Element => {
        const labelKey = roleLabelKey(role);
        return (
          <Tag color={ROLE_COLORS[role] ?? 'default'} data-qa={`employees-role-${role}`}>
            {labelKey ? t(labelKey) : role}
          </Tag>
        );
      },
    },
    {
      title: t('employees.columnLastLogin'),
      dataIndex: 'lastLoginAt',
      render: (lastLoginAt: string | null): string => formatLastLogin(lastLoginAt),
    },
  ];

  return (
    <Card data-qa="employees-page">
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          {t('employees.title')}
        </Title>

        <HasPermission permission={UserPermissions.Permission_users_create}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={(): void => setIsAddOpen(true)}
            data-qa="employees-add-button"
          >
            {t('employees.add')}
          </Button>
        </HasPermission>
      </Space>

      {parsedError && (
        <Alert
          type="error"
          showIcon
          message={parsedError.message}
          data-qa="employees-error"
          style={{ marginBottom: 16 }}
        />
      )}

      <Table<Employee>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data?.resolverUsersList ?? []}
        pagination={false}
        data-qa="employees-table"
      />

      <AddEmployeeModal
        open={isAddOpen}
        onClose={(): void => setIsAddOpen(false)}
        onCreated={(): void => {
          setIsAddOpen(false);
          void message.success(t('employees.addSuccess'));
        }}
      />
    </Card>
  );
}
