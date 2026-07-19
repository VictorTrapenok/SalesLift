import { UserPermissions } from '@/graphql/generated/graphql';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { parseGraphQLError } from '@/utils/graphqlError';
import { useMutation, useQuery } from '@apollo/client';
import { Alert, App, Button, Card, Form, Input, Skeleton, Typography } from 'antd';
import { useEffect, type JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { ORG_SETTINGS_QUERY, UPDATE_ORG_SETTINGS_MUTATION } from './queries';

const { Title } = Typography;

/** Поля формы настроек компании. */
interface OrgSettingsFormValues {
  name: string;
  country: string | null;
  website: string | null;
  contactPhone: string | null;
}

/**
 * Настройки компании.
 *
 * Компания в запросы не передаётся: бэкенд берёт её из токена. Форма
 * блокируется без права `Permission_org_settings_edit` — смотреть настройки
 * может и менеджер, менять их только администратор.
 */
export default function OrgSettingsPage(): JSX.Element {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { hasPermission } = useCurrentUser();
  const [form] = Form.useForm<OrgSettingsFormValues>();

  const canEdit = hasPermission(UserPermissions.Permission_org_settings_edit);

  const { data, loading, error: queryError } = useQuery(ORG_SETTINGS_QUERY);
  const settings = data?.resolverOrgSettingsGet;

  const [updateSettings, { loading: saving, error: saveError }] = useMutation(UPDATE_ORG_SETTINGS_MUTATION, {
    onCompleted: (): void => void message.success(t('orgSettings.saved')),
    // Ошибку показываем в форме; без обработчика Apollo бросит исключение
    // в рендер и уронит страницу.
    onError: (err): void => {
      console.error('Не удалось сохранить настройки компании', err);
    },
  });

  // Значения проставляются здесь, а не через initialValues: форма монтируется
  // раньше, чем приходит ответ, и initialValues уже не подхватятся.
  useEffect((): void => {
    if (settings) {
      // Поля перечислены поимённо: `settings` содержит ещё `id` и
      // `__typename`, и они уехали бы в input мутации, которого таких полей
      // не знает.
      form.setFieldsValue({
        name: settings.name,
        country: settings.country,
        website: settings.website,
        contactPhone: settings.contactPhone,
      });
    }
  }, [settings, form]);

  const parsedError = parseGraphQLError(queryError ?? saveError);

  const handleSubmit = (values: OrgSettingsFormValues): void => {
    void updateSettings({
      variables: {
        input: {
          name: values.name,
          country: values.country,
          website: values.website,
          contactPhone: values.contactPhone,
        },
      },
    });
  };

  return (
    <Card data-qa="org-settings-page">
      <Title level={4}>{t('orgSettings.title')}</Title>

      {parsedError && (
        <Alert
          type="error"
          showIcon
          message={parsedError.message}
          data-qa="org-settings-error"
          style={{ marginBottom: 16 }}
        />
      )}

      {loading ? (
        <Skeleton active data-qa="org-settings-loading" />
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark={false}
          disabled={!canEdit}
          style={{ maxWidth: 480 }}
        >
          <Form.Item
            name="name"
            label={t('orgSettings.companyName')}
            rules={[{ required: true, message: t('orgSettings.companyNameRequired') }]}
          >
            <Input data-qa="org-settings-name" />
          </Form.Item>

          <Form.Item name="country" label={t('orgSettings.country')}>
            <Input maxLength={2} placeholder={t('orgSettings.countryPlaceholder')} data-qa="org-settings-country" />
          </Form.Item>

          <Form.Item name="website" label={t('orgSettings.website')}>
            <Input data-qa="org-settings-website" />
          </Form.Item>

          <Form.Item name="contactPhone" label={t('orgSettings.contactPhone')}>
            <Input data-qa="org-settings-phone" />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={saving} data-qa="org-settings-submit">
            {t('common.save')}
          </Button>
        </Form>
      )}
    </Card>
  );
}
