"""Restricted repair surface. Values select real transaction recovery algorithms."""
POLICIES = {
    'payment_ack_loss': False,
    'unsafe_retry': False,
    'lost_finalization': False,
    'inventory_drift': False,
    'concurrent_retry': False,
    'failed_compensation': False,
}
