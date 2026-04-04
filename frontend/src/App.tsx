import { useState, useEffect } from 'react'
import { LoginView } from './views/Login'
import { DashboardView } from './views/Dashboard'

function App() {
  const [page, setPage] = useState('login')

  useEffect(() => {
    const handleNavigation = () => {
      const path = window.location.pathname
      if (path === '/dashboard') setPage('dashboard')
      else setPage('login')
    }
    
    window.addEventListener('popstate', handleNavigation)
    handleNavigation() // Initial check
    
    return () => window.removeEventListener('popstate', handleNavigation)
  }, [])

  return (
    <>
      {page === 'login' ? <LoginView /> : <DashboardView />}
    </>
  )
}

export default App
