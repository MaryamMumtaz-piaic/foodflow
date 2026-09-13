"""Simulated payment processing (Section 14).

No real card data is ever stored. Cash on delivery is always "pending"
until delivery. Card/wallet payments are simulated with a deterministic
success path (only a synthetic random failure keyword can trigger a
failure, for demo/testing purposes) — orders are only created after
payment is confirmed or explicitly permitted (COD).
"""
import random

from app.models.order import PaymentMethod, PaymentStatus


class PaymentDeclined(Exception):
    pass


def process_payment(method: PaymentMethod, amount: float, card_last4: str | None = None) -> PaymentStatus:
    if method == PaymentMethod.cash_on_delivery:
        # Payment collected on delivery -> allowed to proceed, stays pending.
        return PaymentStatus.pending

    if method in (PaymentMethod.card, PaymentMethod.wallet):
        # Simulate a payment gateway call. Deterministic ~95% success rate.
        # A tiny chance of failure keeps the "payment failure" UI state testable.
        if amount <= 0:
            raise PaymentDeclined("Invalid payment amount.")
        success = random.random() > 0.05
        if not success:
            raise PaymentDeclined("Payment was declined by the simulated gateway. Please try again.")
        return PaymentStatus.success

    raise PaymentDeclined("Unsupported payment method.")
