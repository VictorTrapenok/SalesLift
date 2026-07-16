import LangSwitch from '@/components/LangSwitch';
import { BRAND } from '@/constants/brand';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { clearToken } from '@/utils/auth';
import { LogoutOutlined, SettingOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { useApolloClient } from '@apollo/client';
import { Dropdown, Layout, Menu, Space, Typography, type MenuProps } from 'antd';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

/**
 * Каркас кабинета: боковое меню, шапка с профилем и языком, область страницы.
 *
 * Пункты меню не скрываются по правам: на этом этапе все три страницы доступны
 * любому аутентифицированному сотруднику, а гейтинг конкретных действий делает
 * HasPermission. Когда появятся страницы под ограниченный доступ — фильтровать
 * items через useCurrentUser().hasPermission.
 */
export default function AppLayout(): JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser } = useCurrentUser();
  const apolloClient = useApolloClient();

  const menuItems: MenuProps['items'] = [
    { key: '/employees', icon: <TeamOutlined />, label: t('menu.employees'), 'data-qa': 'menu-employees' },
    { key: '/settings', icon: <SettingOutlined />, label: t('menu.settings'), 'data-qa': 'menu-settings' },
    { key: '/profile', icon: <UserOutlined />, label: t('menu.profile'), 'data-qa': 'menu-profile' },
  ];

  const handleLogout = (): void => {
    clearToken();
    // Чистим кэш: иначе профиль предыдущего пользователя останется в памяти и
    // мелькнёт у следующего до ответа сервера.
    void apolloClient.clearStore().catch((err: unknown) => {
      console.error('Не удалось очистить кэш Apollo при выходе', err);
    });
    void navigate('/login', { replace: true });
  };

  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: t('menu.profile'), 'data-qa': 'user-menu-profile' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: t('common.logout'), 'data-qa': 'user-menu-logout' },
  ];

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }): void => {
    if (key === 'logout') {
      handleLogout();
      return;
    }
    void navigate('/profile');
  };

  return (
    <Layout style={{ minHeight: '100vh' }} data-qa="app-layout">
      <Sider breakpoint="lg" collapsedWidth="0" theme="light">
        <div style={{ padding: 16, fontWeight: 600, fontSize: 18 }} data-qa="app-brand">
          {BRAND.name}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }): void => void navigate(key)}
        />
      </Sider>

      <Layout>
        <Header style={{ background: '#fff', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Space size="middle">
            <LangSwitch />
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }} data-qa="user-menu">
                <UserOutlined />
                <Text data-qa="current-user-name">{currentUser?.name}</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: 24 }} data-qa="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
