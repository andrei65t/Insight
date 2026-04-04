import { useState, useEffect } from 'react';
import { LoginView } from './views/Login';
import { RegisterView } from './views/Register';
import { DashboardView } from './views/Dashboard';

function App() {
  const [page, setPage] = useState('login');

  useEffect(() => {
    const handleNavigation = () => {
      const path = window.location.pathname;
      if (path === '/dashboard') setPage('dashboard');
      else if (path === '/register') setPage('register');
      else setPage('login');
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
