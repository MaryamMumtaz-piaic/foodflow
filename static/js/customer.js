/**
 * customer.js — all customer-facing page behavior:
 * homepage AI search, restaurant listing filters/sort/pagination,
 * restaurant detail + food modal, cart page, checkout, order
 * confirmation, order tracking polling, profile, order history,
 * favorites, and the support chat.
 *
 * Dispatch is based on document.body.dataset.page so this single file
 * can be included on every customer page without errors.
 */
(function () {
  const { qs, qsa, skeletonCards, errorState, emptyState, escapeHtml } = window.FoodFlowUI;
  const money = (n) => 'Rs. ' + Number(n || 0).toLocaleString('en-PK', { maximumFractionDigits: 0 });

  const RECENTLY_VIEWED_KEY = 'foodflow_recently_viewed';
  const WISHLIST_KEY = 'foodflow_wishlist';
  const ADDRESS_KEY = 'foodflow_selected_address';
  const PREFS_KEY = 'foodflow_preferences';

  function readLS(key, fallback) {
    try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch (e) { return fallback; }
  }
  function writeLS(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  function addRecentlyViewed(restaurant) {
    const list = readLS(RECENTLY_VIEWED_KEY, []);
    const filtered = list.filter((r) => r.id !== restaurant.id);
    filtered.unshift(restaurant);
    writeLS(RECENTLY_VIEWED_KEY, filtered.slice(0, 8));
  }

  function toggleWishlistItem(id, type) {
    const list = readLS(WISHLIST_KEY, []);
    const key = type + ':' + id;
    const idx = list.indexOf(key);
    if (idx >= 0) list.splice(idx, 1); else list.push(key);
    writeLS(WISHLIST_KEY, list);
    return idx < 0;
  }
  function isWishlisted(id, type) {
    return readLS(WISHLIST_KEY, []).includes(type + ':' + id);
  }

  /* ============================= HOMEPAGE ============================= */
  function initHome() {
    const form = qs('#ai-search-form');
    const input = qs('#ai-search-input');
    const resultsEl = qs('#ai-search-results');
    const loadingEl = qs('#ai-search-loading');

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = (input.value || '').trim();
        if (!query) return;
        resultsEl.innerHTML = '';
        loadingEl.classList.remove('hidden');
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) { submitBtn.disabled = true; submitBtn.classList.add('is-loading'); }

        const { data, error } = await FoodFlowAPI.post('/api/ai/food-search', { query });

        loadingEl.classList.add('hidden');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.classList.remove('is-loading'); }

        if (error) {
          resultsEl.innerHTML = errorState(error.message, 'ai-search-retry');
          const retry = qs('#ai-search-retry');
          if (retry) retry.addEventListener('click', () => form.requestSubmit());
          return;
        }
        renderAiResults(data, resultsEl, query);
      });
    }

    loadHomeSections();
  }

  function renderAiResults(data, container, query) {
    const results = (data && (data.results || data.items || data.recommendations)) || [];
    if (!results.length) {
      container.innerHTML = emptyState({
        title: 'No matches for “' + escapeHtml(query) + '”',
        message: 'Try a broader description — a cuisine, a budget, or how spicy you want it.',
        actionHref: '/restaurants',
        actionLabel: 'Browse all restaurants'
      });
      return;
    }
    container.innerHTML =
      '<h2 class="font-display text-xl font-bold mb-4">AI picks for “' + escapeHtml(query) + '”</h2>' +
      '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">' +
      results.map(foodCardHtml).join('') +
      '</div>';
    bindFoodCardActions(container);
  }

  function foodCardHtml(item) {
    const img = item.image || placeholderFoodImage(item.name);
    const unavailable = item.available === false;
    return (
      '<article class="card card-hover ' + (unavailable ? 'card-unavailable' : '') + ' overflow-hidden flex flex-col" data-food-id="' + escapeHtml(item.id || '') + '">' +
      '<img src="' + img + '" alt="' + escapeHtml(item.name || 'Food item') + '" class="w-full h-40 object-cover" loading="lazy" />' +
      '<div class="p-4 flex flex-col gap-2 flex-1">' +
      '<div class="flex items-start justify-between gap-2">' +
      '<h3 class="font-display font-semibold text-base">' + escapeHtml(item.name || 'Menu item') + '</h3>' +
      (unavailable ? '<span class="badge badge-neutral">' + iconClock() + 'Unavailable</span>' : '') +
      '</div>' +
      '<p class="text-sm text-ink-soft line-clamp-2">' + escapeHtml(item.description || item.explanation || '') + '</p>' +
      '<div class="mt-auto flex items-center justify-between pt-2">' +
      '<span class="font-semibold">' + money(item.price) + '</span>' +
      '<button type="button" class="btn btn-primary btn-sm add-to-cart-quick" ' + (unavailable ? 'disabled' : '') + ' data-item=\'' + escapeHtml(JSON.stringify({
        menuItemId: item.id, restaurantId: item.restaurant_id || item.restaurantId, name: item.name, image: img, unitPrice: item.price
      })) + '\'>Add to cart</button>' +
      '</div></div></article>'
    );
  }

  function bindFoodCardActions(root) {
    qsa('.add-to-cart-quick', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        try {
          const item = JSON.parse(btn.getAttribute('data-item'));
          FoodFlowCart.addItem(Object.assign({ quantity: 1, addOns: [], specialInstructions: '' }, item));
          FoodFlowToast(item.name + ' added to cart', 'success');
        } catch (e) { FoodFlowToast('Could not add item to cart.', 'error'); }
      });
    });
  }

  async function loadHomeSections() {
    const sections = [
      { key: 'featured_restaurants', el: '#featured-restaurants', endpoint: '/api/restaurants?featured=true&limit=6', render: renderRestaurantGrid },
      { key: 'popular_meals', el: '#popular-meals', endpoint: '/api/restaurants?sort=popular_meals&limit=8', render: renderRestaurantGrid },
      { key: 'fast_delivery', el: '#fast-delivery-restaurants', endpoint: '/api/restaurants?sort=delivery_time&limit=6', render: renderRestaurantGrid },
      { key: 'budget_meals', el: '#budget-meals', endpoint: '/api/restaurants?sort=price_low&limit=6', render: renderRestaurantGrid }
    ];
    for (const section of sections) {
      const container = qs(section.el);
      if (!container) continue;
      container.innerHTML = skeletonCards(4, 'h-40');
      const { data, error } = await FoodFlowAPI.get(section.endpoint);
      if (error) {
        container.innerHTML = errorState(error.message, section.key + '-retry');
        const retry = qs('#' + section.key + '-retry');
        if (retry) retry.addEventListener('click', loadHomeSections);
        continue;
      }
      const list = (data && (data.restaurants || data.items || data)) || [];
      if (!Array.isArray(list) || !list.length) {
        container.innerHTML = emptyState({ title: 'Nothing to show yet', message: 'Check back soon as more restaurants join FoodFlow.' });
        continue;
      }
      section.render(list, container);
    }
  }

  /* ======================= RESTAURANT LISTING ======================= */
  const listingState = { page: 1, pageSize: 9, filters: {}, sort: 'recommended', total: null };

  function initRestaurantListing() {
    const grid = qs('#restaurant-grid');
    if (!grid) return;

    const params = new URLSearchParams(window.location.search);
    if (params.get('q')) listingState.filters.q = params.get('q');

    hydrateFilterControls();

    qs('#filter-form')?.addEventListener('submit', (e) => { e.preventDefault(); applyFiltersFromForm(); });
    qs('#sort-select')?.addEventListener('change', (e) => { listingState.sort = e.target.value; listingState.page = 1; loadRestaurants(); });
    qs('#load-more-btn')?.addEventListener('click', () => { listingState.page += 1; loadRestaurants(true); });
    qs('#clear-filters-btn')?.addEventListener('click', () => {
      listingState.filters = {};
      listingState.page = 1;
      qs('#filter-form')?.reset();
      loadRestaurants();
    });

    loadRestaurants();
  }

  function hydrateFilterControls() {
    const q = qs('#filter-q');
    if (q && listingState.filters.q) q.value = listingState.filters.q;
  }

  function applyFiltersFromForm() {
    const form = qs('#filter-form');
    const fd = new FormData(form);
    const filters = {};
    for (const [key, value] of fd.entries()) {
      if (value !== '' && value !== null) filters[key] = value;
    }
    qsa('input[type=checkbox]:checked', form).forEach((cb) => { filters[cb.name] = cb.value; });
    listingState.filters = filters;
    listingState.page = 1;
    loadRestaurants();
  }

  function buildListingQuery() {
    const params = new URLSearchParams();
    Object.entries(listingState.filters).forEach(([k, v]) => params.set(k, v));
    params.set('sort', listingState.sort);
    params.set('page', String(listingState.page));
    params.set('page_size', String(listingState.pageSize));
    return params.toString();
  }

  async function loadRestaurants(append) {
    const grid = qs('#restaurant-grid');
    const loadMoreBtn = qs('#load-more-btn');
    if (!append) grid.innerHTML = skeletonCards(6, 'h-40');
    else if (loadMoreBtn) { loadMoreBtn.disabled = true; loadMoreBtn.classList.add('is-loading'); }

    const { data, error } = await FoodFlowAPI.get('/api/restaurants?' + buildListingQuery());

    if (error) {
      grid.innerHTML = errorState(error.message, 'listing-retry');
      qs('#listing-retry')?.addEventListener('click', () => loadRestaurants(append));
      if (loadMoreBtn) { loadMoreBtn.disabled = false; loadMoreBtn.classList.remove('is-loading'); }
      return;
    }

    const list = (data && (data.restaurants || data.items || data)) || [];
    const total = data && (data.total ?? data.count);
    listingState.total = typeof total === 'number' ? total : null;

    if (!append) grid.innerHTML = '';
    if (!Array.isArray(list) || !list.length) {
      if (!append) {
        grid.innerHTML = emptyState({
          title: 'No restaurants match your filters',
          message: 'Try widening your price range or clearing a filter to see more results.',
          actionLabel: 'Clear all filters'
        });
        qs('.btn', grid)?.addEventListener('click', () => qs('#clear-filters-btn')?.click());
      }
      if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
      return;
    }

    renderRestaurantGrid(list, grid, true);

    if (loadMoreBtn) {
      loadMoreBtn.disabled = false;
      loadMoreBtn.classList.remove('is-loading');
      const shown = grid.querySelectorAll('[data-restaurant-id]').length;
      loadMoreBtn.classList.toggle('hidden', listingState.total !== null && shown >= listingState.total ? true : list.length < listingState.pageSize);
    }
  }

  function renderRestaurantGrid(list, container, append) {
    const html = '<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">' + list.map(restaurantCardHtml).join('') + '</div>';
    if (append) container.insertAdjacentHTML('beforeend', html);
    else container.innerHTML = html;
    bindFavoriteButtons(container);
  }

  function restaurantCardHtml(r) {
    const closed = r.is_open === false || r.availability_status === 'closed';
    const wished = isWishlisted(r.id, 'restaurant');
    return (
      '<article class="card card-hover overflow-hidden flex flex-col ' + (closed ? 'card-unavailable' : '') + '" data-restaurant-id="' + escapeHtml(r.id) + '">' +
      '<div class="relative">' +
      '<a href="/restaurant-detail?id=' + encodeURIComponent(r.id) + '">' +
      '<img src="' + (r.cover_image || r.image || placeholderRestaurantImage(r.name)) + '" alt="' + escapeHtml(r.name) + ' cover photo" class="w-full h-44 object-cover" loading="lazy" />' +
      '</a>' +
      '<button type="button" class="favorite-btn absolute top-3 right-3 w-9 h-9 rounded-full bg-white/90 flex items-center justify-center shadow" data-type="restaurant" data-id="' + escapeHtml(r.id) + '" aria-pressed="' + wished + '" aria-label="' + (wished ? 'Remove from favorites' : 'Save to favorites') + '">' +
      heartIcon(wished) + '</button>' +
      '<span class="badge ' + (closed ? 'badge-danger' : 'badge-success') + ' absolute top-3 left-3">' + (closed ? iconClock() + 'Closed' : iconCheck() + 'Open now') + '</span>' +
      '</div>' +
      '<div class="p-4 flex flex-col gap-2 flex-1">' +
      '<div class="flex items-start justify-between gap-2">' +
      '<h3 class="font-display font-semibold text-base"><a href="/restaurant-detail?id=' + encodeURIComponent(r.id) + '" class="hover:text-primary">' + escapeHtml(r.name) + '</a></h3>' +
      '<span class="badge badge-warning shrink-0">' + starIcon() + (r.rating != null ? Number(r.rating).toFixed(1) : 'New') + '</span>' +
      '</div>' +
      '<p class="text-sm text-ink-soft">' + escapeHtml((r.cuisine_types || r.cuisine || []).toString().replace(/,/g, ' · ')) + '</p>' +
      '<div class="flex items-center gap-3 text-sm text-ink-soft mt-1">' +
      '<span class="inline-flex items-center gap-1">' + iconClock() + escapeHtml(r.estimated_delivery_time || r.delivery_time || '30-40 min') + '</span>' +
      '<span class="inline-flex items-center gap-1">' + iconBike() + (r.delivery_fee != null ? money(r.delivery_fee) : 'Free delivery') + '</span>' +
      '</div>' +
      (r.popular_dish ? '<p class="text-xs text-ink-soft">Popular: <span class="font-medium text-ink">' + escapeHtml(r.popular_dish) + '</span></p>' : '') +
      '<a href="/restaurant-detail?id=' + encodeURIComponent(r.id) + '" class="btn btn-outline mt-2 w-full">View restaurant</a>' +
      '</div></article>'
    );
  }

  function bindFavoriteButtons(root) {
    qsa('.favorite-btn', root).forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        const type = btn.getAttribute('data-type');
        const nowWished = toggleWishlistItem(id, type);
        btn.setAttribute('aria-pressed', String(nowWished));
        btn.setAttribute('aria-label', nowWished ? 'Remove from favorites' : 'Save to favorites');
        btn.innerHTML = heartIcon(nowWished);
        FoodFlowToast(nowWished ? 'Saved to favorites' : 'Removed from favorites', 'success');
      });
    });
  }

  /* ======================= RESTAURANT DETAIL ======================= */
  async function initRestaurantDetail() {
    const root = qs('#restaurant-detail-root');
    if (!root) return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { root.innerHTML = errorState('No restaurant was specified.', 'rd-retry'); return; }

    qs('#rd-header-skeleton')?.classList.remove('hidden');
    const { data: restaurant, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(id));
    qs('#rd-header-skeleton')?.classList.add('hidden');

    if (error) {
      root.innerHTML = errorState(error.message, 'rd-retry');
      qs('#rd-retry')?.addEventListener('click', initRestaurantDetail);
      return;
    }

    renderRestaurantHeader(restaurant);
    addRecentlyViewed({ id: restaurant.id, name: restaurant.name, image: restaurant.cover_image });
    loadMenu(id);
    loadReviews(id);

    qs('#menu-search')?.addEventListener('input', debounce((e) => filterMenu(e.target.value), 200));
  }

  function renderRestaurantHeader(r) {
    const header = qs('#rd-header');
    if (!header) return;
    const closed = r.is_open === false;
    header.innerHTML =
      '<img src="' + (r.cover_image || placeholderRestaurantImage(r.name)) + '" alt="' + escapeHtml(r.name) + ' cover photo" class="w-full h-56 sm:h-72 object-cover rounded-2xl" />' +
      '<div class="mt-4 flex flex-wrap items-start justify-between gap-3">' +
      '<div>' +
      '<h1 class="font-display text-2xl sm:text-3xl font-bold">' + escapeHtml(r.name) + '</h1>' +
      '<p class="text-ink-soft mt-1">' + escapeHtml((r.cuisine_types || []).toString().replace(/,/g, ' · ')) + '</p>' +
      '</div>' +
      '<span class="badge ' + (closed ? 'badge-danger' : 'badge-success') + '">' + (closed ? iconClock() + 'Closed' : iconCheck() + 'Open now') + '</span>' +
      '</div>' +
      '<div class="flex flex-wrap gap-4 mt-4 text-sm">' +
      '<span class="badge badge-warning">' + starIcon() + (r.rating != null ? Number(r.rating).toFixed(1) : 'New') + ' (' + (r.review_count || 0) + ' reviews)</span>' +
      '<span class="inline-flex items-center gap-1 text-ink-soft">' + iconClock() + (r.estimated_delivery_time || '30-40 min') + '</span>' +
      '<span class="inline-flex items-center gap-1 text-ink-soft">' + iconBike() + (r.delivery_fee != null ? money(r.delivery_fee) : 'Free delivery') + '</span>' +
      '<span class="inline-flex items-center gap-1 text-ink-soft">Min. order ' + money(r.minimum_order || 0) + '</span>' +
      '</div>' +
      (r.description ? '<p class="text-ink-soft mt-3 max-w-2xl">' + escapeHtml(r.description) + '</p>' : '');
  }

  let fullMenuCache = [];
  async function loadMenu(restaurantId) {
    const container = qs('#menu-list');
    container.innerHTML = skeletonCards(6, 'h-24');
    const { data, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(restaurantId) + '/menu');
    if (error) {
      container.innerHTML = errorState(error.message, 'menu-retry');
      qs('#menu-retry')?.addEventListener('click', () => loadMenu(restaurantId));
      return;
    }
    const categories = (data && (data.categories || data)) || [];
    fullMenuCache = categories;
    renderMenu(categories, restaurantId);
  }

  function renderMenu(categories, restaurantId) {
    const container = qs('#menu-list');
    if (!Array.isArray(categories) || !categories.length) {
      container.innerHTML = emptyState({ title: 'No menu items yet', message: 'This restaurant has not published its menu.' });
      return;
    }
    container.innerHTML = categories.map((cat) => {
      const items = cat.items || cat.menu_items || [];
      if (!items.length) return '';
      return (
        '<section class="mb-8">' +
        '<h2 class="font-display text-lg font-bold mb-3">' + escapeHtml(cat.name) + '</h2>' +
        '<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">' +
        items.map((item) => menuItemCardHtml(item, restaurantId)).join('') +
        '</div></section>'
      );
    }).join('');
    bindMenuItemButtons(container, restaurantId);
  }

  function menuItemCardHtml(item, restaurantId) {
    const unavailable = item.availability_status === false || item.available === false;
    return (
      '<article class="card ' + (unavailable ? 'card-unavailable' : 'card-hover') + ' flex gap-3 p-3" data-menu-item="' + escapeHtml(item.name) + '">' +
      '<img src="' + (item.image || placeholderFoodImage(item.name)) + '" alt="' + escapeHtml(item.name) + '" class="w-24 h-24 object-cover rounded-xl shrink-0" loading="lazy" />' +
      '<div class="flex-1 min-w-0">' +
      '<div class="flex items-start justify-between gap-2">' +
      '<h3 class="font-semibold ' + (unavailable ? 'is-unavailable-text' : '') + '">' + escapeHtml(item.name) + '</h3>' +
      (unavailable ? '<span class="badge badge-neutral shrink-0">Unavailable</span>' : '') +
      '</div>' +
      '<p class="text-sm text-ink-soft line-clamp-2">' + escapeHtml(item.description || '') + '</p>' +
      '<div class="flex items-center justify-between mt-2">' +
      '<span class="font-semibold">' + money(item.price) + '</span>' +
      '<button type="button" class="btn btn-outline btn-sm open-food-modal" ' + (unavailable ? 'disabled' : '') + ' data-food=\'' + escapeHtml(JSON.stringify(Object.assign({ restaurant_id: restaurantId }, item))) + '\'>View</button>' +
      '</div></div></article>'
    );
  }

  function filterMenu(query) {
    const q = (query || '').toLowerCase();
    qsa('[data-menu-item]').forEach((el) => {
      const name = (el.getAttribute('data-menu-item') || '').toLowerCase();
      el.classList.toggle('hidden', !!q && !name.includes(q));
    });
  }

  function bindMenuItemButtons(root, restaurantId) {
    qsa('.open-food-modal', root).forEach((btn) => {
      btn.addEventListener('click', () => {
        try {
          const food = JSON.parse(btn.getAttribute('data-food'));
          openFoodModal(food);
        } catch (e) { FoodFlowToast('Could not open this item.', 'error'); }
      });
    });
  }

  async function loadReviews(restaurantId) {
    const container = qs('#reviews-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-6');
    const { data, error } = await FoodFlowAPI.get('/api/restaurants/' + encodeURIComponent(restaurantId) + '/reviews');
    if (error) {
      container.innerHTML = errorState(error.message, 'reviews-retry');
      qs('#reviews-retry')?.addEventListener('click', () => loadReviews(restaurantId));
      return;
    }
    const reviews = (data && (data.reviews || data)) || [];
    if (!Array.isArray(reviews) || !reviews.length) {
      container.innerHTML = emptyState({ title: 'No reviews yet', message: 'Be the first to order and share your experience.' });
      return;
    }
    container.innerHTML = reviews.map((r) => (
      '<div class="card p-4">' +
      '<div class="flex items-center justify-between">' +
      '<span class="font-semibold text-sm">' + escapeHtml(r.customer_name || 'FoodFlow customer') + '</span>' +
      '<span class="badge badge-warning">' + starIcon() + Number(r.rating || 0).toFixed(1) + '</span>' +
      '</div>' +
      '<p class="text-sm text-ink-soft mt-2">' + escapeHtml(r.comment || '') + '</p>' +
      '</div>'
    )).join('');
  }

  /* ============================ FOOD MODAL ============================ */
  let modalState = { food: null, quantity: 1, selectedAddOns: [] };

  function openFoodModal(food) {
    modalState = { food, quantity: 1, selectedAddOns: [] };
    const modal = qs('#food-modal');
    if (!modal) { window.location.href = '/food-detail?id=' + encodeURIComponent(food.id || ''); return; }
    renderFoodModal();
    FoodFlowModal.open(modal);
  }

  function renderFoodModal() {
    const modal = qs('#food-modal');
    const food = modalState.food;
    if (!modal || !food) return;
    qs('#food-modal-title', modal).textContent = food.name;
    qs('#food-modal-image', modal).src = food.image || placeholderFoodImage(food.name);
    qs('#food-modal-image', modal).alt = food.name;
    qs('#food-modal-description', modal).textContent = food.description || '';
    qs('#food-modal-price', modal).textContent = money(food.price);
    qs('#food-modal-portion', modal).textContent = food.portion_size ? 'Portion: ' + food.portion_size : '';
    qs('#food-modal-spice', modal).textContent = food.spice_level ? 'Spice level: ' + food.spice_level : '';

    const ingredientsEl = qs('#food-modal-ingredients', modal);
    ingredientsEl.textContent = (food.ingredients || []).join(', ') || 'Not specified';

    const labelsEl = qs('#food-modal-labels', modal);
    labelsEl.innerHTML = (food.dietary_labels || []).map((l) => '<span class="badge badge-success">' + iconCheck() + escapeHtml(l) + '</span>').join('') || '<span class="text-sm text-ink-soft">No dietary labels provided.</span>';

    const allergensEl = qs('#food-modal-allergens', modal);
    allergensEl.innerHTML = (food.allergens || []).length
      ? '<span class="badge badge-danger">' + warnIcon() + 'Contains: ' + escapeHtml((food.allergens || []).join(', ')) + '</span><p class="field-help mt-1">Allergen info is for guidance only — confirm directly with the restaurant if you have a serious allergy.</p>'
      : '<span class="text-sm text-ink-soft">No known allergens listed.</span>';

    const addOnsEl = qs('#food-modal-addons', modal);
    const addOns = food.add_ons || food.addOns || [];
    addOnsEl.innerHTML = addOns.length
      ? addOns.map((a, i) => (
          '<label class="flex items-center justify-between gap-3 py-2 border-b border-border last:border-0">' +
          '<span class="flex items-center gap-2 text-sm"><input type="checkbox" class="addon-checkbox w-4 h-4" data-index="' + i + '" /> ' + escapeHtml(a.name) + '</span>' +
          '<span class="text-sm font-medium">+' + money(a.price) + '</span></label>'
        )).join('')
      : '<p class="text-sm text-ink-soft">No add-ons available.</p>';

    qsa('.addon-checkbox', addOnsEl).forEach((cb) => {
      cb.addEventListener('change', () => {
        const idx = Number(cb.getAttribute('data-index'));
        const addon = addOns[idx];
        if (cb.checked) modalState.selectedAddOns.push(addon);
        else modalState.selectedAddOns = modalState.selectedAddOns.filter((a) => a.name !== addon.name);
      });
    });

    qs('#food-modal-qty', modal).textContent = String(modalState.quantity);
    qs('#food-modal-special', modal).value = '';
  }

  function initFoodModalControls() {
    const modal = qs('#food-modal');
    if (!modal) return;
    qs('#food-modal-qty-minus', modal)?.addEventListener('click', () => {
      modalState.quantity = Math.max(1, modalState.quantity - 1);
      qs('#food-modal-qty', modal).textContent = String(modalState.quantity);
    });
    qs('#food-modal-qty-plus', modal)?.addEventListener('click', () => {
      modalState.quantity += 1;
      qs('#food-modal-qty', modal).textContent = String(modalState.quantity);
    });
    qs('#food-modal-add-to-cart', modal)?.addEventListener('click', () => {
      const food = modalState.food;
      if (!food) return;
      FoodFlowCart.addItem({
        menuItemId: food.id,
        restaurantId: food.restaurant_id,
        name: food.name,
        image: food.image || placeholderFoodImage(food.name),
        unitPrice: food.price,
        quantity: modalState.quantity,
        addOns: modalState.selectedAddOns,
        specialInstructions: qs('#food-modal-special', modal).value.trim()
      });
      FoodFlowToast(food.name + ' added to cart', 'success');
      FoodFlowModal.close(modal);
    });
  }

  /* ============================ FOOD DETAIL PAGE ============================ */
  async function initFoodDetailPage() {
    const root = qs('#food-detail-root');
    if (!root) return;
    const id = new URLSearchParams(window.location.search).get('id');
    root.innerHTML = skeletonCards(1, 'h-64');
    if (!id) { root.innerHTML = errorState('No food item was specified.', 'fd-retry'); return; }
    const { data, error } = await FoodFlowAPI.get('/api/menu-items/' + encodeURIComponent(id));
    if (error) {
      root.innerHTML = errorState(error.message, 'fd-retry');
      qs('#fd-retry')?.addEventListener('click', initFoodDetailPage);
      return;
    }
    modalState = { food: data, quantity: 1, selectedAddOns: [] };
    root.classList.remove('hidden');
    qs('#food-modal')?.classList.remove('hidden', 'modal-backdrop');
    renderFoodModal();
  }

  /* ============================== CART PAGE ============================== */
  function initCartPage() {
    const container = qs('#cart-items-list');
    if (!container) return;
    renderCart();
    FoodFlowCart.onChange(renderCart);

    qs('#coupon-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = qs('#coupon-input').value.trim();
      const btn = qs('#coupon-apply-btn');
      const feedback = qs('#coupon-feedback');
      if (!code) return;
      btn.disabled = true; btn.classList.add('is-loading');
      const { data, error } = await FoodFlowAPI.post('/api/coupons/validate', { code, subtotal: FoodFlowCart.subtotal() });
      btn.disabled = false; btn.classList.remove('is-loading');
      if (error || (data && data.valid === false)) {
        feedback.textContent = (error && error.message) || (data && data.reason) || 'This coupon is not valid.';
        feedback.className = 'field-error is-visible';
        return;
      }
      FoodFlowCart.setCoupon(code);
      feedback.textContent = 'Coupon applied! You saved ' + money(data.discount_amount || 0) + '.';
      feedback.className = 'field-help';
    });

    qs('#cart-remove-coupon')?.addEventListener('click', () => {
      FoodFlowCart.setCoupon(null);
      renderCart();
    });
  }

  function renderCart() {
    const container = qs('#cart-items-list');
    const cart = FoodFlowCart.readCart();
    const summaryEl = qs('#cart-summary');
    const checkoutBtn = qs('#proceed-to-checkout-btn');

    if (!cart.items.length) {
      container.innerHTML = emptyState({
        title: 'Your cart is empty',
        message: 'Browse restaurants and add a few dishes to get started.',
        actionHref: '/restaurants',
        actionLabel: 'Browse restaurants'
      });
      if (summaryEl) summaryEl.classList.add('hidden');
      if (checkoutBtn) checkoutBtn.setAttribute('disabled', 'true');
      return;
    }

    if (checkoutBtn) checkoutBtn.removeAttribute('disabled');
    if (summaryEl) summaryEl.classList.remove('hidden');

    container.innerHTML = cart.items.map((item) => (
      '<div class="card p-4 flex gap-4" data-line-id="' + escapeHtml(item.id) + '">' +
      '<img src="' + (item.image || placeholderFoodImage(item.name)) + '" alt="' + escapeHtml(item.name) + '" class="w-20 h-20 object-cover rounded-xl shrink-0" />' +
      '<div class="flex-1 min-w-0">' +
      '<div class="flex items-start justify-between gap-2">' +
      '<h3 class="font-semibold">' + escapeHtml(item.name) + '</h3>' +
      '<span class="font-semibold">' + money(FoodFlowCart.lineTotal(item)) + '</span>' +
      '</div>' +
      (item.addOns && item.addOns.length ? '<p class="text-xs text-ink-soft mt-1">Add-ons: ' + escapeHtml(item.addOns.map((a) => a.name).join(', ')) + '</p>' : '') +
      (item.specialInstructions ? '<p class="text-xs text-ink-soft italic mt-1">"' + escapeHtml(item.specialInstructions) + '"</p>' : '') +
      '<div class="flex items-center justify-between mt-3">' +
      '<div class="inline-flex items-center border border-border rounded-lg" role="group" aria-label="Quantity for ' + escapeHtml(item.name) + '">' +
      '<button type="button" class="qty-btn w-9 h-9" data-action="dec" aria-label="Decrease quantity">−</button>' +
      '<span class="w-8 text-center text-sm font-medium" aria-live="polite">' + item.quantity + '</span>' +
      '<button type="button" class="qty-btn w-9 h-9" data-action="inc" aria-label="Increase quantity">+</button>' +
      '</div>' +
      '<button type="button" class="remove-line-btn text-sm text-danger font-medium hover:underline">Remove</button>' +
      '</div></div></div>'
    )).join('');

    qsa('.qty-btn', container).forEach((btn) => {
      btn.addEventListener('click', () => {
        const line = btn.closest('[data-line-id]');
        const id = line.getAttribute('data-line-id');
        const cartNow = FoodFlowCart.readCart();
        const item = cartNow.items.find((i) => i.id === id);
        if (!item) return;
        const delta = btn.getAttribute('data-action') === 'inc' ? 1 : -1;
        FoodFlowCart.updateQuantity(id, item.quantity + delta);
      });
    });
    qsa('.remove-line-btn', container).forEach((btn) => {
      btn.addEventListener('click', () => {
        const line = btn.closest('[data-line-id]');
        FoodFlowCart.removeItem(line.getAttribute('data-line-id'));
        FoodFlowToast('Item removed from cart', 'success');
      });
    });

    renderCartSummary(cart);
  }

  function renderCartSummary(cart) {
    const subtotal = FoodFlowCart.subtotal();
    const deliveryFee = subtotal > 0 ? 150 : 0;
    const discount = cart.couponCode ? Math.min(subtotal * 0.1, 500) : 0; // client-side estimate only — backend recalculates authoritatively
    const tax = Math.round(subtotal * 0.05);
    const total = Math.max(0, subtotal + deliveryFee + tax - discount);

    const el = qs('#cart-summary');
    if (!el) return;
    el.innerHTML =
      row('Subtotal', money(subtotal)) +
      row('Delivery fee', money(deliveryFee)) +
      (discount ? row('Discount' + (cart.couponCode ? ' (' + escapeHtml(cart.couponCode) + ')' : ''), '−' + money(discount), true) : '') +
      row('Tax & service fee', money(tax)) +
      '<div class="border-t border-border my-2"></div>' +
      row('Total', money(total), false, true) +
      (cart.couponCode ? '<button type="button" id="cart-remove-coupon" class="text-xs text-danger mt-2 hover:underline">Remove coupon</button>' : '');

    function row(label, value, isDiscount, isTotal) {
      return '<div class="flex items-center justify-between ' + (isTotal ? 'font-bold text-base' : 'text-sm') + ' ' + (isDiscount ? 'text-success' : '') + '"><span>' + label + '</span><span>' + value + '</span></div>';
    }
    // re-bind remove coupon (innerHTML replaced it)
    qs('#cart-remove-coupon')?.addEventListener('click', () => { FoodFlowCart.setCoupon(null); renderCart(); });
  }

  /* ============================== CHECKOUT PAGE ============================== */
  function initCheckoutPage() {
    const form = qs('#checkout-form');
    if (!form) return;
    const cart = FoodFlowCart.readCart();
    if (!cart.items.length) {
      qs('#checkout-empty-notice')?.classList.remove('hidden');
      form.classList.add('hidden');
      return;
    }
    renderCheckoutSummary(cart);
    hydrateSavedAddress();

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!validateCheckoutForm(form)) return;
      const submitBtn = qs('#place-order-btn');
      submitBtn.disabled = true;
      submitBtn.classList.add('is-loading');

      const fd = new FormData(form);
      const address = {
        recipient_name: fd.get('recipient_name'),
        phone: fd.get('phone'),
        street_address: fd.get('street_address'),
        area: fd.get('area'),
        city: fd.get('city'),
        delivery_instructions: fd.get('delivery_instructions')
      };
      writeLS(ADDRESS_KEY, address);

      const payload = {
        restaurant_id: cart.restaurantId,
        items: cart.items.map((i) => ({
          menu_item_id: i.menuItemId,
          quantity: i.quantity,
          add_ons: (i.addOns || []).map((a) => a.id || a.name),
          special_instructions: i.specialInstructions || ''
        })),
        delivery_address: address,
        coupon_code: cart.couponCode || null,
        payment_method: fd.get('payment_method')
      };

      const { data, error } = await FoodFlowAPI.post('/api/orders', payload);
      submitBtn.disabled = false;
      submitBtn.classList.remove('is-loading');

      if (error) {
        const banner = qs('#checkout-error-banner');
        banner.textContent = error.message;
        banner.classList.remove('hidden');
        FoodFlowToast('Checkout failed: ' + error.message, 'error');
        return;
      }

      FoodFlowCart.clearCart();
      const orderId = data && (data.id || data.order_id);
      window.location.href = '/order-confirmation' + (orderId ? '?id=' + encodeURIComponent(orderId) : '');
    });
  }

  function hydrateSavedAddress() {
    const saved = readLS(ADDRESS_KEY, null);
    if (!saved) return;
    Object.entries(saved).forEach(([key, value]) => {
      const field = document.querySelector('[name="' + key + '"]');
      if (field && value) field.value = value;
    });
  }

  function validateCheckoutForm(form) {
    let valid = true;
    qsa('[required]', form).forEach((field) => {
      const errorEl = form.querySelector('[data-error-for="' + field.name + '"]');
      const isEmpty = !field.value || !field.value.trim();
      if (isEmpty) {
        valid = false;
        if (errorEl) { errorEl.textContent = 'This field is required.'; errorEl.classList.add('is-visible'); }
        field.setAttribute('aria-invalid', 'true');
      } else if (errorEl) {
        errorEl.classList.remove('is-visible');
        field.removeAttribute('aria-invalid');
      }
    });
    const phone = form.querySelector('[name="phone"]');
    if (phone && phone.value && !/^[0-9+\-\s]{7,15}$/.test(phone.value)) {
      valid = false;
      const errorEl = form.querySelector('[data-error-for="phone"]');
      if (errorEl) { errorEl.textContent = 'Enter a valid phone number.'; errorEl.classList.add('is-visible'); }
    }
    if (!valid) {
      const firstInvalid = form.querySelector('[aria-invalid="true"]');
      if (firstInvalid) firstInvalid.focus();
      FoodFlowToast('Please fix the highlighted fields.', 'error');
    }
    return valid;
  }

  function renderCheckoutSummary(cart) {
    const el = qs('#checkout-order-summary');
    if (!el) return;
    const subtotal = FoodFlowCart.subtotal();
    el.innerHTML = cart.items.map((i) => (
      '<div class="flex justify-between text-sm py-1"><span>' + i.quantity + '× ' + escapeHtml(i.name) + '</span><span>' + money(FoodFlowCart.lineTotal(i)) + '</span></div>'
    )).join('') + '<div class="border-t border-border mt-2 pt-2 flex justify-between font-bold"><span>Subtotal</span><span>' + money(subtotal) + '</span></div>';
  }

  /* ============================ ORDER CONFIRMATION ============================ */
  async function initOrderConfirmation() {
    const root = qs('#order-confirmation-root');
    if (!root) return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { root.innerHTML = errorState('We could not find your order number.', 'oc-retry'); return; }
    root.innerHTML = skeletonCards(1, 'h-48');
    const { data, error } = await FoodFlowAPI.get('/api/orders/' + encodeURIComponent(id));
    if (error) {
      root.innerHTML = errorState(error.message, 'oc-retry');
      qs('#oc-retry')?.addEventListener('click', initOrderConfirmation);
      return;
    }
    root.innerHTML =
      '<div class="text-center max-w-lg mx-auto">' +
      '<div class="w-16 h-16 rounded-full bg-success/10 text-success flex items-center justify-center mx-auto mb-4">' + iconCheck(28) + '</div>' +
      '<h1 class="font-display text-2xl font-bold">Order placed!</h1>' +
      '<p class="text-ink-soft mt-1">Order #' + escapeHtml(data.id || id) + ' from ' + escapeHtml(data.restaurant_name || 'your restaurant') + '</p>' +
      '</div>' +
      '<div class="card p-5 max-w-lg mx-auto mt-6">' +
      (data.items || []).map((i) => '<div class="flex justify-between text-sm py-1"><span>' + (i.quantity || 1) + '× ' + escapeHtml(i.name || i.menu_item_name) + '</span><span>' + money(i.total_price || i.price) + '</span></div>').join('') +
      '<div class="border-t border-border mt-2 pt-2 flex justify-between font-bold"><span>Total</span><span>' + money(data.final_total || data.total) + '</span></div>' +
      '<p class="text-sm text-ink-soft mt-3">Estimated delivery: ' + escapeHtml(data.estimated_delivery_time || '35-45 min') + '</p>' +
      '<p class="text-sm mt-1"><span class="badge badge-info">' + iconClock() + escapeHtml(data.order_status || 'pending') + '</span></p>' +
      '</div>' +
      '<div class="flex flex-wrap gap-3 justify-center mt-6">' +
      '<a href="/order-tracking?id=' + encodeURIComponent(data.id || id) + '" class="btn btn-primary">Track order</a>' +
      '<a href="/restaurants" class="btn btn-outline">Continue browsing</a>' +
      '</div>';
  }

  /* ============================ ORDER TRACKING ============================ */
  const STATUS_STEPS = [
    { key: 'pending', label: 'Order Placed' },
    { key: 'accepted', label: 'Restaurant Accepted' },
    { key: 'preparing', label: 'Food Preparing' },
    { key: 'ready_for_pickup', label: 'Ready for Pickup' },
    { key: 'rider_assigned', label: 'Rider Assigned' },
    { key: 'picked_up', label: 'Picked Up' },
    { key: 'out_for_delivery', label: 'Out for Delivery' },
    { key: 'delivered', label: 'Delivered' }
  ];
  let trackingPollHandle = null;

  function initOrderTracking() {
    const root = qs('#order-tracking-root');
    if (!root) return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { root.innerHTML = errorState('No order was specified.', 'ot-retry'); return; }
    loadTracking(id);
    trackingPollHandle = setInterval(() => loadTracking(id, true), 15000);
    window.addEventListener('beforeunload', () => clearInterval(trackingPollHandle));

    qs('#cancel-order-btn')?.addEventListener('click', async () => {
      if (!confirm('Cancel this order? This cannot be undone.')) return;
      const { error } = await FoodFlowAPI.post('/api/orders/' + encodeURIComponent(id) + '/cancel', {});
      if (error) { FoodFlowToast('Could not cancel: ' + error.message, 'error'); return; }
      FoodFlowToast('Order cancelled.', 'success');
      loadTracking(id);
    });
  }

  async function loadTracking(id, silent) {
    const stepperEl = qs('#status-stepper');
    const detailsEl = qs('#tracking-details');
    if (!silent) {
      stepperEl.innerHTML = '<div class="skeleton h-20 w-full"></div>';
      detailsEl.innerHTML = skeletonCards(2, 'h-16');
    }
    const { data, error } = await FoodFlowAPI.get('/api/orders/' + encodeURIComponent(id));
    if (error) {
      if (!silent) {
        stepperEl.innerHTML = '';
        detailsEl.innerHTML = errorState(error.message, 'ot-retry-2');
        qs('#ot-retry-2')?.addEventListener('click', () => loadTracking(id));
      }
      return;
    }
    renderStatusStepper(data.order_status || 'pending', stepperEl);
    renderTrackingDetails(data, detailsEl);

    const cancelBtn = qs('#cancel-order-btn');
    if (cancelBtn) cancelBtn.classList.toggle('hidden', !['pending', 'accepted'].includes(data.order_status));

    if (data.order_status === 'delivered' || data.order_status === 'cancelled' || data.order_status === 'failed') {
      clearInterval(trackingPollHandle);
    }
  }

  function renderStatusStepper(currentStatus, container) {
    if (currentStatus === 'cancelled' || currentStatus === 'failed') {
      container.innerHTML =
        '<div class="badge badge-danger text-sm px-4 py-2">' + warnIcon() + (currentStatus === 'cancelled' ? 'Order cancelled' : 'Delivery failed') + '</div>';
      return;
    }
    const currentIndex = STATUS_STEPS.findIndex((s) => s.key === currentStatus);
    container.innerHTML = '<div class="route-stepper" role="list" aria-label="Order progress">' + STATUS_STEPS.map((step, i) => {
      const state = i < currentIndex ? 'is-complete' : i === currentIndex ? 'is-current' : '';
      return (
        '<div class="route-step ' + state + '" role="listitem">' +
        '<span class="route-dot" aria-hidden="true">' + (i < currentIndex ? iconCheck(14) : String(i + 1)) + '</span>' +
        '<span class="route-label">' + step.label + (i === currentIndex ? ' <span class="sr-only">(current status)</span>' : '') + '</span>' +
        '</div>'
      );
    }).join('') + '</div>';
  }

  function renderTrackingDetails(order, container) {
    container.innerHTML =
      '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">' +
      '<div class="card p-4"><h2 class="font-display font-semibold mb-2">Restaurant</h2><p class="text-sm">' + escapeHtml(order.restaurant_name || '—') + '</p></div>' +
      '<div class="card p-4"><h2 class="font-display font-semibold mb-2">Rider</h2><p class="text-sm">' + (order.rider_name ? escapeHtml(order.rider_name) + (order.rider_phone ? ' · ' + escapeHtml(order.rider_phone) : '') : 'Not yet assigned') + '</p></div>' +
      '<div class="card p-4"><h2 class="font-display font-semibold mb-2">Delivery address</h2><p class="text-sm">' + escapeHtml(formatAddress(order.delivery_address)) + '</p></div>' +
      '<div class="card p-4"><h2 class="font-display font-semibold mb-2">Estimated arrival</h2><p class="text-sm">' + escapeHtml(order.estimated_delivery_time || 'Calculating…') + '</p></div>' +
      '</div>' +
      '<div class="card p-4 mt-4"><h2 class="font-display font-semibold mb-2">Items</h2>' +
      (order.items || []).map((i) => '<div class="flex justify-between text-sm py-1"><span>' + (i.quantity || 1) + '× ' + escapeHtml(i.name || i.menu_item_name) + '</span><span>' + money(i.total_price || i.price) + '</span></div>').join('') +
      '</div>' +
      '<div class="mt-4"><a href="/support?order=' + encodeURIComponent(order.id || '') + '" class="btn btn-outline">Contact support about this order</a></div>';
  }

  function formatAddress(addr) {
    if (!addr) return '—';
    if (typeof addr === 'string') return addr;
    return [addr.street_address, addr.area, addr.city].filter(Boolean).join(', ');
  }

  /* ============================== PROFILE PAGE ============================== */
  async function initProfilePage() {
    const root = qs('#profile-root');
    if (!root) return;

    if (!FoodFlowAuth.isLoggedIn()) {
      renderAuthGate(root);
      return;
    }

    loadProfileInfo();
    loadAddresses();
    loadFavorites();
    initPreferences();

    qs('#profile-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd.entries());
      const btn = e.target.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const { error } = await FoodFlowAPI.put('/api/customers/profile', payload);
      btn.disabled = false; btn.classList.remove('is-loading');
      FoodFlowToast(error ? 'Could not save: ' + error.message : 'Profile updated', error ? 'error' : 'success');
    });
  }

  function renderAuthGate(root) {
    root.innerHTML =
      '<div class="max-w-md mx-auto card p-6">' +
      '<div class="flex gap-2 mb-4" role="tablist">' +
      '<button type="button" id="tab-login" class="btn btn-primary flex-1" role="tab" aria-selected="true">Log in</button>' +
      '<button type="button" id="tab-register" class="btn btn-outline flex-1" role="tab" aria-selected="false">Register</button>' +
      '</div>' +
      '<form id="login-form" class="space-y-3">' +
      '<div><label class="field-label" for="login-email">Email</label><input id="login-email" name="email" type="email" required class="field-input" /></div>' +
      '<div><label class="field-label" for="login-password">Password</label><input id="login-password" name="password" type="password" required class="field-input" /></div>' +
      '<p id="login-error" class="field-error"></p>' +
      '<button type="submit" class="btn btn-primary w-full">Log in</button>' +
      '</form>' +
      '<form id="register-form" class="space-y-3 hidden">' +
      '<div><label class="field-label" for="reg-name">Full name</label><input id="reg-name" name="name" type="text" required class="field-input" /></div>' +
      '<div><label class="field-label" for="reg-email">Email</label><input id="reg-email" name="email" type="email" required class="field-input" /></div>' +
      '<div><label class="field-label" for="reg-phone">Phone</label><input id="reg-phone" name="phone" type="tel" required class="field-input" /></div>' +
      '<div><label class="field-label" for="reg-password">Password</label><input id="reg-password" name="password" type="password" required minlength="8" class="field-input" /></div>' +
      '<p id="register-error" class="field-error"></p>' +
      '<button type="submit" class="btn btn-primary w-full">Create account</button>' +
      '</form>' +
      '</div>';

    const loginTab = qs('#tab-login'), registerTab = qs('#tab-register');
    const loginForm = qs('#login-form'), registerForm = qs('#register-form');
    loginTab.addEventListener('click', () => switchTab(true));
    registerTab.addEventListener('click', () => switchTab(false));
    function switchTab(isLogin) {
      loginForm.classList.toggle('hidden', !isLogin);
      registerForm.classList.toggle('hidden', isLogin);
      loginTab.setAttribute('aria-selected', String(isLogin));
      registerTab.setAttribute('aria-selected', String(!isLogin));
      loginTab.className = 'btn flex-1 ' + (isLogin ? 'btn-primary' : 'btn-outline');
      registerTab.className = 'btn flex-1 ' + (!isLogin ? 'btn-primary' : 'btn-outline');
    }

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(loginForm);
      const btn = loginForm.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const result = await FoodFlowAuth.login(fd.get('email'), fd.get('password'));
      btn.disabled = false; btn.classList.remove('is-loading');
      if (!result.ok) {
        const err = qs('#login-error');
        err.textContent = result.error.message;
        err.classList.add('is-visible');
        return;
      }
      window.FoodFlowApp.refreshAccountMenu();
      window.location.reload();
    });

    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(registerForm);
      const payload = Object.fromEntries(fd.entries());
      payload.role = 'customer';
      const btn = registerForm.querySelector('button[type="submit"]');
      btn.disabled = true; btn.classList.add('is-loading');
      const result = await FoodFlowAuth.register(payload);
      btn.disabled = false; btn.classList.remove('is-loading');
      if (!result.ok) {
        const err = qs('#register-error');
        err.textContent = result.error.message;
        err.classList.add('is-visible');
        return;
      }
      window.FoodFlowApp.refreshAccountMenu();
      window.location.reload();
    });
  }

  async function loadProfileInfo() {
    const form = qs('#profile-form');
    if (!form) return;
    const { data, error } = await FoodFlowAPI.get('/api/customers/profile');
    if (error) { FoodFlowToast('Could not load profile: ' + error.message, 'error'); return; }
    Object.entries(data || {}).forEach(([key, value]) => {
      const field = form.querySelector('[name="' + key + '"]');
      if (field && typeof value !== 'object') field.value = value;
    });
  }

  async function loadAddresses() {
    const container = qs('#addresses-list');
    if (!container) return;
    container.innerHTML = skeletonCards(2, 'h-16');
    const { data, error } = await FoodFlowAPI.get('/api/customers/addresses');
    if (error) {
      container.innerHTML = errorState(error.message, 'addr-retry');
      qs('#addr-retry')?.addEventListener('click', loadAddresses);
      return;
    }
    const list = (data && (data.addresses || data)) || [];
    if (!Array.isArray(list) || !list.length) {
      container.innerHTML = emptyState({ title: 'No saved addresses', message: 'Add a delivery address to check out faster next time.' });
      return;
    }
    container.innerHTML = list.map((a) => (
      '<div class="card p-3 flex justify-between items-start gap-2">' +
      '<div><p class="font-medium text-sm">' + escapeHtml(a.label || 'Address') + (a.is_default ? ' <span class="badge badge-info">Default</span>' : '') + '</p>' +
      '<p class="text-sm text-ink-soft">' + escapeHtml([a.street_address, a.area, a.city].filter(Boolean).join(', ')) + '</p></div>' +
      '<button type="button" class="text-danger text-sm hover:underline delete-address-btn" data-id="' + escapeHtml(a.id) + '">Remove</button>' +
      '</div>'
    )).join('');
    qsa('.delete-address-btn', container).forEach((btn) => {
      btn.addEventListener('click', async () => {
        const { error: delErr } = await FoodFlowAPI.delete('/api/customers/addresses/' + encodeURIComponent(btn.getAttribute('data-id')));
        if (delErr) { FoodFlowToast('Could not remove address', 'error'); return; }
        loadAddresses();
      });
    });
  }

  async function loadFavorites() {
    const restEl = qs('#favorite-restaurants');
    const mealEl = qs('#favorite-meals');
    const wishlist = readLS(WISHLIST_KEY, []);
    const restaurantIds = wishlist.filter((k) => k.startsWith('restaurant:'));
    const mealIds = wishlist.filter((k) => k.startsWith('food:'));
    if (restEl) restEl.innerHTML = restaurantIds.length ? restaurantIds.map((k) => '<li class="text-sm">' + escapeHtml(k.split(':')[1]) + '</li>').join('') : emptyState({ title: 'No favorite restaurants', message: 'Tap the heart icon on any restaurant to save it here.' });
    if (mealEl) mealEl.innerHTML = mealIds.length ? mealIds.map((k) => '<li class="text-sm">' + escapeHtml(k.split(':')[1]) + '</li>').join('') : emptyState({ title: 'No favorite meals', message: 'Tap the heart icon on any dish to save it here.' });
  }

  function initPreferences() {
    const form = qs('#preferences-form');
    if (!form) return;
    const prefs = readLS(PREFS_KEY, {});
    Object.entries(prefs).forEach(([key, value]) => {
      const field = form.querySelector('[name="' + key + '"]');
      if (field && field.type === 'checkbox') field.checked = !!value;
      else if (field) field.value = value;
    });
    form.addEventListener('change', () => {
      const fd = new FormData(form);
      const next = {};
      qsa('input, select', form).forEach((f) => {
        next[f.name] = f.type === 'checkbox' ? f.checked : fd.get(f.name);
      });
      writeLS(PREFS_KEY, next);
      FoodFlowToast('Preferences saved', 'success');
    });
  }

  /* ============================ ORDER HISTORY ============================ */
  async function initOrderHistory() {
    const container = qs('#order-history-list');
    if (!container) return;
    container.innerHTML = skeletonCards(3, 'h-24');
    const { data, error } = await FoodFlowAPI.get('/api/orders');
    if (error) {
      container.innerHTML = errorState(error.message, 'oh-retry');
      qs('#oh-retry')?.addEventListener('click', initOrderHistory);
      return;
    }
    const orders = (data && (data.orders || data)) || [];
    if (!Array.isArray(orders) || !orders.length) {
      container.innerHTML = emptyState({
        title: 'No orders yet',
        message: 'When you place an order, it will show up here so you can track and reorder easily.',
        actionHref: '/restaurants',
        actionLabel: 'Start an order'
      });
      return;
    }
    container.innerHTML = orders.map(orderHistoryRowHtml).join('');
    qsa('.reorder-btn', container).forEach((btn) => {
      btn.addEventListener('click', async () => {
        btn.disabled = true; btn.classList.add('is-loading');
        const { data: reorderData, error: reorderError } = await FoodFlowAPI.post('/api/orders/' + encodeURIComponent(btn.getAttribute('data-id')) + '/reorder', {});
        btn.disabled = false; btn.classList.remove('is-loading');
        if (reorderError) { FoodFlowToast('Could not reorder: ' + reorderError.message, 'error'); return; }
        FoodFlowToast('Items added to your cart', 'success');
        if (reorderData && reorderData.items) {
          reorderData.items.forEach((i) => FoodFlowCart.addItem({
            menuItemId: i.menu_item_id, restaurantId: reorderData.restaurant_id, name: i.name, unitPrice: i.unit_price, quantity: i.quantity, addOns: i.add_ons || [], specialInstructions: ''
          }));
        }
        setTimeout(() => { window.location.href = '/cart'; }, 500);
      });
    });
  }

  function orderHistoryRowHtml(o) {
    return (
      '<div class="card p-4 flex flex-wrap items-center justify-between gap-3">' +
      '<div>' +
      '<p class="font-semibold">' + escapeHtml(o.restaurant_name || 'Order #' + o.id) + '</p>' +
      '<p class="text-sm text-ink-soft">' + escapeHtml(formatDate(o.created_date)) + ' · ' + money(o.final_total || o.total) + '</p>' +
      '</div>' +
      statusBadge(o.order_status) +
      '<div class="flex gap-2">' +
      '<a href="/order-tracking?id=' + encodeURIComponent(o.id) + '" class="btn btn-outline btn-sm">View details</a>' +
      '<button type="button" class="btn btn-primary btn-sm reorder-btn" data-id="' + escapeHtml(o.id) + '">Reorder</button>' +
      (o.order_status === 'delivered' ? '<a href="/restaurant-detail?id=' + encodeURIComponent(o.restaurant_id) + '#reviews" class="btn btn-ghost btn-sm">Review</a>' : '') +
      '</div></div>'
    );
  }

  function statusBadge(status) {
    const map = {
      pending: ['badge-info', iconClock()], accepted: ['badge-info', iconCheck()],
      preparing: ['badge-warning', iconClock()], ready_for_pickup: ['badge-warning', iconCheck()],
      rider_assigned: ['badge-info', iconBike()], picked_up: ['badge-info', iconBike()],
      out_for_delivery: ['badge-info', iconBike()], delivered: ['badge-success', iconCheck()],
      cancelled: ['badge-danger', warnIcon()], failed: ['badge-danger', warnIcon()]
    };
    const [cls, icon] = map[status] || ['badge-neutral', iconClock()];
    return '<span class="badge ' + cls + '">' + icon + escapeHtml((status || 'pending').replace(/_/g, ' ')) + '</span>';
  }

  function formatDate(d) {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('en-PK', { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { return d; }
  }

  /* ============================== SUPPORT PAGE ============================== */
  function initSupportPage() {
    const chatForm = qs('#support-chat-form');
    if (!chatForm) return;
    const orderId = new URLSearchParams(window.location.search).get('order');
    if (orderId) qs('#support-order-context').textContent = 'Regarding order #' + orderId;

    qsa('.faq-question-btn').forEach((btn) => {
      btn.addEventListener('click', () => sendSupportMessage(btn.textContent.trim()));
    });

    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = qs('#support-chat-input');
      const message = input.value.trim();
      if (!message) return;
      input.value = '';
      sendSupportMessage(message);
    });

    qs('#escalate-btn')?.addEventListener('click', () => {
      appendChatMessage('Your issue has been flagged for a human support agent. Expect a follow-up within a few hours.', 'system');
    });
  }

  async function sendSupportMessage(message) {
    appendChatMessage(message, 'user');
    const loadingId = appendChatMessage('Thinking…', 'assistant', true);
    const orderId = new URLSearchParams(window.location.search).get('order');
    const { data, error } = await FoodFlowAPI.post('/api/ai/customer-support', { message, order_id: orderId || null });
    qs('#' + loadingId)?.remove();
    if (error) {
      appendChatMessage('Sorry, support is unavailable right now (' + error.message + '). Please try again or use the escalate option below.', 'assistant');
      return;
    }
    appendChatMessage((data && (data.reply || data.response || data.message)) || 'I could not generate a response — please try rephrasing.', 'assistant');
  }

  function appendChatMessage(text, role, isLoading) {
    const list = qs('#support-chat-log');
    if (!list) return '';
    const id = 'msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);
    const bubbleClass = role === 'user' ? 'bg-primary text-white ml-auto' : role === 'system' ? 'bg-info/10 text-info mx-auto' : 'bg-white border border-border';
    list.insertAdjacentHTML('beforeend',
      '<div id="' + id + '" class="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm ' + bubbleClass + ' ' + (isLoading ? 'animate-pulse' : '') + '">' + escapeHtml(text) + '</div>'
    );
    list.scrollTop = list.scrollHeight;
    return id;
  }

  /* ============================== ICONS ============================== */
  function iconCheck(size) { return '<svg width="' + (size || 12) + '" height="' + (size || 12) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="m5 12 5 5L20 7"/></svg>'; }
  function iconClock() { return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>'; }
  function iconBike() { return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="6" cy="17" r="3"/><circle cx="18" cy="17" r="3"/><path d="M6 17 10 8h4l4 9M10 8h6"/></svg>'; }
  function warnIcon() { return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a1.5 1.5 0 0 0 1.3 2.2h17.8a1.5 1.5 0 0 0 1.3-2.2L13.7 3.9a1.5 1.5 0 0 0-2.6 0Z"/></svg>'; }
  function starIcon() { return '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m12 2 3.1 6.6 7.2.9-5.3 5 1.4 7.2L12 18l-6.4 3.7 1.4-7.2-5.3-5 7.2-.9Z"/></svg>'; }
  function heartIcon(filled) { return '<svg width="18" height="18" viewBox="0 0 24 24" fill="' + (filled ? '#ea580c' : 'none') + '" stroke="' + (filled ? '#ea580c' : 'currentColor') + '" stroke-width="2" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>'; }
  function placeholderFoodImage(name) {
    const seed = encodeURIComponent((name || 'food').slice(0, 40));
    return 'https://picsum.photos/seed/food-' + seed + '/400/300';
  }
  function placeholderRestaurantImage(name) {
    const seed = encodeURIComponent((name || 'restaurant').slice(0, 40));
    return 'https://picsum.photos/seed/rest-' + seed + '/600/400';
  }
  function debounce(fn, wait) {
    let t;
    return function (...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait); };
  }

  /* ============================== DISPATCH ============================== */
  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    initFoodModalControls();
    switch (page) {
      case 'home': initHome(); break;
      case 'restaurants': initRestaurantListing(); break;
      case 'restaurant-detail': initRestaurantDetail(); break;
      case 'food-detail': initFoodDetailPage(); break;
      case 'cart': initCartPage(); break;
      case 'checkout': initCheckoutPage(); break;
      case 'order-confirmation': initOrderConfirmation(); break;
      case 'order-tracking': initOrderTracking(); break;
      case 'profile': initProfilePage(); break;
      case 'order-history': initOrderHistory(); break;
      case 'support': initSupportPage(); break;
    }
  });
})();
