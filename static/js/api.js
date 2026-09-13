/**
 * api.js — shared Fetch API wrapper for FoodFlow.
 * - Prefixes requests with the API base URL.
 * - Injects the Bearer auth token (read from sessionStorage via auth.js) when present.
 * - Normalizes JSON parsing and error shapes so callers can rely on one error format.
 *
 * Usage:
 *   const { data, error } = await FoodFlowAPI.get('/api/restaurants');
 *   const { data, error } = await FoodFlowAPI.post('/api/cart/items', { menu_item_id, quantity });
 */
(function (global) {
  const API_BASE = ''; // same-origin FastAPI backend; change if the API is hosted elsewhere

  function getAuthToken() {
    try {
      return sessionStorage.getItem('foodflow_auth_token');
    } catch (e) {
      return null;
    }
  }

  /**
   * Normalized error shape: { message, status, details }
   */
  function normalizeError(status, payload, fallbackMessage) {
    let message = fallbackMessage || 'Something went wrong. Please try again.';
    let details = null;
    if (payload && typeof payload === 'object') {
      if (typeof payload.detail === 'string') message = payload.detail;
      else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
        details = payload.detail;
      } else if (typeof payload.message === 'string') message = payload.message;
    }
    if (status === 0) message = 'Network error — check your connection and try again.';
    if (status === 401) message = message === fallbackMessage ? 'Please log in to continue.' : message;
    if (status === 403) message = message === fallbackMessage ? 'You do not have permission to do that.' : message;
    if (status === 404) message = message === fallbackMessage ? 'We could not find what you were looking for.' : message;
    if (status >= 500) message = 'Our servers are having trouble. Please try again shortly.';
    return { message, status, details };
  }

  async function request(method, path, body, opts) {
    opts = opts || {};
    const headers = Object.assign({ 'Content-Type': 'application/json', Accept: 'application/json' }, opts.headers || {});
    const token = getAuthToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;

    let response;
    try {
      response = await fetch(API_BASE + path, {
        method,
        headers,
        credentials: 'same-origin',
        body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
        signal: opts.signal
      });
    } catch (networkErr) {
      return { data: null, error: normalizeError(0, null) };
    }

    let payload = null;
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (e) {
        payload = null;
      }
    }

    if (!response.ok) {
      return { data: null, error: normalizeError(response.status, payload), status: response.status };
    }

    return { data: payload, error: null, status: response.status };
  }

  const FoodFlowAPI = {
    get: (path, opts) => request('GET', path, null, opts),
    post: (path, body, opts) => request('POST', path, body, opts),
    put: (path, body, opts) => request('PUT', path, body, opts),
    patch: (path, body, opts) => request('PATCH', path, body, opts),
    delete: (path, opts) => request('DELETE', path, null, opts),
    getAuthToken
  };

  global.FoodFlowAPI = FoodFlowAPI;
})(window);
