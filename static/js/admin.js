/**
 * admin.js — Admin dashboard: platform overview, customer/restaurant/rider
 * management tables, order monitoring, and review/complaint moderation.
 */
(function () {
  const { qs, qsa, skeletonCards, errorState, emptyState, escapeHtml } = window.FoodFlowUI;
  const money = (n) => 'Rs. ' + Number(n || 0).toLocaleString('en-PK', { maximumFractionDigits: 0 });

  async function loadOverview() {
    const grid = qs('#admin-overview-grid');
    if (!grid) return;
    grid.innerHTML = skeletonCards(8, 'h-20');
    const { data, error } = await FoodFlowAPI.get('/api/admin/overview');
    if (error) { grid.innerHTML = errorState(error.message, 'admin-overview-retry'); qs('#admin-overview-retry')?.addEventListener('click', loadOverview); return; }
    const stats = [
      ['Total customers', data.total_customers], ['Total restaurants', data.total_restaurants],
      ['Total riders', data.total_riders], ['Total orders', data.total_orders],
      ['Total revenue', data.total_revenue != null ? money(data.total_revenue) : null],
      ['Active orders', data.active_orders], ['Pending restaurant approvals', data.pending_restaurant_approvals],
      ['Pending rider approvals', data.pending_rider_approvals], ['Avg. delivery time', data.average_delivery_time],
      ['Cancellation rate', data.cancellation_rate != null ? data.cancellation_rate + '%' : null]
    ];
    grid.innerHTML = stats.map(([label, value]) => (
      '<div class="card p-4"><p class="text-xs text-ink-soft font-medium">' + escapeHtml(label) + '</p><p class="font-display text-2xl font-bold mt-1">' + escapeHtml(value != null ? String(value) : '—') + '</p></div>'
    )).join('');
  }

  async function loadTable(opts) {
    const container = qs(opts.containerSel);
    if (!container) return;
    container.innerHTML = skeletonCards(4, 'h-10');
    const { data, error } = await FoodFlowAPI.get(opts.endpoint);
    if (error) { container.innerHTML = errorState(error.message, opts.retryId); qs('#' + opts.retryId)?.addEventListener('click', () => loadTable(opts)); return; }
    const rows = (data && (data[opts.dataKey] || data)) || [];
    if (!Array.isArray(rows) || !rows.length) {
      container.innerHTML = emptyState({ title: opts.emptyTitle, message: opts.emptyMessage });
      return;
    }
    container.innerHTML =
      '<div class="overflow-x-auto"><table class="w-full text-sm border-collapse">' +
      '<thead><tr class="text-left border-b border-border text-ink-soft">' + opts.columns.map((c) => '<th scope="col" class="py-2 pr-4 font-medium">' + escapeHtml(c.label) + '</th>').join('') + '<th scope="col" class="py-2">Actions</th></tr></thead>' +
      '<tbody>' + rows.map((row) => opts.rowHtml(row)).join('') + '</tbody></table></div>';
    opts.bindActions && opts.bindActions(container);
  }

  function loadCustomers() {
    return loadTable({
      containerSel: '#customers-table', endpoint: '/api/admin/customers', dataKey: 'customers', retryId: 'customers-retry',
      emptyTitle: 'No customers found', emptyMessage: 'Registered customers will appear here.',
      columns: [{ label: 'Name' }, { label: 'Email' }, { label: 'Status' }],
      rowHtml: (c) => (
        '<tr class="border-b border-border" data-id="' + escapeHtml(c.id) + '">' +
        '<td class="py-2 pr-4">' + escapeHtml(c.name) + '</td><td class="py-2 pr-4">' + escapeHtml(c.email) + '</td>' +
        '<td class="py-2 pr-4">' + (c.account_status === 'suspended' ? '<span class="badge badge-danger">Suspended</span>' : '<span class="badge badge-success">Active</span>') + '</td>' +
        '<td class="py-2"><button type="button" class="btn btn-outline btn-sm toggle-customer-btn" data-status="' + escapeHtml(c.account_status || 'active') + '">' + (c.account_status === 'suspended' ? 'Activate' : 'Suspend') + '</button></td></tr>'
      ),
      bindActions: (root) => qsa('.toggle-customer-btn', root).forEach((btn) => btn.addEventListener('click', async () => {
        const row = btn.closest('[data-id]');
        const nextStatus = btn.getAttribute('data-status') === 'suspended' ? 'active' : 'suspended';
        const { error } = await FoodFlowAPI.patch('/api/admin/customers/' + encodeURIComponent(row.getAttribute('data-id')), { account_status: nextStatus });
        if (error) { FoodFlowToast('Could not update customer', 'error'); return; }
        FoodFlowToast('Customer updated', 'success');
        loadCustomers();
      }))
    });
  }

  function loadRestaurants() {
    return loadTable({
      containerSel: '#restaurants-table', endpoint: '/api/admin/restaurants', dataKey: 'restaurants', retryId: 'restaurants-admin-retry',
      emptyTitle: 'No restaurants found', emptyMessage: 'Restaurant applications will appear here.',
      columns: [{ label: 'Name' }, { label: 'Cuisine' }, { label: 'Approval' }],
      rowHtml: (r) => (
        '<tr class="border-b border-border" data-id="' + escapeHtml(r.id) + '">' +
        '<td class="py-2 pr-4">' + escapeHtml(r.name) + '</td><td class="py-2 pr-4">' + escapeHtml((r.cuisine_types || []).join(', ')) + '</td>' +
        '<td class="py-2 pr-4">' + approvalBadge(r.approval_status) + '</td>' +
        '<td class="py-2 flex gap-2 flex-wrap">' +
        '<button type="button" class="btn btn-primary btn-sm approve-restaurant-btn">Approve</button>' +
        '<button type="button" class="btn btn-outline btn-sm reject-restaurant-btn">Reject</button>' +
        '<button type="button" class="btn btn-ghost btn-sm suspend-restaurant-btn">Suspend</button></td></tr>'
      ),
      bindActions: (root) => {
        qsa('.approve-restaurant-btn', root).forEach((btn) => btn.addEventListener('click', () => setRestaurantApproval(btn, 'approved')));
        qsa('.reject-restaurant-btn', root).forEach((btn) => btn.addEventListener('click', () => setRestaurantApproval(btn, 'rejected')));
        qsa('.suspend-restaurant-btn', root).forEach((btn) => btn.addEventListener('click', () => setRestaurantApproval(btn, 'suspended')));
      }
    });
  }

  async function setRestaurantApproval(btn, status) {
    const id = btn.closest('[data-id]').getAttribute('data-id');
    const { error } = await FoodFlowAPI.patch('/api/admin/restaurants/' + encodeURIComponent(id) + '/approval', { approval_status: status });
    if (error) { FoodFlowToast('Update failed: ' + error.message, 'error'); return; }
    FoodFlowToast('Restaurant ' + status, 'success');
    loadRestaurants();
  }

  function approvalBadge(status) {
    if (status === 'approved') return '<span class="badge badge-success">Approved</span>';
    if (status === 'rejected') return '<span class="badge badge-danger">Rejected</span>';
    if (status === 'suspended') return '<span class="badge badge-danger">Suspended</span>';
    return '<span class="badge badge-warning">Pending</span>';
  }

  function loadRiders() {
    return loadTable({
      containerSel: '#riders-table', endpoint: '/api/admin/riders', dataKey: 'riders', retryId: 'riders-admin-retry',
      emptyTitle: 'No riders found', emptyMessage: 'Rider applications will appear here.',
      columns: [{ label: 'Name' }, { label: 'Phone' }, { label: 'Status' }],
      rowHtml: (r) => (
        '<tr class="border-b border-border" data-id="' + escapeHtml(r.id) + '">' +
        '<td class="py-2 pr-4">' + escapeHtml(r.name) + '</td><td class="py-2 pr-4">' + escapeHtml(r.phone || '') + '</td>' +
        '<td class="py-2 pr-4">' + approvalBadge(r.approval_status) + '</td>' +
        '<td class="py-2 flex gap-2 flex-wrap">' +
        '<button type="button" class="btn btn-primary btn-sm approve-rider-btn">Approve</button>' +
        '<button type="button" class="btn btn-outline btn-sm deactivate-rider-btn">Deactivate</button></td></tr>'
      ),
      bindActions: (root) => {
        qsa('.approve-rider-btn', root).forEach((btn) => btn.addEventListener('click', () => setRiderApproval(btn, 'approved')));
        qsa('.deactivate-rider-btn', root).forEach((btn) => btn.addEventListener('click', () => setRiderApproval(btn, 'deactivated')));
      }
    });
  }

  async function setRiderApproval(btn, status) {
    const id = btn.closest('[data-id]').getAttribute('data-id');
    const { error } = await FoodFlowAPI.patch('/api/admin/riders/' + encodeURIComponent(id) + '/approval', { approval_status: status });
    if (error) { FoodFlowToast('Update failed: ' + error.message, 'error'); return; }
    FoodFlowToast('Rider ' + status, 'success');
    loadRiders();
  }

  function loadOrders() {
    const filterSelect = qs('#order-status-filter');
    const search = qs('#order-search-input');
    const endpoint = () => {
      const params = new URLSearchParams();
      if (filterSelect && filterSelect.value) params.set('status', filterSelect.value);
      if (search && search.value) params.set('q', search.value);
      return '/api/admin/orders' + (params.toString() ? '?' + params.toString() : '');
    };
    const run = () => loadTable({
      containerSel: '#orders-table', endpoint: endpoint(), dataKey: 'orders', retryId: 'orders-admin-retry',
      emptyTitle: 'No orders found', emptyMessage: 'Try a different status filter or search term.',
      columns: [{ label: 'Order #' }, { label: 'Customer' }, { label: 'Restaurant' }, { label: 'Total' }, { label: 'Status' }],
      rowHtml: (o) => (
        '<tr class="border-b border-border" data-id="' + escapeHtml(o.id) + '">' +
        '<td class="py-2 pr-4">' + escapeHtml(o.id) + '</td><td class="py-2 pr-4">' + escapeHtml(o.customer_name || '') + '</td>' +
        '<td class="py-2 pr-4">' + escapeHtml(o.restaurant_name || '') + '</td><td class="py-2 pr-4">' + money(o.final_total || o.total) + '</td>' +
        '<td class="py-2 pr-4">' + escapeHtml((o.order_status || '').replace(/_/g, ' ')) + '</td>' +
        '<td class="py-2"><select class="field-select !min-h-0 !py-1 text-xs manual-status-select">' +
        ['pending', 'accepted', 'preparing', 'ready_for_pickup', 'rider_assigned', 'picked_up', 'out_for_delivery', 'delivered', 'cancelled', 'failed']
          .map((s) => '<option value="' + s + '" ' + (s === o.order_status ? 'selected' : '') + '>' + s.replace(/_/g, ' ') + '</option>').join('') +
        '</select></td></tr>'
      ),
      bindActions: (root) => qsa('.manual-status-select', root).forEach((sel) => sel.addEventListener('change', async () => {
        const id = sel.closest('[data-id]').getAttribute('data-id');
        const { error } = await FoodFlowAPI.patch('/api/orders/' + encodeURIComponent(id) + '/status', { status: sel.value });
        FoodFlowToast(error ? 'Update failed: ' + error.message : 'Order status updated', error ? 'error' : 'success');
      }))
    });
    filterSelect?.addEventListener('change', run);
    search?.addEventListener('input', debounce(run, 300));
    run();
  }

  async function loadComplaints() {
    const container = qs('#complaints-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-16');
    const { data, error } = await FoodFlowAPI.get('/api/admin/complaints');
    if (error) { container.innerHTML = errorState(error.message, 'complaints-retry'); qs('#complaints-retry')?.addEventListener('click', loadComplaints); return; }
    const list = (data && (data.complaints || data)) || [];
    container.innerHTML = list.length
      ? list.map((c) => '<div class="card p-3"><p class="text-sm font-medium">' + escapeHtml(c.subject || 'Complaint #' + c.id) + '</p><p class="text-sm text-ink-soft">' + escapeHtml(c.description || '') + '</p></div>').join('')
      : emptyState({ title: 'No complaints reported', message: 'Customer and rider complaints will show up here for review.' });
  }

  async function loadRiskAlerts() {
    const container = qs('#risk-alerts-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-16');
    const { data, error } = await FoodFlowAPI.get('/api/admin/risk-alerts');
    if (error) { container.innerHTML = errorState(error.message, 'risk-retry'); qs('#risk-retry')?.addEventListener('click', loadRiskAlerts); return; }
    const list = (data && (data.alerts || data)) || [];
    container.innerHTML = list.length
      ? list.map((a) => '<div class="card p-3 flex justify-between"><span class="text-sm">' + escapeHtml(a.description || a.reason || '') + '</span><span class="badge badge-warning">Review</span></div>').join('')
      : emptyState({ title: 'No suspicious activity detected', message: 'Risk alerts flagged by the fraud agent will appear here.' });
  }

  function debounce(fn, wait) { let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), wait); }; }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'admin-dashboard') return;
    loadOverview();
    loadCustomers();
    loadRestaurants();
    loadRiders();
    loadOrders();
    loadComplaints();
    loadRiskAlerts();

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
