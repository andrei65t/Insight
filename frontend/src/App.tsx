import { useState, useEffect } from 'react';
import { LoginView } from './views/Login';
import { RegisterView } from './views/Register';
import { DashboardView } from './views/Dashboard';
import { api } from './lib/api';

function App() {
  const [page, setPage] = useState('login');

  useEffect(() => {
    const handleNavigation = () => {
      const path = window.location.pathname;
      const token = api.getToken();

      if (path === '/') {
        if (token) {
          window.history.replaceState({}, '', '/dashboard');
          setPage('dashboard');
          return;
        }
        window.history.replaceState({}, '', '/login');
        setPage('login');
        return;
      }

      if (path === '/dashboard') {
        if (!token) {
          window.history.replaceState({}, '', '/login');
          setPage('login');
          return;
        }
        setPage('dashboard');
        return;
      }

      if (path === '/register') {
        setPage('register');
        return;
      }

      setPage('login');
    };

    window.addEventListener('popstate', handleNavigation);
    handleNavigation();

    return () => window.removeEventListener('popstate', handleNavigation);
  }, []);

  if (page === 'dashboard') return <DashboardView />;
  if (page === 'register') return <RegisterView />;
  return <LoginView />;
}

export default App;
