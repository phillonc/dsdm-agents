/**
 * OPTIX Component Loader
 * Handles dynamic loading of layout components and GenUI components
 * Version: 1.0
 */

const OPTIXComponentLoader = (function() {
  'use strict';

  // Cache for loaded components
  const componentCache = new Map();

  /**
   * Load HTML component from file
   */
  async function loadComponent(url) {
    // Check cache
    if (componentCache.has(url)) {
      return componentCache.get(url);
    }

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load component: ${url}`);
      }
      const html = await response.text();
      componentCache.set(url, html);
      return html;
    } catch (error) {
      console.error('Component load error:', error);
      return '';
    }
  }

  /**
   * Inject component into element
   */
  async function inject(selector, componentUrl) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`Element not found: ${selector}`);
      return;
    }

    const html = await loadComponent(componentUrl);
    element.innerHTML = html;

    // Execute any scripts in the loaded component
    executeScripts(element);

    // Dispatch event for component initialization
    element.dispatchEvent(new CustomEvent('component:loaded', { bubbles: true }));
  }

  /**
   * Execute scripts in loaded HTML
   */
  function executeScripts(container) {
    const scripts = container.querySelectorAll('script');
    scripts.forEach(oldScript => {
      const newScript = document.createElement('script');
      Array.from(oldScript.attributes).forEach(attr => {
        newScript.setAttribute(attr.name, attr.value);
      });
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
  }

  /**
   * Load standard layout (header + sidebar)
   */
  async function loadLayout() {
    const basePath = OPTIXAuth?.getBasePath() || '';

    // Load header and sidebar in parallel
    await Promise.all([
      inject('#header-container', `${basePath}/components/layout/header.html`),
      inject('#sidebar-container', `${basePath}/components/layout/sidebar.html`),
    ]);

    // Initialize layout interactions
    initLayoutInteractions();
  }

  /**
   * Initialize layout interactions (sidebar toggle, etc.)
   */
  function initLayoutInteractions() {
    // Sidebar toggle
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');

    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainContent?.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
      });

      // Restore saved state
      if (localStorage.getItem('sidebar-collapsed') === 'true') {
        sidebar.classList.add('collapsed');
        mainContent?.classList.add('sidebar-collapsed');
      }
    }

    // User menu dropdown
    const userMenu = document.getElementById('user-menu');
    const userDropdown = document.getElementById('user-dropdown');

    if (userMenu && userDropdown) {
      userMenu.addEventListener('click', (e) => {
        e.stopPropagation();
        userDropdown.classList.toggle('active');
      });

      document.addEventListener('click', () => {
        userDropdown.classList.remove('active');
      });
    }

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        OPTIXAuth.logout();
      });
    }

    // Set active nav item
    setActiveNavItem();

    // Update user info in header
    updateUserInfo();
  }

  /**
   * Set active navigation item based on current path
   */
  function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && currentPath.includes(href.replace('.html', ''))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  /**
   * Update user info in header
   */
  function updateUserInfo() {
    const user = OPTIXAuth?.getUser();
    if (user) {
      const userName = document.getElementById('user-name');
      const userEmail = document.getElementById('user-email');
      const userAvatar = document.getElementById('user-avatar');

      if (userName) userName.textContent = user.name || user.email;
      if (userEmail) userEmail.textContent = user.email;
      if (userAvatar) {
        userAvatar.textContent = (user.name || user.email || 'U').charAt(0).toUpperCase();
      }
    }
  }

  /**
   * Load GenUI component dynamically
   */
  async function loadGenUIComponent(selector, query, context = {}) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`Element not found: ${selector}`);
      return;
    }

    // Show loading state
    element.innerHTML = `
      <div class="flex items-center justify-center p-lg">
        <div class="spinner"></div>
        <span class="text-muted ml-md">Generating UI...</span>
      </div>
    `;

    try {
      const response = await OPTIXDataBridge.genui.generate(query, context);

      if (response.html) {
        element.innerHTML = response.html;
        executeScripts(element);

        // Initialize data bindings in generated UI
        initDataBindings(element);

        element.dispatchEvent(new CustomEvent('genui:loaded', {
          bubbles: true,
          detail: response.metadata
        }));
      } else {
        throw new Error('No HTML returned');
      }
    } catch (error) {
      element.innerHTML = `
        <div class="alert alert-error">
          <strong>Failed to generate UI</strong>
          <p class="text-muted mt-sm">${error.message}</p>
          <button class="btn btn-secondary mt-md" onclick="OPTIXComponentLoader.loadGenUIComponent('${selector}', '${query}')">
            Retry
          </button>
        </div>
      `;
    }
  }

  /**
   * Stream GenUI component with progress
   */
  async function streamGenUIComponent(selector, query, context = {}) {
    const element = document.querySelector(selector);
    if (!element) return;

    element.innerHTML = `
      <div class="genui-progress">
        <div class="flex items-center gap-md mb-md">
          <div class="spinner"></div>
          <span id="genui-status">Starting...</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" id="genui-progress-fill" style="width: 0%"></div>
        </div>
      </div>
    `;

    const statusEl = document.getElementById('genui-status');
    const progressEl = document.getElementById('genui-progress-fill');

    try {
      await OPTIXDataBridge.genui.generateStream(query, context, (event) => {
        if (statusEl) statusEl.textContent = event.message || event.event;
        if (progressEl && event.progress) progressEl.style.width = `${event.progress}%`;

        if (event.event === 'complete' && event.html) {
          element.innerHTML = event.html;
          executeScripts(element);
          initDataBindings(element);
        }

        if (event.event === 'error') {
          throw new Error(event.error);
        }
      });
    } catch (error) {
      element.innerHTML = `
        <div class="alert alert-error">
          <strong>Generation failed</strong>
          <p class="text-muted mt-sm">${error.message}</p>
        </div>
      `;
    }
  }

  /**
   * Initialize data bindings in element
   */
  async function initDataBindings(container) {
    const bindings = container.querySelectorAll('[data-bind]');

    for (const el of bindings) {
      const endpoint = el.dataset.bind;
      const params = el.dataset.params;

      el.classList.add('loading');

      try {
        let data;

        // Route to appropriate API based on endpoint
        if (endpoint.startsWith('quote:')) {
          const symbol = endpoint.split(':')[1];
          data = await OPTIXDataBridge.quotes.get(symbol);
        } else if (endpoint.startsWith('options:')) {
          const symbol = endpoint.split(':')[1];
          data = await OPTIXDataBridge.options.getChain(symbol);
        } else if (endpoint.startsWith('gex:')) {
          const symbol = endpoint.split(':')[1];
          data = await OPTIXDataBridge.gex.calculate(symbol);
        } else if (endpoint === 'portfolio') {
          data = await OPTIXDataBridge.portfolio.get();
        } else if (endpoint === 'watchlists') {
          data = await OPTIXDataBridge.watchlists.getAll();
        } else {
          // Generic request
          data = await OPTIXDataBridge.request(`/${endpoint}`, { params: params ? JSON.parse(params) : {} });
        }

        // Update element with data
        updateElementWithData(el, data);
        el.classList.remove('loading');
      } catch (error) {
        el.textContent = '[Error]';
        el.classList.add('error');
        el.classList.remove('loading');
      }
    }
  }

  /**
   * Update element with fetched data
   */
  function updateElementWithData(el, data) {
    const format = el.dataset.format;

    if (format === 'price') {
      el.textContent = formatPrice(data.price || data);
    } else if (format === 'change') {
      el.textContent = formatChange(data.change || data);
      el.classList.toggle('positive', (data.change || data) >= 0);
      el.classList.toggle('negative', (data.change || data) < 0);
    } else if (format === 'percent') {
      el.textContent = formatPercent(data.changePercent || data);
    } else if (format === 'number') {
      el.textContent = formatNumber(data);
    } else if (typeof data === 'object') {
      el.textContent = JSON.stringify(data);
    } else {
      el.textContent = data;
    }
  }

  /**
   * Format helpers
   */
  function formatPrice(value) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  }

  function formatChange(value) {
    const prefix = value >= 0 ? '+' : '';
    return prefix + formatPrice(value);
  }

  function formatPercent(value) {
    const prefix = value >= 0 ? '+' : '';
    return prefix + value.toFixed(2) + '%';
  }

  function formatNumber(value) {
    if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
    if (value >= 1e3) return (value / 1e3).toFixed(2) + 'K';
    return value.toLocaleString();
  }

  /**
   * Clear component cache
   */
  function clearCache() {
    componentCache.clear();
  }

  // ==========================================
  // Public API
  // ==========================================
  return {
    loadComponent,
    inject,
    loadLayout,
    loadGenUIComponent,
    streamGenUIComponent,
    initDataBindings,
    clearCache,
    formatPrice,
    formatChange,
    formatPercent,
    formatNumber,
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OPTIXComponentLoader;
}

// Make available globally
window.OPTIXComponentLoader = OPTIXComponentLoader;
