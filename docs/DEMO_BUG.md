# Deliberate bug: committed payment, unresolved order

The gateway first persists a pending order, reserves finite inventory, then calls the payment boundary with the same idempotency key. Payment enqueues a persistent job; its background loop commits `charged`. With an after-response proxy latency fault of 1.5 s, the successful acknowledgement reaches the gateway after its 0.5 s client timeout.

The gateway deliberately has no durable reconciliation or compensation for an unknown payment outcome. It returns HTTP 504 and does not finalize the pending order. Payment remains charged and inventory reserved. This is normal timeout behavior plus an omitted recovery mechanism, not a hardcoded finding.

Order, reservation and payment writes enforce key/payload consistency. Retrying checkout with the same key after cleanup reuses the existing charge and can finalize the order. The discovery workload deliberately does not repair the pending workflow by retrying; the business postcondition must converge without an external user retry within the configured window.

## Reproduce

```sh
docker compose up --build -d
docker compose exec api python scripts/seed.py
```

The seeded run performs a healthy baseline under a separate key, then the faulted workflow. Inspect `/api/v1/runs/{id}/summary`. Expected evidence when the scenario manifests:

- Baseline order finalized, payment charged, inventory reserved.
- Faulted gateway response 504.
- Authoritative payment charged, order pending, inventory reserved.
- `Charged payment implies finalized order` FAIL across the verification window and one persisted finding.
- Amount equality and finalized-implies-reserved checks PASS.
- Fault removal and final cleanup recorded; subsequent baseline succeeds.

These are scenario expectations; they are not prepopulated API responses. The test suite asserts the actual HTTP-driven state and persists only genuine FAIL evaluations as findings. Failure to read payment/order/inventory state instead yields INCONCLUSIVE and no finding.

For a healthy control experiment register the same configuration with `delay_seconds: 0.01`. The checkout should finish within the gateway timeout and all three checks should PASS. Extreme host overload can invalidate the baseline; the runner then fails the experiment without creating a fault finding.
