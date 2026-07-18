import { parseGraphQLError } from '@/utils/graphqlError';
import { useMutation } from '@apollo/client';
import { Alert, App, Button, Form, Input } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { CHANGE_PASSWORD_MUTATION } from '../queries';

/** Поля формы смены пароля. */
interface ChangePasswordFormValues {
  currentPassword: string;
  newPassword: string;
}

/**
 * Форма смены собственного пароля.
 *
 * Текущий пароль спрашивается даже у вошедшего: иначе чужая незакрытая сессия
 * позволяет забрать аккаунт себе. Проверяет его бэкенд, здесь поле только
 * обязательное.
 */
export default function ChangePasswordForm(): JSX.Element {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm<ChangePasswordFormValues>();

  const [changePassword, { loading, error }] = useMutation(CHANGE_PASSWORD_MUTATION, {
    onCompleted: (): void => {
      // Пароли в полях не оставляем: страница живёт до перехода, а поля
      // автозаполнение браузера подхватывает охотно.
      form.resetFields();
      void message.success(t('profile.passwordChanged'));
    },
    // Ошибку показываем в форме; без обработчика Apollo бросит исключение
    // в рендер и уронит страницу.
    onError: (err): void => {
      console.error('Не удалось сменить пароль', err);
    },
  });

  const parsedError = parseGraphQLError(error);

  const handleSubmit = (values: ChangePasswordFormValues): void => {
    void changePassword({ variables: { input: values } });
  };

  return (
    <>
      {parsedError && (
        <Alert
          type="error"
          showIcon
          message={parsedError.message}
          data-qa="profile-password-error"
          style={{ marginBottom: 16 }}
        />
      )}

      <Form form={form} layout="vertical" onFinish={handleSubmit} requiredMark={false} style={{ maxWidth: 480 }}>
        <Form.Item
          name="currentPassword"
          label={t('profile.currentPassword')}
          rules={[{ required: true, message: t('profile.currentPasswordRequired') }]}
        >
          <Input.Password autoComplete="current-password" data-qa="profile-current-password" />
        </Form.Item>

        <Form.Item
          name="newPassword"
          label={t('profile.newPassword')}
          rules={[
            { required: true, message: t('profile.newPasswordRequired') },
            { min: 8, message: t('auth.register.passwordTooShort') },
          ]}
        >
          <Input.Password autoComplete="new-password" data-qa="profile-new-password" />
        </Form.Item>

        <Button type="primary" htmlType="submit" loading={loading} data-qa="profile-password-submit">
          {t('profile.changePassword')}
        </Button>
      </Form>
    </>
  );
}
