/**
 * OPTIX Authentication Module
 * Handles login, logout, token management, and route protection
 * Version: 1.0
 */

const OPTIXAuth = (function() {
  'use strict';

  const TOKEN_KEY = 'optix_access_token';
  const REFRESH_KEY = 'optix_refresh_token';
  const USER_KEY = 'optix_user';

  // Protected routes that require authentication
  const PROTECTED_ROUTES = [
    '/pages/dashboard.html',
    '/pages/watchlist.html',
    '/pages/options.html',
    '/pages/gex.html',
  ];

  // Public routes (no auth required)
  const PUBLIC_ROUTES = [
    '/',
    '/index.html',
    '/pages/auth/login.html',
    '/pages/auth/register.html',
  ];

  /**
   * Initialize auth module
   */
  function init() {
    // Check auth status on page load
    checkAuthStatus();

    // Listen for storage changes (logout from other tabs)
    window.addEventListener('storage', handleStorageChange);
  }

  /**
   * Check authentication status and redirect if needed
   */
  function checkAuthStatus() {
    const isAuthenticated = hasValidToken();
    const currentPath = window.location.pathname;

    // Normalize path (handle /frontend/ prefix)
    const normalizedPath = currentPath.replace('/frontend', '');

    // If on protected route without auth, redirect to login
    if (isProtectedRoute(normalizedPath) && !isAuthenticated) {
      redirectToLogin();
      return false;
    }

    // If on login/register with valid auth, redirect to dashboard
    if (isAuthRoute(normalizedPath) && isAuthenticated) {
      redirectToDashboard();
      return true;
    }

    return isAuthenticated;
  }

  /**
   * Check if user has valid token
   */
  function hasValidToken() {
    const token = getAccessToken();
    if (!token) return false;

    // Check if token is expired
    try {
      const payload = parseJWT(token);
      if (payload.exp && Date.now() >= payload.exp * 1000) {
        // Token expired, try refresh
        return false;
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Parse JWT token
   */
  function parseJWT(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      return {};
    }
  }

  /**
   * Check if path is protected
   */
  function isProtectedRoute(path) {
    return PROTECTED_ROUTES.some(route => path.includes(route.replace('/pages', '')));
  }

  /**
   * Check if path is auth route (login/register)
   */
  function isAuthRoute(path) {
    return path.includes('login') || path.includes('register');
  }

  /**
   * Get access token
   */
  function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * Get refresh token
   */
  function getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY);
  }

  /**
   * Set tokens
   */
  function setTokens(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_KEY, refreshToken);
    }
  }

  /**
   * Clear tokens
   */
  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  /**
   * Get stored user
   */
  function getUser() {
    const userData = localStorage.getItem(USER_KEY);
    return userData ? JSON.parse(userData) : null;
  }

  /**
   * Set user data
   */
  function setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  /**
   * Login user
   */
  async function login(email, password) {
    try {
      const response = await OPTIXDataBridge.auth.login(email, password);

      if (response.access_token) {
        setTokens(response.access_token, response.refresh_token);

        // Fetch user data
        const user = await OPTIXDataBridge.auth.getCurrentUser();
        setUser(user);

        return { success: true, user };
      }

      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      return { success: false, error: error.message || 'Login failed' };
    }
  }

  /**
   * Register user
   * @param {string} email - User email
   * @param {string} password - User password
   * @param {string} name - Full name (will be split into first/last)
   * @param {boolean} acceptedTos - Whether user accepted terms of service
   */
  async function register(email, password, name, acceptedTos = true) {
    try {
      // Split name into first and last name
      const nameParts = name.trim().split(/\s+/);
      const firstName = nameParts[0] || '';
      const lastName = nameParts.slice(1).join(' ') || nameParts[0] || '';

      const response = await OPTIXDataBridge.auth.register(email, password, firstName, lastName, acceptedTos);

      if (response.access_token) {
        setTokens(response.access_token, response.refresh_token);

        // Fetch user data
        const user = await OPTIXDataBridge.auth.getCurrentUser();
        setUser(user);

        return { success: true, user };
      }

      // Registration successful but no auto-login
      if (response.id || response.email) {
        return { success: true, requiresLogin: true };
      }

      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      return { success: false, error: error.message || 'Registration failed' };
    }
  }

  /**
   * Logout user
   */
  async function logout() {
    try {
      await OPTIXDataBridge.auth.logout();
    } catch (e) {
      // Ignore logout errors
    }
    clearTokens();
    OPTIXDataBridge.closeAll();
    redirectToLogin();
  }

  /**
   * Refresh access token
   */
  async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${OPTIXDataBridge.CONFIG.API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    clearTokens();
    return false;
  }

  /**
   * Redirect to login page
   */
  function redirectToLogin(returnUrl = null) {
    const basePath = getBasePath();
    let loginUrl = `${basePath}/pages/auth/login.html`;
    if (returnUrl) {
      loginUrl += `?return=${encodeURIComponent(returnUrl)}`;
    }
    window.location.href = loginUrl;
  }

  /**
   * Redirect to dashboard
   */
  function redirectToDashboard() {
    const basePath = getBasePath();
    window.location.href = `${basePath}/pages/dashboard.html`;
  }

  /**
   * Get base path for the frontend
   */
  function getBasePath() {
    const path = window.location.pathname;
    if (path.includes('/frontend/')) {
      return '/frontend';
    }
    return '';
  }

  /**
   * Handle storage change (cross-tab logout)
   */
  function handleStorageChange(event) {
    if (event.key === TOKEN_KEY && !event.newValue) {
      // Token was removed in another tab
      redirectToLogin();
    }
  }

  /**
   * Get return URL from query params
   */
  function getReturnUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('return');
  }

  /**
   * Password validation
   * Requirements: 8+ chars, uppercase, lowercase, number, special character
   */
  function validatePassword(password) {
    const errors = [];
    if (password.length < 8) {
      errors.push('Password must be at least 8 characters');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain an uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain a lowercase letter');
    }
    if (!/[0-9]/.test(password)) {
      errors.push('Password must contain a number');
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      errors.push('Password must contain a special character (#, @, $, etc.)');
    }
    return errors;
  }

  /**
   * Email validation
   */
  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  // ==========================================
  // Public API
  // ==========================================
  return {
    init,
    login,
    register,
    logout,
    checkAuthStatus,
    hasValidToken,
    getAccessToken,
    getRefreshToken,
    getUser,
    setUser,
    refreshAccessToken,
    redirectToLogin,
    redirectToDashboard,
    getReturnUrl,
    validatePassword,
    validateEmail,
    getBasePath,
  };
})();

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', OPTIXAuth.init);
} else {
  OPTIXAuth.init();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OPTIXAuth;
}

// Make available globally
window.OPTIXAuth = OPTIXAuth;
