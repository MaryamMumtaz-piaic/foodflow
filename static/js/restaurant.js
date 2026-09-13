/**
 * restaurant.js — Restaurant Manager dashboard: overview stats, profile
 * management, menu CRUD, and order management actions.
 * Assumes the current session's restaurant id is available via
 * FoodFlowAuth.getCurrentUser().restaurant_id (falls back to a query
 * param `restaurant_id` for demoing without full auth wired up).
 */
(function () {
  const { qs, qsa, skeletonCards, errorState, emptyState, escapeHtml } = window.FoodFlowUI;
  const money = (n) => 'Rs. ' + Number(n || 0).toLocaleString('en-PK', { maximumFractionDigits: 0 });

  function currentRestaurantId() {
    const user = window.FoodFlowAuth && FoodFlowAuth.getCurrentUser();
    return (user && (user.restaurant_id || user.id)) || new URLSearchParams(window.location.search).get('restaurant_id') || 'demo-restaurant';
  }

  /* ---------------------------- OVERVIEW ---------------------------- */
  async function loadOverview() {
    const grid = qs('#restaurant-overview-grid');
    if (!grid) return;
    grid.innerHTML = skeletonCards(6, 'h-20');
    const rid = currentRestaurantId();
    const { data, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(rid));
    if (error) {
      grid.innerHTML = errorState(error.message, 'overview-retry');
      qs('#overview-retry')?.addEventListener('click', loadOverview);
      return;
    }
    const stats = [
      { label: 'Total orders', value: data.total_orders ?? '—', icon: 'box' },
      { label: "Today's revenue", value: data.today_revenue != null ? money(data.today_revenue) : '—', icon: 'cash' },
      { label: 'Pending orders', value: data.pending_orders ?? '—', icon: 'clock' },
      { label: 'Completed orders', value: data.completed_orders ?? '—', icon: 'check' },
      { label: 'Average rating', value: data.rating != null ? Number(data.rating).toFixed(1) + ' / 5' : '—', icon: 'star' },
      { label: 'Status', value: data.is_open === false ? 'Closed' : 'Open', icon: 'status' }
    ];
    grid.innerHTML = stats.map(statCardHtml).join('');
    loadInsights(rid);
    loadPopularItems(rid);
  }

  function statCardHtml(s) {
    return '<div class="card p-4"><p class="text-xs text-ink-soft font-medium">' + escapeHtml(s.label) + '</p><p class="font-display text-2xl font-bold mt-1">' + escapeHtml(String(s.value)) + '</p></div>';
  }

  async function loadInsights(rid) {
    const el = qs('#ai-insights-panel');
    if (!el) return;
    el.innerHTML = '<div class="skeleton h-16 w-full"></div>';
    const { data, error } = await FoodFlowAPI.post('/api/ai/restaurant-insights', { restaurant_id: rid });
    if (error) { el.innerHTML = errorState(error.message, 'insights-retry'); qs('#insights-retry')?.addEventListener('click', () => loadInsights(rid)); return; }
    const insights = (data && (data.insights || data.recommendations)) || [];
    el.innerHTML = insights.length
      ? '<ul class="space-y-2">' + insights.map((i) => '<li class="text-sm flex gap-2"><span class="text-primary">•</span>' + escapeHtml(typeof i === 'string' ? i : i.text || JSON.stringify(i)) + '</li>').join('') + '</ul>'
      : emptyState({ title: 'No insights available yet', message: 'Insights appear once you have enough order history.' });
  }

  async function loadPopularItems(rid) {
    const el = qs('#popular-items-panel');
    if (!el) return;
    el.innerHTML = skeletonCards(3, 'h-10');
    const { data, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(rid) + '/menu');
    if (error) { el.innerHTML = errorState(error.message, 'popular-retry'); qs('#popular-retry')?.addEventListener('click', () => loadPopularItems(rid)); return; }
    const items = (data && (data.categories || [])).flatMap((c) => c.items || []).slice(0, 5);
    el.innerHTML = items.length
      ? items.map((i) => '<div class="flex justify-between text-sm py-1.5 border-b border-border last:border-0"><span>' + escapeHtml(i.name) + '</span><span class="text-ink-soft">' + money(i.price) + '</span></div>').join('')
      : emptyState({ title: 'No menu items yet', message: 'Add your first dish to see it appear here.' });
  }

  /* ---------------------------- PROFILE ---------------------------- */
  function initProfileForm() {
    const form = qs('#restaurant-profile-form');
    if (!form) return;
    const rid = currentRestaurantId();
    FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(rid)).then(({ data, error }) => {
      if (error) return;
      Object.entries(data).forEach(([key, value]) => {
        const field = form.querySelector('[name="' + key + '"]');
        if (field && typeof value !== 'object') field.value = value;
      });
    });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const payload = Object.fromEntries(fd.entries());
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const { error } = await FoodFlowAPI.put('/api/restaurants/' + encodeURIComponent(rid), payload);
      btn.disabled = false; btn.classList.remove('is-loading');
      FoodFlowToast(error ? 'Save failed: ' + error.message : 'Restaurant profile updated', error ? 'error' : 'success');
    });

    qs('#availability-toggle')?.addEventListener('change', async (e) => {
      const { error } = await FoodFlowAPI.put('/api/restaurants/' + encodeURIComponent(rid), { availability_status: e.target.checked ? 'available' : 'unavailable' });
      FoodFlowToast(error ? 'Could not update availability' : 'Availability updated', error ? 'error' : 'success');
    });
  }

  /* ---------------------------- MENU MANAGEMENT ---------------------------- */
  async function loadMenuManagement() {
    const container = qs('#menu-management-list');
    if (!container) return;
    const rid = currentRestaurantId();
    container.innerHTML = skeletonCards(4, 'h-16');
    const { data, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(rid) + '/menu');
    if (error) { container.innerHTML = errorState(error.message, 'menu-mgmt-retry'); qs('#menu-mgmt-retry')?.addEventListener('click', loadMenuManagement); return; }
    const categories = (data && (data.categories || data)) || [];
    if (!categories.length) {
      container.innerHTML = emptyState({ title: 'No menu items yet', message: 'Use the form above to add your first category and dish.' });
      return;
    }
    container.innerHTML = categories.map((cat) => (
      '<div class="mb-4"><h3 class="font-display font-semibold mb-2">' + escapeHtml(cat.name) + '</h3>' +
      (cat.items || []).map(menuManagementRowHtml).join('') + '</div>'
    )).join('');
    bindMenuManagementActions(container, rid);
  }

  function menuManagementRowHtml(item) {
    const available = item.availability_status !== false && item.available !== false;
    return (
      '<div class="card p-3 flex items-center justify-between gap-3 mb-2" data-item-id="' + escapeHtml(item.id) + '">' +
      '<div class="min-w-0"><p class="font-medium text-sm ' + (available ? '' : 'is-unavailable-text') + '">' + escapeHtml(item.name) + '</p><p class="text-xs text-ink-soft">' + money(item.price) + '</p></div>' +
      '<div class="flex items-center gap-2 shrink-0">' +
      '<label class="inline-flex items-center gap-1.5 text-xs"><input type="checkbox" class="availability-checkbox w-4 h-4" ' + (available ? 'checked' : '') + ' /> Available</label>' +
      '<button type="button" class="btn btn-outline btn-sm edit-item-btn">Edit</button>' +
      '<button type="button" class="btn btn-danger btn-sm delete-item-btn">Delete</button>' +
      '</div></div>'
    );
  }

  function bindMenuManagementActions(root, rid) {
    qsa('.availability-checkbox', root).forEach((cb) => {
      cb.addEventListener('change', async () => {
        const itemId = cb.closest('[data-item-id]').getAttribute('data-item-id');
        const { error } = await FoodFlowAPI.patch('/api/menu-items/' + encodeURIComponent(itemId) + '/availability', { available: cb.checked });
        FoodFlowToast(error ? 'Update failed' : 'Availability updated', error ? 'error' : 'success');
      });
    });
    qsa('.delete-item-btn', root).forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!confirm('Delete this menu item?')) return;
        const itemId = btn.closest('[data-item-id]').getAttribute('data-item-id');
        const { error } = await FoodFlowAPI.delete('/api/menu-items/' + encodeURIComponent(itemId));
        if (error) { FoodFlowToast('Delete failed: ' + error.message, 'error'); return; }
        loadMenuManagement();
      });
    });
    qsa('.edit-item-btn', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        const itemId = btn.closest('[data-item-id]').getAttribute('data-item-id');
        const form = qs('#menu-item-form');
        if (form) { form.dataset.editingId = itemId; qs('#menu-item-form-title').textContent = 'Edit menu item'; window.scrollTo({ top: form.offsetTop - 100, behavior: 'smooth' }); }
      });
    });
  }

  function initMenuItemForm() {
    const form = qs('#menu-item-form');
    if (!form) return;
    const rid = currentRestaurantId();
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const payload = {
        name: fd.get('name'), description: fd.get('description'), price: Number(fd.get('price')),
        category_id: fd.get('category_id'), ingredients: (fd.get('ingredients') || '').split(',').map((s) => s.trim()).filter(Boolean),
        allergens: (fd.get('allergens') || '').split(',').map((s) => s.trim()).filter(Boolean),
        spice_level: fd.get('spice_level'), portion_size: fd.get('portion_size'), image: fd.get('image') || ''
      };
      const editingId = form.dataset.editingId;
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const result = editingId
        ? await FoodFlowAPI.put('/api/menu-items/' + encodeURIComponent(editingId), payload)
        : await FoodFlowAPI.post('/api/restaurants/' + encodeURIComponent(rid) + '/menu', payload);
      btn.disabled = false; btn.classList.remove('is-loading');
      if (result.error) { FoodFlowToast('Save failed: ' + result.error.message, 'error'); return; }
      FoodFlowToast(editingId ? 'Menu item updated' : 'Menu item added', 'success');
      form.reset();
      delete form.dataset.editingId;
      qs('#menu-item-form-title').textContent = 'Add menu item';
      loadMenuManagement();
    });
  }

  /* ---------------------------- ORDER MANAGEMENT ---------------------------- */
  async function loadIncomingOrders() {
    const container = qs('#incoming-orders-list');
    if (!container) return;
    const rid = currentRestaurantId();
    container.innerHTML = skeletonCards(3, 'h-24');
    const { data, error } = await FoodFlowAPI.get('/api/admin/orders?restaurant_id=' + encodeURIComponent(rid));
    if (error) { container.innerHTML = errorState(error.message, 'orders-retry'); qs('#orders-retry')?.addEventListener('click', loadIncomingOrders); return; }
    const orders = (data && (data.orders || data)) || [];
    if (!orders.length) {
      container.innerHTML = emptyState({ title: 'No incoming orders', message: 'New orders will appear here as customers check out.' });
      return;
    }
    container.innerHTML = orders.map(incomingOrderRowHtml).join('');
    bindOrderActions(container);
  }

  function incomingOrderRowHtml(o) {
    const actions = orderActionsForStatus(o.order_status, o.id);
    return (
      '<div class="card p-4" data-order-id="' + escapeHtml(o.id) + '">' +
      '<div class="flex flex-wrap items-start justify-between gap-2">' +
      '<div><p class="font-semibold">Order #' + escapeHtml(o.id) + '</p><p class="text-sm text-ink-soft">' + escapeHtml(o.customer_name || 'Customer') + ' · ' + escapeHtml(o.order_time || o.created_date || '') + '</p></div>' +
      '<span class="badge badge-info">' + escapeHtml((o.order_status || '').replace(/_/g, ' ')) + '</span>' +
      '</div>' +
      '<div class="text-sm mt-2 text-ink-soft">' + (o.items || []).map((i) => (i.quantity || 1) + '× ' + escapeHtml(i.name)).join(', ') + '</div>' +
      '<div class="flex flex-wrap gap-2 mt-3">' + actions + '</div>' +
      '</div>'
    );
  }

  function orderActionsForStatus(status, id) {
    const idAttr = 'data-order-id="' + escapeHtml(id) + '"';
    if (status === 'pending') {
      return '<button class="btn btn-primary btn-sm accept-order-btn" ' + idAttr + '>Accept</button><button class="btn btn-outline btn-sm reject-order-btn" ' + idAttr + '>Reject</button>';
    }
    if (status === 'accepted') return '<button class="btn btn-primary btn-sm set-status-btn" data-status="preparing" ' + idAttr + '>Mark preparing</button>';
    if (status === 'preparing') return '<button class="btn btn-primary btn-sm set-status-btn" data-status="ready_for_pickup" ' + idAttr + '>Mark ready</button>';
    return '<span class="text-xs text-ink-soft">No actions available</span>';
  }

  function bindOrderActions(root) {
    qsa('.accept-order-btn', root).forEach((btn) => btn.addEventListener('click', () => updateOrderStatus(btn.getAttribute('data-order-id'), 'accepted')));
    qsa('.reject-order-btn', root).forEach((btn) => btn.addEventListener('click', () => {
      const reason = prompt('Reason for rejecting this order:');
      if (reason === null) return;
      updateOrderStatus(btn.getAttribute('data-order-id'), 'cancelled', reason);
    }));
    qsa('.set-status-btn', root).forEach((btn) => btn.addEventListener('click', () => updateOrderStatus(btn.getAttribute('data-order-id'), btn.getAttribute('data-status'))));
  }

  async function updateOrderStatus(orderId, status, reason) {
    const { error } = await FoodFlowAPI.patch('/api/orders/' + encodeURIComponent(orderId) + '/status', { status, reason: reason || undefined });
    if (error) { FoodFlowToast('Order update failed: ' + error.message, 'error'); return; }
    FoodFlowToast('Order updated', 'success');
    loadIncomingOrders();
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'restaurant-dashboard') return;
    loadOverview();
    initProfileForm();
    loadMenuManagement();
    initMenuItemForm();
    loadIncomingOrders();

    qsa('[data-dash-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        qsa('[data-dash-tab]').forEach((b) => b.classList.remove('is-active'));
        qsa('[data-dash-panel]').forEach((p) => p.classList.add('hidden'));
        btn.classList.add('is-active');
        qs('[data-dash-panel="' + btn.getAttribute('data-dash-tab') + '"]')?.classList.remove('hidden');
      });
    });
  });
})();
