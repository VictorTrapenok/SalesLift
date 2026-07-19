import type { CurrentUser } from '@/hooks/useCurrentUser';
import { toBackendLocale } from '@/i18n';
import { parseGraphQLError } from '@/utils/graphqlError';
import { useMutation } from '@apollo/client';
import { Alert, App, Button, Form, Input } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { UPDATE_PROFILE_MUTATION } from '../queries';

const { TextArea } = Input;

/** Поля формы профиля. */
interface ProfileFormValues {
  name: string;
  bio: string | null;
}

interface ProfileFormProps {
  currentUser: CurrentUser;
}

/**
 * Форма имени и «о себе».
 *
 * E-mail показан, но не редактируется: это логин, и менять его без
 * подтверждения по почте — способ потерять доступ.
 *
 * Вместе с профилем уезжает язык интерфейса: он определяет, на каком языке
 * бэкенд присылает ошибки. Отдельного поля в форме нет — язык выбирается
 * переключателем в шапке, а сюда попадает его текущее значение.
 */
export default function ProfileForm({ currentUser }: ProfileFormProps): JSX.Element {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm<ProfileFormValues>();

  const [updateProfile, { loading, error }] = useMutation(UPDATE_PROFILE_MUTATION, {
    onCompleted: (): void => void message.success(t('profile.bioSaved')),
    // Ошибку показываем в форме; без обработчика Apollo бросит исключение
    // в рендер и уронит страницу.
    onError: (err): void => {
      console.error('Не удалось сохранить профиль', err);
    },
  });

  const parsedError = parseGraphQLError(error);

  const handleSubmit = (values: ProfileFormValues): void => {
    void updateProfile({
      variables: {
        input: {
          name: values.name,
          bio: values.bio ?? '',
          locale: toBackendLocale(i18n.language),
        },
      },
    });
  };

  return (
    <>
      {parsedError && (
        <Alert
          type="error"
          showIcon
          message={parsedError.message}
          data-qa="profile-error"
          style={{ marginBottom: 16 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        requiredMark={false}
        initialValues={{ name: currentUser.name, bio: currentUser.bio }}
        style={{ maxWidth: 480 }}
      >
        <Form.Item
          name="name"
          label={t('profile.name')}
          rules={[{ required: true, message: t('auth.register.adminNameRequired') }]}
        >
          <Input data-qa="profile-name" />
        </Form.Item>

        <Form.Item label={t('profile.email')}>
          <Input value={currentUser.email} disabled data-qa="profile-email" />
        </Form.Item>

        <Form.Item name="bio" label={t('profile.bio')}>
          <TextArea rows={4} maxLength={1000} placeholder={t('profile.bioPlaceholder')} data-qa="profile-bio" />
        </Form.Item>

        <Button type="primary" htmlType="submit" loading={loading} data-qa="profile-submit">
          {t('common.save')}
        </Button>
      </Form>
    </>
  );
}
