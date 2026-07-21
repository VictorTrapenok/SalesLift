import HasPermission from '@/components/HasPermission';
import type { EmployeesQuery } from '@/graphql/generated/graphql';
import { UserPermissions } from '@/graphql/generated/graphql';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { parseGraphQLError } from '@/utils/graphqlError';
import { DeleteOutlined } from '@ant-design/icons';
import { useMutation, type ApolloError } from '@apollo/client';
import { App, Button, Popconfirm, Select, Space, Tooltip } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { CHANGE_ROLE_MUTATION, DELETE_EMPLOYEE_MUTATION, EMPLOYEES_QUERY, SET_STATUS_MUTATION } from '../queries';
import { ROLE_LABEL_KEYS, ROLE_NAMES } from '../roles';

/** Сотрудник строки таблицы. Тип выведен из GraphQL-схемы. */
type Employee = EmployeesQuery['resolverUsersList'][number];

interface EmployeeActionsProps {
  employee: Employee;
}

/**
 * Управляющие действия над сотрудником: смена роли, отключение/включение,
 * удаление.
 *
 * Каждое действие скрыто без соответствующего права (`HasPermission`) — но это
 * только вежливость к пользователю: настоящую проверку делает резолвер. Над
 * собственной учётной записью действия заблокированы: бэкенд их всё равно
 * отвергнет (`users.cannotManageSelf`), а на клиенте так понятнее, почему
 * контролы неактивны.
 */
export default function EmployeeActions({ employee }: EmployeeActionsProps): JSX.Element {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { currentUser } = useCurrentUser();

  const isSelf = currentUser?.id === employee.id;
  const isSuspended = employee.status === 'suspended';

  /** Общий обработчик ошибок: показываем локализованный текст бэкенда. */
  const onError =
    (action: string) =>
    (err: ApolloError): void => {
      console.error(`Не удалось выполнить действие над сотрудником: ${action}`, err);
      const parsed = parseGraphQLError(err);
      if (parsed) {
        void message.error(parsed.message);
      }
    };

  const [changeRole, { loading: changingRole }] = useMutation(CHANGE_ROLE_MUTATION, {
    onCompleted: (): void => void message.success(t('employees.roleChanged')),
    onError: onError('changeRole'),
  });

  const [setStatus, { loading: settingStatus }] = useMutation(SET_STATUS_MUTATION, {
    onCompleted: (data): void =>
      void message.success(
        data.resolverUsersSetStatus.status === 'suspended' ? t('employees.suspended') : t('employees.activated'),
      ),
    onError: onError('setStatus'),
  });

  const [deleteEmployee, { loading: deleting }] = useMutation(DELETE_EMPLOYEE_MUTATION, {
    // Строка исчезает из списка — правкой кэша по id не обойтись, перезапрашиваем.
    refetchQueries: [EMPLOYEES_QUERY],
    onCompleted: (): void => void message.success(t('employees.deleted')),
    onError: onError('delete'),
  });

  return (
    <Space data-qa={`employees-actions-${employee.id}`}>
      <HasPermission permission={UserPermissions.Permission_users_edit}>
        <Tooltip title={isSelf ? t('employees.selfDisabled') : undefined}>
          <Select
            size="small"
            value={employee.role}
            disabled={isSelf || changingRole}
            loading={changingRole}
            style={{ width: 130 }}
            data-qa={`employees-role-select-${employee.id}`}
            onChange={(role): void => {
              void changeRole({ variables: { input: { userId: employee.id, role } } });
            }}
            options={ROLE_NAMES.map((role) => ({ value: role, label: t(ROLE_LABEL_KEYS[role]) }))}
          />
        </Tooltip>

        <Tooltip title={isSelf ? t('employees.selfDisabled') : undefined}>
          <Button
            size="small"
            disabled={isSelf}
            loading={settingStatus}
            data-qa={`employees-toggle-status-${employee.id}`}
            onClick={(): void => {
              void setStatus({
                variables: { input: { userId: employee.id, status: isSuspended ? 'active' : 'suspended' } },
              });
            }}
          >
            {isSuspended ? t('employees.activate') : t('employees.suspend')}
          </Button>
        </Tooltip>
      </HasPermission>

      <HasPermission permission={UserPermissions.Permission_users_delete}>
        <Popconfirm
          title={t('employees.deleteConfirm')}
          okText={t('employees.delete')}
          cancelText={t('common.cancel')}
          okButtonProps={{ danger: true, 'data-qa': `employees-delete-confirm-${employee.id}` }}
          disabled={isSelf}
          onConfirm={(): void => {
            void deleteEmployee({ variables: { input: { userId: employee.id } } });
          }}
        >
          <Tooltip title={isSelf ? t('employees.selfDisabled') : undefined}>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={isSelf}
              loading={deleting}
              data-qa={`employees-delete-${employee.id}`}
            />
          </Tooltip>
        </Popconfirm>
      </HasPermission>
    </Space>
  );
}
