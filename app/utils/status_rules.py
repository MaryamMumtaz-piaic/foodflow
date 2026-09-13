"""Order status transition state machine (Section 13 of task.md).

pending -> accepted -> preparing -> ready_for_pickup -> rider_assigned ->
picked_up -> out_for_delivery -> delivered

cancelled / failed / rejected are terminal states reachable from certain
non-terminal states. Invalid transitions raise StatusTransitionError so
routes can return a clear 400 error.
"""
from app.models.order import OrderStatus

# Which statuses each status is allowed to move to.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.accepted, OrderStatus.rejected, OrderStatus.cancelled},
    OrderStatus.accepted: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.ready_for_pickup, OrderStatus.cancelled},
    OrderStatus.ready_for_pickup: {OrderStatus.rider_assigned, OrderStatus.cancelled},
    OrderStatus.rider_assigned: {OrderStatus.picked_up, OrderStatus.failed, OrderStatus.cancelled},
    OrderStatus.picked_up: {OrderStatus.out_for_delivery, OrderStatus.failed},
    OrderStatus.out_for_delivery: {OrderStatus.delivered, OrderStatus.failed},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
    OrderStatus.failed: set(),
    OrderStatus.rejected: set(),
}

TERMINAL_STATUSES = {OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.failed, OrderStatus.rejected}


class StatusTransitionError(Exception):
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition order from '{current}' to '{target}'.")


def validate_transition(current: OrderStatus, target: OrderStatus) -> None:
    if current == target:
        raise StatusTransitionError(current.value, target.value)
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise StatusTransitionError(current.value, target.value)


def can_cancel(current: OrderStatus) -> bool:
    return current in {
        OrderStatus.pending,
        OrderStatus.accepted,
        OrderStatus.preparing,
        OrderStatus.ready_for_pickup,
        OrderStatus.rider_assigned,
    }
