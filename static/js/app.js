/**
 * app.js — shared site chrome: mobile nav, account menu, cart badge,
 * toast notifications, and small reusable UI helpers used by every page.
 * Loaded on every page after api.js / auth.js / cart.js.
 */
(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  /* ---------- Toasts ---------- */
  function toast(message, type) {
    const region = qs('#toast-region');
    if (!region) return;
    const el = document.createElement('div');
    el.className = 'toast' + (type === 'success' ? ' toast-success' : type === 'error' ? ' toast-error' : '');
    el.setAttribute('role', 'status');
    el.textContent = message;
    region.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 200ms ease';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 220);
    }, 4200);
  }
  window.FoodFlowToast = toast;

  /* ---------- Skeleton / error / empty state helpers ----------
     Reused across customer.js, restaurant.js, rider.js, admin.js so every
     list follows the same loading -> data | error | empty pattern. */
  function skeletonCards(count, heightClass) {
    let html = '';
    for (let i = 0; i < count; i++) {
      html += '<div class="card p-4"><div class="skeleton ' + (heightClass || 'h-36') + ' w-full mb-3"></div><div class="skeleton h-4 w-3/4 mb-2"></div><div class="skeleton h-4 w-1/2"></div></div>';
    }
    return html;
  }
  function errorState(message, retryId) {
    return (
      '<div class="col-span-full flex flex-col items-center text-center gap-3 py-14 px-4">' +
      '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="text-danger" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v5M12 16h.01"/></svg>' +
      '<p class="font-display font-semibold text-lg">Something went wrong</p>' +
      '<p class="text-ink-soft text-sm max-w-sm">' + escapeHtml(message || 'We could not load this right now.') + '</p>' +
      '<button type="button" id="' + retryId + '" class="btn btn-primary">Try again</button>' +
      '</div>'
    );
  }
  function emptyState(opts) {
    opts = opts || {};
    return (
      '<div class="col-span-full flex flex-col items-center text-center gap-3 py-14 px-4">' +
      '<div class="w-16 h-16 rounded-2xl bg-primary-light flex items-center justify-center text-primary" aria-hidden="true">' + (opts.icon || defaultEmptyIcon()) + '</div>' +
      '<p class="font-display font-semibold text-lg">' + escapeHtml(opts.title || 'Nothing here yet') + '</p>' +
      '<p class="text-ink-soft text-sm max-w-sm">' + escapeHtml(opts.message || '') + '</p>' +
      (opts.actionHref ? '<a href="' + opts.actionHref + '" class="btn btn-primary">' + escapeHtml(opts.actionLabel || 'Explore') + '</a>' : '') +
      '</div>'
    );
  }
  function defaultEmptyIcon() {
    return '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>';
  }
  function escapeHtml(str) {
    return String(str == null ? '' : str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function groupMenuByCategory(rawCategories, rawItems) {
    // The /api/restaurants/{id}/menu response carries categories and items
    // as two separate flat lists (each item has a category_id); group them
    // here so callers can render "category -> its items" directly.
    rawCategories = rawCategories || [];
    rawItems = rawItems || [];
    if (!rawItems.length) {
      return rawCategories.map((cat) => Object.assign({}, cat, { items: cat.items || cat.menu_items || [] }));
    }
    const byCategory = new Map();
    rawCategories.forEach((cat) => byCategory.set(cat.id, Object.assign({}, cat, { items: [] })));
    const uncategorized = [];
    rawItems.forEach((item) => {
      const bucket = byCategory.get(item.category_id);
      if (bucket) bucket.items.push(item);
      else uncategorized.push(item);
    });
    const result = rawCategories
      .slice()
      .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
      .map((cat) => byCategory.get(cat.id));
    if (uncategorized.length) result.push({ id: '_uncategorized', name: 'Other items', items: uncategorized });
    return result;
  }
  window.FoodFlowUI = { skeletonCards, errorState, emptyState, escapeHtml, qs, qsa, groupMenuByCategory };

  /* ---------- Modal helpers (accessible: focus trap + Escape to close) ---------- */
  function openModal(backdropEl) {
    backdropEl.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    const panel = backdropEl.querySelector('.modal-panel');
    const focusable = panel ? qsa('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])', panel) : [];
    if (focusable.length) focusable[0].focus();
    function trap(e) {
      if (e.key === 'Escape') { closeModal(backdropEl); }
      if (e.key === 'Tab' && focusable.length) {
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    backdropEl._trap = trap;
    document.addEventListener('keydown', trap);
  }
  function closeModal(backdropEl) {
    backdropEl.classList.add('hidden');
    document.body.style.overflow = '';
    if (backdropEl._trap) document.removeEventListener('keydown', backdropEl._trap);
  }
  window.FoodFlowModal = { open: openModal, close: closeModal };

  /* ---------- Cart badge ---------- */
  function refreshCartBadge() {
    const badge = qs('#cart-count-badge');
    if (!badge || !window.FoodFlowCart) return;
    const count = FoodFlowCart.itemCount();
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.classList.remove('hidden');
      badge.classList.add('flex');
    } else {
      badge.classList.add('hidden');
      badge.classList.remove('flex');
    }
  }

  /* ---------- Account menu state ---------- */
  function refreshAccountMenu() {
    const guest = qs('#account-menu-guest');
    const user = qs('#account-menu-user');
    const label = qs('#account-menu-label');
    if (!window.FoodFlowAuth) return;
    const isIn = FoodFlowAuth.isLoggedIn();
    const current = FoodFlowAuth.getCurrentUser();
    if (guest) guest.classList.toggle('hidden', isIn);
    if (user) user.classList.toggle('hidden', !isIn);
    if (label) label.textContent = isIn && current && current.name ? current.name.split(' ')[0] : 'Account';
  }

  /* ---------- Init on DOM ready ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    const yearEl = qs('#footer-year');
    if (yearEl) yearEl.textContent = String(new Date().getFullYear());

    refreshCartBadge();
    refreshAccountMenu();
    if (window.FoodFlowCart) FoodFlowCart.onChange(refreshCartBadge);

    // Mobile nav toggle
    const mobileBtn = qs('#mobile-menu-btn');
    const mobileMenu = qs('#mobile-menu');
    if (mobileBtn && mobileMenu) {
      mobileBtn.addEventListener('click', () => {
        const isOpen = !mobileMenu.classList.contains('hidden');
        mobileMenu.classList.toggle('hidden');
        mobileBtn.setAttribute('aria-expanded', String(!isOpen));
      });
    }

    // Dashboard sidebar toggle
    const dashBtn = qs('#dash-mobile-menu-btn');
    const dashSidebar = qs('#dash-sidebar');
    if (dashBtn && dashSidebar) {
      dashBtn.addEventListener('click', () => {
        const isOpen = !dashSidebar.classList.contains('hidden');
        dashSidebar.classList.toggle('hidden');
        dashBtn.setAttribute('aria-expanded', String(!isOpen));
      });
    }

    // Account dropdown menu
    const accountBtn = qs('#account-menu-btn');
    const accountMenu = qs('#account-menu');
    if (accountBtn && accountMenu) {
      accountBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = !accountMenu.classList.contains('hidden');
        accountMenu.classList.toggle('hidden');
        accountBtn.setAttribute('aria-expanded', String(!isOpen));
      });
      document.addEventListener('click', () => {
        accountMenu.classList.add('hidden');
        accountBtn.setAttribute('aria-expanded', 'false');
      });
      accountMenu.addEventListener('click', (e) => e.stopPropagation());
    }

    // Logout
    const logoutBtn = qs('#logout-btn');
    if (logoutBtn && window.FoodFlowAuth) {
      logoutBtn.addEventListener('click', async () => {
        await FoodFlowAuth.logout();
        refreshAccountMenu();
        toast('You have been logged out.', 'success');
        setTimeout(() => { window.location.href = '/'; }, 600);
      });
    }

    // Any element with data-modal-open="modal-id" opens that modal
    qsa('[data-modal-open]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const modal = document.getElementById(btn.getAttribute('data-modal-open'));
        if (modal) openModal(modal);
      });
    });
    qsa('[data-modal-close]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-backdrop');
        if (modal) closeModal(modal);
      });
    });
    qsa('.modal-backdrop').forEach((backdrop) => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal(backdrop);
      });
    });
  });

  window.FoodFlowApp = { refreshCartBadge, refreshAccountMenu };
})();
