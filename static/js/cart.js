/**
 * cart.js — LocalStorage-backed cart state (task.md §16/18: cart data is
 * safe to persist in LocalStorage; never store payment or password data
 * here). Cross-tab sync via the `storage` event so the badge/cart page
 * stay accurate if the cart is edited in another tab.
 *
 * A cart item shape:
 * {
 *   id: string (client-generated line id),
 *   menuItemId, restaurantId, name, image, unitPrice,
 *   quantity, addOns: [{id,name,price}], specialInstructions
 * }
 */
(function (global) {
  const CART_KEY = 'foodflow_cart';
  const listeners = new Set();

  function readCart() {
    try {
      const raw = localStorage.getItem(CART_KEY);
      const parsed = raw ? JSON.parse(raw) : { restaurantId: null, items: [], couponCode: null };
      if (!Array.isArray(parsed.items)) parsed.items = [];
      return parsed;
    } catch (e) {
      return { restaurantId: null, items: [], couponCode: null };
    }
  }

  function writeCart(cart) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(cart));
    } catch (e) { /* storage full or unavailable */ }
    notify(cart);
  }

  function notify(cart) {
    listeners.forEach((fn) => {
      try { fn(cart); } catch (e) { /* listener error should not break cart */ }
    });
  }

  function onChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  // Cross-tab sync
  window.addEventListener('storage', (e) => {
    if (e.key === CART_KEY) notify(readCart());
  });

  function lineTotal(item) {
    const addOnsTotal = (item.addOns || []).reduce((sum, a) => sum + (Number(a.price) || 0), 0);
    return (Number(item.unitPrice) + addOnsTotal) * Number(item.quantity || 1);
  }

  function subtotal() {
    return readCart().items.reduce((sum, item) => sum + lineTotal(item), 0);
  }

  function itemCount() {
    return readCart().items.reduce((sum, item) => sum + Number(item.quantity || 1), 0);
  }

  /**
   * Adding an item from a different restaurant replaces the cart (single-restaurant
   * cart, matching how most food-delivery apps work) — the caller should confirm
   * with the user before calling addItem in that scenario if desired.
   */
  function addItem(item) {
    const cart = readCart();
    if (cart.restaurantId && item.restaurantId && cart.restaurantId !== item.restaurantId) {
      cart.items = [];
      cart.couponCode = null;
    }
    cart.restaurantId = item.restaurantId || cart.restaurantId;

    const existing = cart.items.find(
      (i) => i.menuItemId === item.menuItemId && JSON.stringify(i.addOns || []) === JSON.stringify(item.addOns || []) && i.specialInstructions === item.specialInstructions
    );
    if (existing) {
      existing.quantity = Number(existing.quantity || 1) + Number(item.quantity || 1);
    } else {
      cart.items.push(Object.assign({ id: 'line_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7) }, item));
    }
    writeCart(cart);
    return cart;
  }

  function updateQuantity(lineId, quantity) {
    const cart = readCart();
    const item = cart.items.find((i) => i.id === lineId);
    if (!item) return cart;
    if (quantity <= 0) {
      cart.items = cart.items.filter((i) => i.id !== lineId);
    } else {
      item.quantity = quantity;
    }
    if (cart.items.length === 0) cart.restaurantId = null;
    writeCart(cart);
    return cart;
  }

  function removeItem(lineId) {
    return updateQuantity(lineId, 0);
  }

  function clearCart() {
    const cart = { restaurantId: null, items: [], couponCode: null };
    writeCart(cart);
    return cart;
  }

  function setCoupon(code) {
    const cart = readCart();
    cart.couponCode = code || null;
    writeCart(cart);
    return cart;
  }

  global.FoodFlowCart = {
    readCart,
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
    setCoupon,
    subtotal,
    itemCount,
    lineTotal,
    onChange
  };
})(window);
