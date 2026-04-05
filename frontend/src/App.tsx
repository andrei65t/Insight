import { useState, useEffect } from 'react';
import { LoginView } from './views/Login';
import { RegisterView } from './views/Register';
import { DashboardView } from './views/Dashboard';
import { CompanyDashboardView } from './views/CompanyDashboard';
import { api } from './lib/api';

function App() {
  const [page, setPage] = useState('login');
  const [selectedCompany, setSelectedCompany] = useState<string>('');

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
          setSelectedCompany('');
          return;
        }

        const params = new URLSearchParams(window.location.search);
        const encodedCompany = (params.get('company') || '').trim();
        const decodedCompany = decodeURIComponent(encodedCompany);
        if (decodedCompany) {
          setSelectedCompany(decodedCompany);
          setPage('company-dashboard');
          return;
        }

        setPage('dashboard');
        setSelectedCompany('');
        return;
      }

      if (path.startsWith('/dashboard/company/')) {
        if (!token) {
          window.history.replaceState({}, '', '/login');
          setPage('login');
          setSelectedCompany('');
          return;
        }

        const encodedName = path.replace('/dashboard/company/', '').trim();
        const decodedName = decodeURIComponent(encodedName || '');
        if (!decodedName) {
          window.history.replaceState({}, '', '/dashboard');
          setPage('dashboard');
          setSelectedCompany('');
          return;
        }

        // Rewrite old deep-link format to query format to avoid refresh 404 on some static servers.
        const encodedCompany = encodeURIComponent(decodedName);
        window.history.replaceState({}, '', `/dashboard?company=${encodedCompany}`);
        setSelectedCompany(decodedName);
        setPage('company-dashboard');
        return;
      }

      if (path === '/register') {
        setPage('register');
        setSelectedCompany('');
        return;
      }

      setPage('login');
      setSelectedCompany('');
    };

    window.addEventListener('popstate', handleNavigation);
    handleNavigation();

    return () => window.removeEventListener('popstate', handleNavigation);
  }, []);

  if (page === 'dashboard') return <DashboardView />;
  if (page === 'company-dashboard' && selectedCompany) {
    return <CompanyDashboardView companyName={selectedCompany} />;
  }
  if (page === 'register') return <RegisterView />;
  return <LoginView />;
}

export default App;
