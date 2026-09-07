import { useState, useEffect } from 'react';

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('api_token'));
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const handleExpired = () => {
      setToken(null);
      window.location.href = '/auth';
    };
    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, []);

  const login = (newToken: string) => {
    localStorage.setItem('api_token', newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem('api_token');
    setToken(null);
    window.location.href = '/auth';
  };

  return { token, isLoading, login, logout };
}