import App from '@/App';
// Импорт до рендера: i18n должен быть проинициализирован раньше первого
// useTranslation, иначе компоненты отрисуются с пустыми переводами.
import '@/i18n';
import '@/styles.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

const container = document.getElementById('root');
if (!container) {
  throw new Error('Не найден элемент #root — проверьте index.html');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
