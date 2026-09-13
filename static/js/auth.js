/**
 * auth.js — authentication state for FoodFlow.
 * Security note (task.md §18/16): the auth token lives ONLY in sessionStorage
 * (cleared when the tab closes), never in localStorage, and passwords are
 * never persisted client-side. The current-user object (non-sensitive
 * profile fields only) is cached in sessionStorage for quick UI rendering.
 */
(function (global) {
  const TOKEN_KEY = 'foodflow_auth_token';
  const USER_KEY = 'foodflow_current_user';

  function getToken() {
    try { return sessionStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }
  function setToken(token) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* storage unavailable — auth simply won't persist across reload */ }
  }
  function getCurrentUser() {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function setCurrentUser(user) {
    try {
      if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
      else sessionStorage.removeItem(USER_KEY);
    } catch (e) { /* ignore */ }
  }
  function isLoggedIn() {
    return !!getToken();
  }

  async function login(email, password) {
    const { data, error } = await FoodFlowAPI.post('/api/auth/login', { email, password });
    if (error) return { ok: false, error };
    // Backend is expected to return { token, user }. Degrade gracefully if shape differs.
    const token = data && (data.token || data.access_token);
    const user = data && (data.user || data);
    if (token) setToken(token);
    if (user) setCurrentUser(user);
    return { ok: true, user };
  }

  async function register(payload) {
    const { data, error } = await FoodFlowAPI.post('/api/auth/register', payload);
    if (error) return { ok: false, error };
    const token = data && (data.token || data.access_token);
    const user = data && (data.user || data);
    if (token) setToken(token);
    if (user) setCurrentUser(user);
    return { ok: true, user };
  }

  async function logout() {
    try { await FoodFlowAPI.post('/api/auth/logout', {}); } catch (e) { /* best effort */ }
    setToken(null);
    setCurrentUser(null);
  }

  async function refreshCurrentUser() {
    if (!isLoggedIn()) return null;
    const { data, error } = await FoodFlowAPI.get('/api/auth/me');
    if (error) return null;
    setCurrentUser(data);
    return data;
  }

  global.FoodFlowAuth = {
    getToken,
    getCurrentUser,
    setCurrentUser,
    isLoggedIn,
    login,
    register,
    logout,
    refreshCurrentUser
  };
})(window);
