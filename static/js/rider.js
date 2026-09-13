/**
 * rider.js — Delivery Rider dashboard: online/offline toggle, delivery
 * task list, status updates through the 8-stage lifecycle, and issue
 * reporting.
 */
(function () {
  const { qs, qsa, skeletonCards, errorState, emptyState, escapeHtml } = window.FoodFlowUI;

  const ISSUE_TYPES = [
    ['restaurant_delay', 'Restaurant delay'],
    ['customer_unavailable', 'Customer unavailable'],
    ['incorrect_address', 'Incorrect address'],
    ['vehicle_issue', 'Vehicle issue'],
    ['missing_item', 'Missing food item'],
    ['safety_concern', 'Safety concern'],
    ['other', 'Other delivery problem']
  ];

  const NEXT_STATUS = {
    assigned: 'accepted',
    accepted: 'arrived_at_restaurant',
    arrived_at_restaurant: 'picked_up',
    picked_up: 'out_for_delivery',
    out_for_delivery: 'delivered'
  };
  const STATUS_LABEL = {
    assigned: 'Assigned', accepted: 'Accept delivery', arrived_at_restaurant: 'Arrived at restaurant',
    picked_up: 'Mark picked up', out_for_delivery: 'Start delivery', delivered: 'Mark delivered'
  };

  async function loadOverview() {
    const grid = qs('#rider-overview-grid');
    if (!grid) return;
    grid.innerHTML = skeletonCards(6, 'h-20');
    const { data, error } = await FoodFlowAPI.get('/api/riders/profile');
    if (error) { grid.innerHTML = errorState(error.message, 'rider-overview-retry'); qs('#rider-overview-retry')?.addEventListener('click', loadOverview); return; }
    const stats = [
      { label: 'Status', value: data.is_online ? 'Online' : 'Offline' },
      { label: 'Pending tasks', value: data.pending_deliveries ?? '—' },
      { label: 'Completed deliveries', value: data.completed_deliveries ?? '—' },
      { label: "Today's earnings", value: data.daily_earnings != null ? 'Rs. ' + Number(data.daily_earnings).toLocaleString() : '—' },
      { label: 'Weekly earnings', value: data.weekly_earnings != null ? 'Rs. ' + Number(data.weekly_earnings).toLocaleString() : '—' },
      { label: 'Success rate', value: data.success_rate != null ? data.success_rate + '%' : '—' }
    ];
    grid.innerHTML = stats.map((s) => '<div class="card p-4"><p class="text-xs text-ink-soft font-medium">' + escapeHtml(s.label) + '</p><p class="font-display text-2xl font-bold mt-1">' + escapeHtml(String(s.value)) + '</p></div>').join('');

    const toggle = qs('#online-toggle');
    if (toggle) {
      toggle.checked = !!data.is_online;
      toggle.dataset.bound !== 'true' && toggle.addEventListener('change', async () => {
        const { error: toggleErr } = await FoodFlowAPI.patch('/api/riders/status', { is_online: toggle.checked });
        if (toggleErr) { FoodFlowToast('Could not update status: ' + toggleErr.message, 'error'); toggle.checked = !toggle.checked; return; }
        FoodFlowToast(toggle.checked ? "You're online" : "You're offline", 'success');
        qs('#online-status-label').textContent = toggle.checked ? 'Online' : 'Offline';
      });
      toggle.dataset.bound = 'true';
      qs('#online-status-label') && (qs('#online-status-label').textContent = data.is_online ? 'Online' : 'Offline');
    }
  }

  async function loadDeliveries() {
    const container = qs('#delivery-tasks-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-28');
    const { data, error } = await FoodFlowAPI.get('/api/riders/deliveries');
    if (error) { container.innerHTML = errorState(error.message, 'deliveries-retry'); qs('#deliveries-retry')?.addEventListener('click', loadDeliveries); return; }
    const tasks = (data && (data.deliveries || data)) || [];
    if (!tasks.length) {
      container.innerHTML = emptyState({ title: 'No assigned deliveries', message: 'Go online to start receiving delivery tasks.' });
      return;
    }
    container.innerHTML = tasks.map(taskCardHtml).join('');
    bindTaskActions(container);
  }

  function taskCardHtml(t) {
    const next = NEXT_STATUS[t.delivery_status];
    return (
      '<div class="card p-4" data-delivery-id="' + escapeHtml(t.id) + '">' +
      '<div class="flex flex-wrap items-start justify-between gap-2">' +
      '<div><p class="font-semibold">Order #' + escapeHtml(t.order_id || t.id) + ' · ' + escapeHtml(t.restaurant_name || '') + '</p>' +
      '<p class="text-sm text-ink-soft">Pickup: ' + escapeHtml(t.pickup_address || '—') + '</p>' +
      '<p class="text-sm text-ink-soft">Drop-off: ' + escapeHtml(t.dropoff_address || t.drop_off_address || '—') + ' (' + escapeHtml(t.customer_name || 'customer') + ')</p>' +
      (t.delivery_instructions ? '<p class="text-xs text-ink-soft italic mt-1">"' + escapeHtml(t.delivery_instructions) + '"</p>' : '') +
      '<p class="text-xs text-ink-soft mt-1">Est. distance: ' + escapeHtml(t.estimated_distance != null ? t.estimated_distance + ' km' : '—') + '</p>' +
      '</div>' +
      '<span class="badge badge-info">' + escapeHtml((t.delivery_status || '').replace(/_/g, ' ')) + '</span>' +
      '</div>' +
      '<div class="flex flex-wrap gap-2 mt-3">' +
      (next ? '<button type="button" class="btn btn-primary btn-sm advance-status-btn" data-next="' + next + '">' + escapeHtml(STATUS_LABEL[next]) + '</button>' : '') +
      '<button type="button" class="btn btn-outline btn-sm fail-delivery-btn">Report failed delivery</button>' +
      '<button type="button" class="btn btn-ghost btn-sm report-issue-btn">Report an issue</button>' +
      '</div></div>'
    );
  }

  function bindTaskActions(root) {
    qsa('.advance-status-btn', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.closest('[data-delivery-id]').getAttribute('data-delivery-id');
        updateDeliveryStatus(id, btn.getAttribute('data-next'));
      });
    });
    qsa('.fail-delivery-btn', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        if (!confirm('Mark this delivery as failed?')) return;
        const id = btn.closest('[data-delivery-id]').getAttribute('data-delivery-id');
        updateDeliveryStatus(id, 'failed');
      });
    });
    qsa('.report-issue-btn', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.closest('[data-delivery-id]').getAttribute('data-delivery-id');
        openIssueModal(id);
      });
    });
  }

  async function updateDeliveryStatus(deliveryId, status) {
    const { error } = await FoodFlowAPI.patch('/api/riders/deliveries/' + encodeURIComponent(deliveryId) + '/status', { status });
    if (error) { FoodFlowToast('Status update failed: ' + error.message, 'error'); return; }
    FoodFlowToast('Delivery status updated', 'success');
    loadDeliveries();
    loadOverview();
  }

  function openIssueModal(deliveryId) {
    const modal = qs('#issue-modal');
    if (!modal) return;
    modal.dataset.deliveryId = deliveryId;
    FoodFlowModal.open(modal);
  }

  function initIssueForm() {
    const select = qs('#issue-type-select');
    if (select && !select.dataset.hydrated) {
      select.innerHTML = ISSUE_TYPES.map(([val, label]) => '<option value="' + val + '">' + escapeHtml(label) + '</option>').join('');
      select.dataset.hydrated = 'true';
    }
    const form = qs('#issue-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const modal = qs('#issue-modal');
      const deliveryId = modal.dataset.deliveryId;
      const fd = new FormData(form);
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const { error } = await FoodFlowAPI.post('/api/riders/deliveries/' + encodeURIComponent(deliveryId) + '/issue', {
        issue_type: fd.get('issue_type'), description: fd.get('description')
      });
      btn.disabled = false; btn.classList.remove('is-loading');
      if (error) { FoodFlowToast('Could not submit report: ' + error.message, 'error'); return; }
      FoodFlowToast('Issue reported to support', 'success');
      form.reset();
      FoodFlowModal.close(modal);
    });
  }

  async function loadCompletedDeliveries() {
    const container = qs('#completed-deliveries-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-16');
    const { data, error } = await FoodFlowAPI.get('/api/riders/deliveries?status=delivered');
    if (error) { container.innerHTML = errorState(error.message, 'completed-retry'); qs('#completed-retry')?.addEventListener('click', loadCompletedDeliveries); return; }
    const list = (data && (data.deliveries || data)) || [];
    container.innerHTML = list.length
      ? list.map((d) => '<div class="card p-3 flex justify-between text-sm"><span>Order #' + escapeHtml(d.order_id || d.id) + '</span><span class="badge badge-success">Delivered</span></div>').join('')
      : emptyState({ title: 'No completed deliveries yet', message: 'Finished deliveries will show up here.' });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'rider-dashboard') return;
    loadOverview();
    loadDeliveries();
    loadCompletedDeliveries();
    initIssueForm();
  });
})();
