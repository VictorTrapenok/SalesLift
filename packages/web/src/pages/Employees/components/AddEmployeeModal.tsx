import { parseGraphQLError } from '@/utils/graphqlError';
import { useMutation } from '@apollo/client';
import { Alert, Form, Input, Modal, Select } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { CREATE_EMPLOYEE_MUTATION, EMPLOYEES_QUERY } from '../queries';
import { ROLE_LABEL_KEYS, ROLE_NAMES } from '../roles';

/** Поля формы «новый сотрудник». */
interface AddEmployeeFormValues {
  name: string;
  email: string;
  password: string;
  role: string;
}

interface AddEmployeeModalProps {
  open: boolean;
  onClose: () => void;
  /** Вызывается после успешного создания — страница показывает уведомление. */
  onCreated: () => void;
}

/**
 * Модальное окно заведения сотрудника.
 *
 * Пароль задаёт администратор и передаёт сотруднику сам: приглашений по ссылке
 * пока нет. Валидация здесь — только про удобство; настоящая живёт в
 * `users_service.create_employee`, и её ошибки показываются в Alert.
 */
export default function AddEmployeeModal({ open, onClose, onCreated }: AddEmployeeModalProps): JSX.Element {
  const { t } = useTranslation();
  const [form] = Form.useForm<AddEmployeeFormValues>();

  const [createEmployee, { loading, error, reset }] = useMutation(CREATE_EMPLOYEE_MUTATION, {
    // Проще перезапросить список, чем править кэш руками: сотрудников
    // десятки, запрос дешёвый, а ручное обновление кэша — источник
    // рассинхрона при каждом изменении набора полей.
    refetchQueries: [EMPLOYEES_QUERY],
    onCompleted: (): void => {
      form.resetFields();
      onCreated();
    },
    // Ошибку показываем в окне; без обработчика Apollo бросит исключение
    // в рендер и уронит страницу.
    onError: (err): void => {
      console.error('Не удалось завести сотрудника', err);
    },
  });

  const parsedError = parseGraphQLError(error);

  const handleSubmit = (values: AddEmployeeFormValues): void => {
    void createEmployee({ variables: { input: values } });
  };

  const handleCancel = (): void => {
    // Сбрасываем и форму, и ошибку: иначе прошлая ошибка встретит
    // пользователя при следующем открытии окна.
    form.resetFields();
    reset();
    onClose();
  };

  return (
    <Modal
      open={open}
      title={t('employees.addTitle')}
      okText={t('common.save')}
      cancelText={t('common.cancel')}
      confirmLoading={loading}
      onOk={(): void => void form.submit()}
      onCancel={handleCancel}
      okButtonProps={{ 'data-qa': 'employees-add-submit' }}
      data-qa="employees-add-modal"
      destroyOnClose
    >
      {parsedError && (
        <Alert
          type="error"
          showIcon
          message={parsedError.message}
          data-qa="employees-add-error"
          style={{ marginBottom: 16 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        requiredMark={false}
        initialValues={{ role: 'viewer' }}
      >
        <Form.Item
          name="name"
          label={t('employees.columnName')}
          rules={[{ required: true, message: t('auth.register.adminNameRequired') }]}
        >
          <Input data-qa="employees-add-name" />
        </Form.Item>

        <Form.Item
          name="email"
          label={t('employees.columnEmail')}
          rules={[
            { required: true, message: t('auth.register.emailRequired') },
            { type: 'email', message: t('auth.register.emailInvalid') },
          ]}
        >
          <Input type="email" data-qa="employees-add-email" />
        </Form.Item>

        <Form.Item
          name="password"
          label={t('auth.register.password')}
          rules={[
            { required: true, message: t('auth.register.passwordRequired') },
            { min: 8, message: t('auth.register.passwordTooShort') },
          ]}
        >
          <Input.Password autoComplete="new-password" data-qa="employees-add-password" />
        </Form.Item>

        <Form.Item name="role" label={t('employees.columnRole')}>
          <Select
            data-qa="employees-add-role"
            options={ROLE_NAMES.map((role) => ({ value: role, label: t(ROLE_LABEL_KEYS[role]) }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
