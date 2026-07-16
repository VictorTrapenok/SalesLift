import AppLayout from '@/components/AppLayout';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import EmployeesPage from '@/pages/Employees';
import LoginPage from '@/pages/Login';
import NotFoundPage from '@/pages/NotFound';
import OrgSettingsPage from '@/pages/OrgSettings';
import ProfilePage from '@/pages/Profile';
import RegisterPage from '@/pages/Register';
import { clearToken, getToken } from '@/utils/auth';
import { Spin } from 'antd';
import type { JSX } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router';

/**
 * Пускает дальше только аутентифицированных.
 *
 * Проверка в два шага: сначала наличие токена (мгновенно, без сети), затем
 * запрос Me. Токен может быть протухшим или подделанным, поэтому его наличие
 * ничего не гарантирует — решает ответ сервера.
 */
function ProtectedRoute(): JSX.Element {
  const { currentUser, loading } = useCurrentUser();

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }} data-qa="route-loading">
        <Spin size="large" />
      </div>
    );
  }

  if (!currentUser) {
    // Токен есть, но профиль не пришёл: протух или пользователя удалили.
    // Чистим токен, иначе получится цикл редиректов.
    clearToken();
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

/** Не пускает уже вошедших на страницы входа и регистрации. */
function PublicOnlyRoute(): JSX.Element {
  if (getToken()) {
    return <Navigate to="/employees" replace />;
  }
  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: <Navigate to="/employees" replace /> },
          { path: '/employees', element: <EmployeesPage /> },
          { path: '/settings', element: <OrgSettingsPage /> },
          { path: '/profile', element: <ProfilePage /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
