import { Button, Result } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

/** Страница 404. */
export default function NotFoundPage(): JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="404"
      subTitle={t('error.notFound')}
      data-qa="not-found-page"
      extra={
        <Button type="primary" onClick={(): void => void navigate('/')} data-qa="not-found-home">
          {t('error.goHome')}
        </Button>
      }
    />
  );
}
