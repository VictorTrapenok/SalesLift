import { BRAND } from '@/constants/brand';
import { saveToken } from '@/utils/auth';
import { parseGraphQLError } from '@/utils/graphqlError';
import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { useMutation } from '@apollo/client';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';
import { LOGIN_MUTATION } from './queries';

const { Title, Text } = Typography;

interface LoginFormValues {
  email: string;
  password: string;
}

/**
 * Страница входа.
 *
 * Форма содержит только e-mail и пароль: компания определяется по e-mail
 * (он глобально уникален). Поля «компания» нет и не должно быть — см.
 * docs/adr/0001-tenant-resolution.md.
 */
export default function LoginPage(): JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [form] = Form.useForm<LoginFormValues>();

  const [login, { loading, error }] = useMutation(LOGIN_MUTATION, {
    onCompleted: (data): void => {
      saveToken(data.resolverAuthLogin.token);
      void navigate(BRAND.homePage, { replace: true });
    },
    // Ошибку показываем в форме; без обработчика Apollo бросит исключение
    // в рендер и уронит страницу.
    onError: (err): void => {
      console.error('Не удалось войти', err);
    },
  });

  const parsedError = parseGraphQLError(error);

  const handleSubmit = (values: LoginFormValues): void => {
    void login({ variables: { input: { email: values.email, password: values.password } } });
  };

  return (
    <div className="auth-page" data-qa="login-page">
      <Card className="auth-card">
        <Title level={3} data-qa="login-title">
          {t('auth.login.title')}
        </Title>
        <Text type="secondary">{t('auth.login.subtitle')}</Text>

        {parsedError && (
          <Alert
            type="error"
            showIcon
            message={parsedError.message}
            data-qa="login-error"
            style={{ marginTop: 16 }}
          />
        )}

        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 24 }} requiredMark={false}>
          <Form.Item
            name="email"
            label={t('auth.login.email')}
            rules={[{ required: true, message: t('auth.login.emailRequired') }]}
          >
            <Input prefix={<MailOutlined />} type="email" autoComplete="email" data-qa="login-email" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            label={t('auth.login.password')}
            rules={[{ required: true, message: t('auth.login.passwordRequired') }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              autoComplete="current-password"
              data-qa="login-password"
              size="large"
            />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={loading} block size="large" data-qa="login-submit">
            {t('auth.login.submit')}
          </Button>
        </Form>

        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <Text type="secondary">{t('auth.login.noAccount')} </Text>
          <Link to="/register" data-qa="login-register-link">
            {t('auth.login.registerLink')}
          </Link>
        </div>
      </Card>
    </div>
  );
}
