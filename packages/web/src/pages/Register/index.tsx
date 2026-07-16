import { BRAND } from '@/constants/brand';
import { toBackendLocale } from '@/i18n';
import { saveToken } from '@/utils/auth';
import { parseGraphQLError } from '@/utils/graphqlError';
import { BankOutlined, LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { useMutation } from '@apollo/client';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';
import { REGISTER_MUTATION } from './queries';

const { Title, Text } = Typography;

/** Минимальная длина пароля. Должна совпадать с MIN_PASSWORD_LENGTH на бэкенде. */
const MIN_PASSWORD_LENGTH = 8;

interface RegisterFormValues {
  companyName: string;
  adminName: string;
  email: string;
  password: string;
}

/**
 * Регистрация компании.
 *
 * Это же и есть сценарий первого запуска: зарегистрировал компанию → стал её
 * администратором → попал в кабинет. Ни сидинга, ни настройки не требуется.
 *
 * Поля «придумайте адрес/slug» нет: у компании нет человекочитаемого
 * идентификатора, только UUID.
 */
export default function RegisterPage(): JSX.Element {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [form] = Form.useForm<RegisterFormValues>();

  const [register, { loading, error }] = useMutation(REGISTER_MUTATION, {
    onCompleted: (data): void => {
      saveToken(data.resolverAuthRegister.token);
      void navigate(BRAND.homePage, { replace: true });
    },
    onError: (err): void => {
      console.error('Не удалось зарегистрировать компанию', err);
    },
  });

  const parsedError = parseGraphQLError(error);

  const handleSubmit = (values: RegisterFormValues): void => {
    void register({
      variables: {
        input: {
          companyName: values.companyName,
          adminName: values.adminName,
          email: values.email,
          password: values.password,
          // Язык интерфейса сохраняется в профиль: серверные ошибки будут
          // приходить на том же языке.
          locale: toBackendLocale(i18n.language),
        },
      },
    });
  };

  return (
    <div className="auth-page" data-qa="register-page">
      <Card className="auth-card">
        <Title level={3} data-qa="register-title">
          {t('auth.register.title')}
        </Title>
        <Text type="secondary">{t('auth.register.subtitle')}</Text>

        {parsedError && (
          <Alert
            type="error"
            showIcon
            message={parsedError.message}
            data-qa="register-error"
            style={{ marginTop: 16 }}
          />
        )}

        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 24 }} requiredMark={false}>
          <Form.Item
            name="companyName"
            label={t('auth.register.companyName')}
            rules={[{ required: true, message: t('auth.register.companyNameRequired') }]}
          >
            <Input prefix={<BankOutlined />} data-qa="register-company-name" size="large" />
          </Form.Item>

          <Form.Item
            name="adminName"
            label={t('auth.register.adminName')}
            rules={[{ required: true, message: t('auth.register.adminNameRequired') }]}
          >
            <Input prefix={<UserOutlined />} autoComplete="name" data-qa="register-admin-name" size="large" />
          </Form.Item>

          <Form.Item
            name="email"
            label={t('auth.register.email')}
            rules={[
              { required: true, message: t('auth.register.emailRequired') },
              { type: 'email', message: t('auth.register.emailInvalid') },
            ]}
          >
            <Input prefix={<MailOutlined />} type="email" autoComplete="email" data-qa="register-email" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            label={t('auth.register.password')}
            rules={[
              { required: true, message: t('auth.register.passwordRequired') },
              { min: MIN_PASSWORD_LENGTH, message: t('auth.register.passwordTooShort') },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              autoComplete="new-password"
              data-qa="register-password"
              size="large"
            />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={loading} block size="large" data-qa="register-submit">
            {t('auth.register.submit')}
          </Button>
        </Form>

        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <Text type="secondary">{t('auth.register.hasAccount')} </Text>
          <Link to="/login" data-qa="register-login-link">
            {t('auth.register.loginLink')}
          </Link>
        </div>
      </Card>
    </div>
  );
}
