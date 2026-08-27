/**
 * Authentication context.
 *
 * Holds the signed in user for the React view layer. The frontend never makes
 * the final authorisation decision: it hides controls for convenience while the
 * backend enforces every rule (NFR-B, Coding Standard 3.6).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, clearToken, getToken, setToken } from '../../services/apiClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .get('/auth/me')
      .then(setUser)
      .catch(() => {
        clearToken();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (identifier, password) => {
    const data = await api.post('/auth/login', { identifier, password }, { auth: false });
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      clearToken();
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      setUser,
      isAuthenticated: Boolean(user),
      hasRole: (...roles) => Boolean(user) && roles.includes(user.role),
    }),
    [user, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Read the authentication context.
 * @returns {{user: object|null, loading: boolean, login: Function, logout: Function, isAuthenticated: boolean, hasRole: Function}}
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider.');
  }
  return context;
}
