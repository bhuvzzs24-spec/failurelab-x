# Managed e-commerce sandbox

Compose starts four independent processes from the shared Python image. Their implementation is `backend/app/services/demo.py`; `DEMO_ROLE` selects gateway, order, payment or inventory. The shared image keeps contracts and authentication behavior consistent without duplicating service code.

Each process has independent HTTP and worker lifecycle; persistent records are partitioned by role in the demo PostgreSQL instance. `init.sql` provisions the demo tables. Platform experiment/evidence tables live in a separate PostgreSQL instance and use Alembic.

- Gateway: POST `/checkout`.
- Order: POST `/orders`, POST `/orders/{key}/finalize`.
- Inventory: POST `/reserve`, GET `/stock` (one SKU, capacity 100).
- Payment: POST `/charge`, persistent queue processor, TTL pause/resume control.
- Authoritative adapters: GET `/state/{key}` and authenticated DELETE `/state` reset per role.

All business/control endpoints except the internal proxied payment data boundary require the control token. Services and proxy ports are not published by Compose. All payments are fake, and reset deletes demo records. See `docs/DEMO_BUG.md` for the deliberate coordinator recovery omission.
