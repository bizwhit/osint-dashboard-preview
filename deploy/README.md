# Gated deployment stack

This separate stack does not overwrite the original development Compose file.

## Before startup

1. Apply migrations 001 through 004 in Supabase. Migration 004 intentionally aborts if duplicate child targets exist; reconcile those records without deleting evidence blindly.
2. Create an untracked `deploy/htpasswd` file using a password manager and an htpasswd-compatible tool. This gateway credential protects the entire workspace; the separate API admin password still controls audit and health endpoints.
3. Set SUPABASE_URL, SUPABASE_KEY, ADMIN_PASSWORD (unique, at least 24 characters), PUBLIC_ORIGIN and PUBLIC_WS_ORIGIN in the shell or an untracked environment file. Local values: http://localhost:8080 and ws://localhost:8080. Hosted values must use https:// and wss://. No trailing slashes.
4. Run `docker compose -f deploy/compose.yml config` and then `docker compose -f deploy/compose.yml up --build -d` from the repository root. Browse localhost:8080 locally.
5. For remote use put a TLS-terminating, authenticated edge in front of loopback port 8080. Do not expose the HTTP listener publicly or change the bind to 0.0.0.0 without a reviewed TLS configuration. Browser API URLs are build-time settings; rebuild frontend when the public origin changes.

Only loopback port 8080 is published. API, worker, Redis, frontend and SpiderFoot have no host port mappings. The private network isolates service ingress; backend, worker and SpiderFoot also have egress for authorized collection. CORS is an explicit allowlist, not authentication. Nginx gateway authentication covers API and WebSocket traffic, with only a static proxy liveness endpoint exempted.

Health checks cover frontend HTTP, API HTTP, Redis PING, targeted Celery ping, and proxy liveness. They do not prove Supabase migrations or individual collection tools work. Run `docker compose -f deploy/compose.yml ps` and inspect logs. No database migration or live collection runs automatically.

## Validation and limitations

Run `PYTHONPATH=backend python -m pytest backend/tests -q` after installing backend requirements and pytest; run `npm install && npm run build` inside frontend. CI performs these checks on push. The tests mock external services: they do not constitute a live end-to-end scan or a real PostgreSQL race test.

The child uniqueness key uses exact query text. It does not canonicalize phone formats or username case. The insert constraint arbitrates concurrent duplicate child creation. Pivot depth is checked against the persisted parent. Database insert and Celery enqueue are not transactional; dispatch failure marks the child failed and needs operator recovery. A transactional outbox remains future work. Existing email, phone and domain workers do not gain new automatic pivot behavior in this patch.

This is a deployment baseline, not a claim of production readiness. Before internet-facing use, upgrade and audit pinned frontend dependencies, add a lockfile, pin container digests including SpiderFoot, verify each tool's actual CLI/output format, test the full stack, and implement per-user authorization/data isolation for multi-user use. Shared gateway authentication does not provide tenant isolation. Existing case completion semantics may still report completed after individual tool failures.
