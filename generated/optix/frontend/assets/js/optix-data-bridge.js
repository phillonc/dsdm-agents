/**
 * OPTIX Data Bridge
 * Handles API communication and real-time data subscriptions
 * Version: 1.0
 */

const OPTIXDataBridge = (function() {
  'use strict';

  // API Configuration
  const CONFIG = {
    API_BASE: 'http://localhost:8000/api/v1',
    GEX_API_BASE: 'http://localhost:8001/api/v1',
    GENUI_API_BASE: 'http://localhost:8004/api/v1',
    WS_BASE: 'ws://localhost:8000/ws',
    GENUI_WS_BASE: 'ws://localhost:8004/ws',
    REQUEST_TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
  };

  // WebSocket connections
  const websockets = new Map();
  const subscriptions = new Map();

  // Request cache
  const cache = new Map();
  const CACHE_TTL = 60000; // 1 minute default

  /**
   * Get authentication headers
   */
  function getAuthHeaders() {
    const token = localStorage.getItem('optix_access_token');
    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Make an HTTP request with retry logic
   */
  async function request(endpoint, options = {}) {
    const {
      method = 'GET',
      body = null,
      params = null,
      baseUrl = CONFIG.API_BASE,
      useCache = false,
      cacheTTL = CACHE_TTL,
      retries = CONFIG.RETRY_ATTEMPTS,
    } = options;

    // Build URL with query params
    let url = `${baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    // Check cache for GET requests
    const cacheKey = `${method}:${url}`;
    if (useCache && method === 'GET') {
      const cached = cache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < cacheTTL) {
        return cached.data;
      }
    }

    // Request options
    const fetchOptions = {
      method,
      headers: getAuthHeaders(),
    };

    if (body && method !== 'GET') {
      fetchOptions.body = JSON.stringify(body);
    }

    // Retry logic
    let lastError;
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

        const response = await fetch(url, {
          ...fetchOptions,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Handle 401 - token refresh
        if (response.status === 401) {
          const refreshed = await refreshToken();
          if (refreshed) {
            // Retry with new token
            fetchOptions.headers = getAuthHeaders();
            const retryResponse = await fetch(url, fetchOptions);
            if (!retryResponse.ok) {
              throw new Error(`HTTP ${retryResponse.status}: ${retryResponse.statusText}`);
            }
            return await retryResponse.json();
          } else {
            // Redirect to login
            window.location.href = '/pages/auth/login.html';
            throw new Error('Session expired');
          }
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Cache successful GET requests
        if (useCache && method === 'GET') {
          cache.set(cacheKey, { data, timestamp: Date.now() });
        }

        return data;

      } catch (error) {
        lastError = error;
        if (error.name === 'AbortError') {
          throw new Error('Request timeout');
        }
        if (attempt < retries - 1) {
          await sleep(CONFIG.RETRY_DELAY * (attempt + 1));
        }
      }
    }

    throw lastError;
  }

  /**
   * Refresh access token
   */
  async function refreshToken() {
    const refreshToken = localStorage.getItem('optix_refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${CONFIG.API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('optix_access_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('optix_refresh_token', data.refresh_token);
        }
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    // Clear tokens on failure
    localStorage.removeItem('optix_access_token');
    localStorage.removeItem('optix_refresh_token');
    return false;
  }

  /**
   * Subscribe to real-time updates via WebSocket
   */
  function subscribe(channel, callback, options = {}) {
    const { wsBase = CONFIG.WS_BASE } = options;
    const wsUrl = `${wsBase}/${channel}`;

    // Check for existing subscription
    if (subscriptions.has(channel)) {
      subscriptions.get(channel).callbacks.push(callback);
      return () => unsubscribe(channel, callback);
    }

    // Create new WebSocket connection
    const ws = new WebSocket(wsUrl);
    const subscription = {
      ws,
      callbacks: [callback],
      reconnectAttempts: 0,
    };

    ws.onopen = () => {
      console.log(`WebSocket connected: ${channel}`);
      subscription.reconnectAttempts = 0;

      // Send auth token if available
      const token = localStorage.getItem('optix_access_token');
      if (token) {
        ws.send(JSON.stringify({ type: 'auth', token }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        subscription.callbacks.forEach(cb => cb(data));
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error: ${channel}`, error);
    };

    ws.onclose = () => {
      console.log(`WebSocket closed: ${channel}`);

      // Reconnect logic
      if (subscription.reconnectAttempts < 5) {
        subscription.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, subscription.reconnectAttempts), 30000);
        setTimeout(() => {
          if (subscriptions.has(channel)) {
            const callbacks = subscription.callbacks;
            subscriptions.delete(channel);
            callbacks.forEach(cb => subscribe(channel, cb, options));
          }
        }, delay);
      }
    };

    subscriptions.set(channel, subscription);
    websockets.set(channel, ws);

    // Return unsubscribe function
    return () => unsubscribe(channel, callback);
  }

  /**
   * Unsubscribe from a channel
   */
  function unsubscribe(channel, callback) {
    const subscription = subscriptions.get(channel);
    if (!subscription) return;

    subscription.callbacks = subscription.callbacks.filter(cb => cb !== callback);

    // Close WebSocket if no more callbacks
    if (subscription.callbacks.length === 0) {
      subscription.ws.close();
      subscriptions.delete(channel);
      websockets.delete(channel);
    }
  }

  /**
   * Close all WebSocket connections
   */
  function closeAll() {
    websockets.forEach(ws => ws.close());
    websockets.clear();
    subscriptions.clear();
  }

  /**
   * Utility: Sleep
   */
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Clear cache
   */
  function clearCache() {
    cache.clear();
  }

  // ==========================================
  // API Methods
  // ==========================================

  /**
   * Authentication
   */
  const auth = {
    async login(email, password) {
      return request('/auth/login', {
        method: 'POST',
        body: { email, password },
      });
    },

    async register(email, password, firstName, lastName, acceptedTos = true) {
      return request('/auth/register', {
        method: 'POST',
        body: {
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          accepted_tos: acceptedTos
        },
      });
    },

    async logout() {
      try {
        await request('/auth/logout', { method: 'POST' });
      } finally {
        localStorage.removeItem('optix_access_token');
        localStorage.removeItem('optix_refresh_token');
        closeAll();
      }
    },

    async getCurrentUser() {
      return request('/users/me');
    },

    isAuthenticated() {
      return !!localStorage.getItem('optix_access_token');
    },
  };

  /**
   * Market Data
   */
  const quotes = {
    async get(symbol) {
      return request(`/quotes/${symbol}`, { useCache: true, cacheTTL: 5000 });
    },

    async getBatch(symbols) {
      return request('/quotes', {
        params: { symbols: symbols.join(',') },
        useCache: true,
        cacheTTL: 5000,
      });
    },

    subscribeRealtime(symbols, callback) {
      return subscribe(`quotes?symbols=${symbols.join(',')}`, callback);
    },
  };

  /**
   * Options Data
   */
  const options = {
    async getExpirations(symbol) {
      return request(`/options/expirations/${symbol}`, { useCache: true, cacheTTL: 300000 });
    },

    async getChain(symbol, expiration = null) {
      const params = expiration ? { expiration } : {};
      return request(`/options/chain/${symbol}`, { params, useCache: true, cacheTTL: 10000 });
    },
  };

  /**
   * GEX Data
   */
  const gex = {
    async calculate(symbol) {
      return request(`/gex/calculate/${symbol}`, {
        baseUrl: CONFIG.GEX_API_BASE,
        useCache: true,
        cacheTTL: 30000,
      });
    },

    async getHeatmap(symbol) {
      return request(`/gex/heatmap/${symbol}`, {
        baseUrl: CONFIG.GEX_API_BASE,
        useCache: true,
        cacheTTL: 30000,
      });
    },

    async getGammaFlip(symbol) {
      return request(`/gex/gamma-flip/${symbol}`, {
        baseUrl: CONFIG.GEX_API_BASE,
        useCache: true,
        cacheTTL: 30000,
      });
    },

    async getHistorical(symbol, days = 30) {
      return request(`/historical/${symbol}`, {
        baseUrl: CONFIG.GEX_API_BASE,
        params: { days },
        useCache: true,
        cacheTTL: 60000,
      });
    },
  };

  /**
   * Watchlists
   */
  const watchlists = {
    async getAll() {
      return request('/watchlists');
    },

    async get(id) {
      return request(`/watchlists/${id}`);
    },

    async create(name, symbols = []) {
      return request('/watchlists', {
        method: 'POST',
        body: { name, symbols },
      });
    },

    async update(id, data) {
      return request(`/watchlists/${id}`, {
        method: 'PATCH',
        body: data,
      });
    },

    async delete(id) {
      return request(`/watchlists/${id}`, { method: 'DELETE' });
    },

    async addSymbol(id, symbol) {
      return request(`/watchlists/${id}/symbols`, {
        method: 'POST',
        body: { symbol },
      });
    },

    async removeSymbol(id, symbol) {
      return request(`/watchlists/${id}/symbols`, {
        method: 'DELETE',
        body: { symbol },
      });
    },
  };

  /**
   * Portfolio
   */
  const portfolio = {
    async get() {
      return request('/portfolio');
    },

    async getPositions() {
      return request('/portfolio/positions');
    },

    async getPerformance() {
      return request('/portfolio/performance');
    },

    async sync() {
      return request('/portfolio/sync', { method: 'POST' });
    },

    subscribeRealtime(callback) {
      return subscribe('portfolio', callback);
    },
  };

  /**
   * Alerts
   */
  const alerts = {
    async getAll() {
      return request('/alerts');
    },

    async create(alertData) {
      return request('/alerts', {
        method: 'POST',
        body: alertData,
      });
    },

    async delete(id) {
      return request(`/alerts/${id}`, { method: 'DELETE' });
    },

    async enable(id) {
      return request(`/alerts/${id}/enable`, { method: 'PATCH' });
    },

    async disable(id) {
      return request(`/alerts/${id}/disable`, { method: 'PATCH' });
    },
  };

  /**
   * Generative UI
   */
  const genui = {
    async generate(query, context = {}) {
      return request('/genui/generate', {
        baseUrl: CONFIG.GENUI_API_BASE,
        method: 'POST',
        body: { query, context },
      });
    },

    async generateStream(query, context = {}, onProgress) {
      const response = await fetch(`${CONFIG.GENUI_API_BASE}/genui/generate/stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ query, context }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n').filter(line => line.startsWith('data:'));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(5));
            onProgress(data);
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    },

    async refine(generationId, refinement) {
      return request('/genui/refine', {
        baseUrl: CONFIG.GENUI_API_BASE,
        method: 'POST',
        body: { generation_id: generationId, refinement },
      });
    },

    async getComponents() {
      return request('/genui/components', {
        baseUrl: CONFIG.GENUI_API_BASE,
        useCache: true,
        cacheTTL: 300000,
      });
    },

    subscribeGeneration(generationId, callback) {
      return subscribe(`genui/${generationId}`, callback, { wsBase: CONFIG.GENUI_WS_BASE });
    },
  };

  // ==========================================
  // Public API
  // ==========================================
  return {
    // Configuration
    CONFIG,

    // Core methods
    request,
    subscribe,
    unsubscribe,
    closeAll,
    clearCache,

    // API modules
    auth,
    quotes,
    options,
    gex,
    watchlists,
    portfolio,
    alerts,
    genui,

    // Utility
    getAuthHeaders,
    isAuthenticated: auth.isAuthenticated,
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OPTIXDataBridge;
}

// Make available globally
window.OPTIXDataBridge = OPTIXDataBridge;
