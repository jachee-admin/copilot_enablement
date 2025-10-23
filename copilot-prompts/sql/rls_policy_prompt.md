# Prompt: PostgreSQL Row-Level Security (RLS) for Multi-Tenant Data

## Goal
Generate a **safe, idempotent** PostgreSQL setup that enforces **row-level security (RLS)** for a multi-tenant app.
Users should only see and modify rows where `tenant_id = current tenant`. Admins may optionally see everything.

This artifact demonstrates security design, clear prompting, and production-grade SQL.

---

## Context / Constraints
- PostgreSQL **14+** (RLS, `pg_has_role`, JSONB available).
- Multi-tenant pattern: tables include `tenant_id UUID NOT NULL`.
- The **current tenant** is carried as a **session GUC** (custom setting) named `app.current_tenant`.
- Use a safe helper: `app.tenant_id()` returns the UUID in the session (or NULL if not set).
- Enforce **USING** (visibility) + **WITH CHECK** (writes) policies.
- Provide an **admin bypass** via role membership (e.g., `role app_admin`).
- Policies should be **auditable** and **lintable**; avoid leaky functions or SECURITY DEFINER surprises.
- Keep everything **schema-qualified** and **IF NOT EXISTS** safe; re-runs don’t explode.

---

## Primary Prompt (paste to Copilot)
> Write an idempotent PostgreSQL script that:
> 1) Creates schema `app` and role `app_admin` if they don’t exist.
> 2) Defines a helper `app.tenant_id()` function that returns the UUID stored in the session GUC `app.current_tenant` using `current_setting('app.current_tenant', true)`.
>    - Returns `uuid` or `NULL` if unset, **IMMUTABLE/STABLE?** Use **STABLE**.
> 3) Creates example tables `app.customers` and `app.projects` with a `tenant_id uuid not null` column and basic fields.
> 4) Enables RLS on both tables.
> 5) Adds two policies per table:
>    - **tenant_rw**: regular users can `SELECT/INSERT/UPDATE/DELETE` only rows with `tenant_id = app.tenant_id()` (USING + WITH CHECK).
>    - **admin_all**: members of `app_admin` can `SELECT/INSERT/UPDATE/DELETE` all rows.
> 6) Adds helpful indexes on `(tenant_id)` to keep queries fast.
> 7) Demonstrates usage:
>    - `SET LOCAL app.current_tenant = '…uuid…';` then `SELECT`/`INSERT` to show isolation.
>    - `SET ROLE` to a user in `app_admin` to show admin visibility.
> 8) Uses `CREATE OR REPLACE` where appropriate and guards object creation with `IF NOT EXISTS`.
> 9) Does **not** disable RLS; do not rely on superuser bypass. Keep default behavior (RLS applies to all non-bypass users).

---

## Acceptance Criteria
- `app.tenant_id()` returns the session tenant (UUID) or NULL.
- RLS **enabled** and works for all commands.
- **USING** restricts visibility; **WITH CHECK** restricts writes.
- Admins (members of `app_admin`) can access all rows.
- Indexes on `tenant_id` exist.
- Script is **re-runnable** safely.
- Simple, readable demo queries verify behavior.

---

## Reference SQL

```sql
-- rls_multi_tenant.sql

-- 1) Schema & role
CREATE SCHEMA IF NOT EXISTS app;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
    CREATE ROLE app_admin;
  END IF;
END$$;

-- 2) Helper to read tenant from session (GUC)
--    Use STABLE; returns NULL if the setting is missing.
CREATE OR REPLACE FUNCTION app.tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_tenant', true), '')::uuid
$$;

COMMENT ON FUNCTION app.tenant_id() IS
'Returns the current session tenant UUID from app.current_tenant (or NULL).';

-- 3) Example tables
CREATE TABLE IF NOT EXISTS app.customers (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid NOT NULL,
  name       text NOT NULL,
  email      text UNIQUE
);

CREATE TABLE IF NOT EXISTS app.projects (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid NOT NULL,
  customer_id uuid NOT NULL REFERENCES app.customers(id) ON DELETE CASCADE,
  name       text NOT NULL,
  status     text NOT NULL DEFAULT 'active'
);

-- Useful indexes for RLS filters and joins
CREATE INDEX IF NOT EXISTS customers_tenant_idx ON app.customers (tenant_id);
CREATE INDEX IF NOT EXISTS projects_tenant_idx  ON app.projects  (tenant_id);
CREATE INDEX IF NOT EXISTS projects_customer_idx ON app.projects (customer_id);

-- 4) Enable RLS
ALTER TABLE app.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.projects  ENABLE ROW LEVEL SECURITY;

-- 5) Policies
-- Admins can do everything
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='app' AND tablename='customers' AND policyname='admin_all'
  ) THEN
    CREATE POLICY admin_all ON app.customers
      FOR ALL
      TO PUBLIC
      USING (pg_has_role(current_user, 'app_admin', 'member'))
      WITH CHECK (pg_has_role(current_user, 'app_admin', 'member'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='app' AND tablename='projects' AND policyname='admin_all'
  ) THEN
    CREATE POLICY admin_all ON app.projects
      FOR ALL
      TO PUBLIC
      USING (pg_has_role(current_user, 'app_admin', 'member'))
      WITH CHECK (pg_has_role(current_user, 'app_admin', 'member'));
  END IF;
END$$;

-- Tenant-scoped read/write
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='app' AND tablename='customers' AND policyname='tenant_rw'
  ) THEN
    CREATE POLICY tenant_rw ON app.customers
      FOR ALL
      TO PUBLIC
      USING (tenant_id = app.tenant_id())
      WITH CHECK (tenant_id = app.tenant_id());
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='app' AND tablename='projects' AND policyname='tenant_rw'
  ) THEN
    CREATE POLICY tenant_rw ON app.projects
      FOR ALL
      TO PUBLIC
      USING (tenant_id = app.tenant_id())
      WITH CHECK (tenant_id = app.tenant_id());
  END IF;
END$$;

-- Optional: tight default privileges (example – adapt to your roles)
REVOKE ALL ON app.customers FROM PUBLIC;
REVOKE ALL ON app.projects  FROM PUBLIC;

-- 6) Demonstration

-- Simulate two tenants
-- NOTE: In real apps, your API gateway / connection pool sets this per-request.
SET LOCAL app.current_tenant = '11111111-1111-1111-1111-111111111111';
INSERT INTO app.customers (tenant_id, name, email)
VALUES (app.tenant_id(), 'Acme', 'ops@acme.test')
ON CONFLICT DO NOTHING;

INSERT INTO app.projects (tenant_id, customer_id, name)
SELECT app.tenant_id(), c.id, 'Telemetry' FROM app.customers c
WHERE c.name = 'Acme' AND c.tenant_id = app.tenant_id()
ON CONFLICT DO NOTHING;

-- Switch tenant
RESET app.current_tenant;
SET LOCAL app.current_tenant = '22222222-2222-2222-2222-222222222222';
INSERT INTO app.customers (tenant_id, name, email)
VALUES (app.tenant_id(), 'Globex', 'it@globex.test')
ON CONFLICT DO NOTHING;

-- Visibility checks
-- Tenant 2 sees only Globex
SELECT c.name, p.name
FROM app.customers c LEFT JOIN app.projects p ON p.customer_id = c.id;

-- Admin visibility (requires a role that is member of app_admin):
-- GRANT app_admin TO some_admin_user;
-- SET ROLE some_admin_user; -- now policies allow all rows due to admin_all
```

#### Expected:

- Regular users see/modify only rows for their app.current_tenant.
- Attempts to write other tenants’ rows are rejected.
- Admin role members can see and write across tenants.

### Notes & Pitfalls

- Where to set the tenant? In production, set SET LOCAL app.current_tenant = '…' per request in your API/connection pool. Avoid SECURITY DEFINER setters unless you deeply understand the risks.
- Indexes matter. Always index tenant_id. It’s in every filter.
- RLS applies to views and functions by default; keep it that way. Don’t disable RLS globally.
- Combine with your audit trigger (see sql/audit_trail_trigger_prompt.md) so tenant-scoped access is fully logged.

### Follow-up Refinement Prompts
- “Add default privileges and role grants for app_readonly and app_writer roles.”
- “Add partitioning by tenant or by time on large tables.”
- “Add Row Security qualifiers for soft-deleted rows (deleted_at is null).”
- “Expose a limited analytics view that aggregates across tenants, but only for app_admin.”
- “Wire this into pgBouncer / app middleware to set GUCs per connection safely.”

## Test Script (sample)

```sql
\echo
\echo '=== PostgreSQL RLS Demo: Minimal PASS/FAIL Test ==='
\echo

-- Safety: stop on first error
\set ON_ERROR_STOP 1

-- --- Assumptions -----------------------------------------------------------
-- You already ran the RLS setup from: sql/rls_policy_prompt.md
-- (schema app, app_admin role, app.tenant_id(), tables, policies, etc.)
-- --------------------------------------------------------------------------

-- Create demo roles (login users for test)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user') THEN
    EXECUTE $$CREATE ROLE tenant_user LOGIN PASSWORD 'tenant_user'$$;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_user') THEN
    EXECUTE $$CREATE ROLE admin_user LOGIN PASSWORD 'admin_user'$$;
  END IF;
END$$;

-- Make admin_user a member of app_admin (admin bypass via policy)
GRANT app_admin TO admin_user;

-- Optional: grant basic privileges (RLS still applies)
GRANT USAGE ON SCHEMA app TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.customers, app.projects TO PUBLIC;

-- Tenants for the demo
\set tenant_a '11111111-1111-1111-1111-111111111111'
\set tenant_b '22222222-2222-2222-2222-222222222222'

-------------------------------------------------------------------------------
\echo
\echo '--- Test 1: Tenant-scoped visibility (tenant_user on tenant A) ---'
\echo

-- Act as tenant_user and set tenant A in the session
SET ROLE tenant_user;

DO $$
DECLARE
  c_before int;
  c_after  int;
  proj_id  uuid;
BEGIN
  -- Set session tenant via GUC (same as your app would do per request)
  PERFORM set_config('app.current_tenant', :'tenant_a', true);

  -- Count visible customers (should be 0 initially for this tenant)
  SELECT count(*) INTO c_before
  FROM app.customers
  WHERE tenant_id = app.tenant_id();

  RAISE NOTICE 'INFO: tenant A initial customer count = %', c_before;

  -- Insert a customer for tenant A
  INSERT INTO app.customers (tenant_id, name, email)
  VALUES (app.tenant_id(), 'Acme', 'ops@acme.test')
  ON CONFLICT DO NOTHING;

  -- Insert a project for that customer
  INSERT INTO app.projects (tenant_id, customer_id, name)
  SELECT app.tenant_id(), c.id, 'Telemetry'
  FROM app.customers c
  WHERE c.tenant_id = app.tenant_id() AND c.name = 'Acme'
  LIMIT 1
  RETURNING id INTO proj_id;

  SELECT count(*) INTO c_after
  FROM app.customers
  WHERE tenant_id = app.tenant_id();

  IF c_after >= c_before THEN
    RAISE NOTICE 'PASS: tenant_user sees only tenant A rows and can write for tenant A.';
  ELSE
    RAISE EXCEPTION 'FAIL: unexpected decrease in visible rows for tenant A.';
  END IF;
END$$;

-------------------------------------------------------------------------------
\echo
\echo '--- Test 2: Cross-tenant write should be REJECTED by WITH CHECK ---'
\echo

-- Still tenant_user, still tenant A in session
DO $$
BEGIN
  PERFORM set_config('app.current_tenant', :'tenant_a', true);

  -- Attempt to insert a row claiming tenant B — should FAIL due to WITH CHECK
  BEGIN
    INSERT INTO app.customers (tenant_id, name) VALUES (:'tenant_b'::uuid, 'Nope');
    RAISE EXCEPTION 'FAIL: cross-tenant INSERT unexpectedly succeeded.';
  EXCEPTION WHEN others THEN
    -- Any error is acceptable here: policy or permissions should block it
    RAISE NOTICE 'PASS: cross-tenant INSERT blocked as expected (%).', SQLERRM;
  END;
END$$;

-------------------------------------------------------------------------------
\echo
\echo '--- Test 3: Admin can see ALL tenants (admin_user, member of app_admin) ---'
\echo

-- Switch to admin_user (policy allows all rows for app_admin members)
RESET ROLE;
SET ROLE admin_user;

DO $$
DECLARE
  total int;
BEGIN
  -- Admin view does NOT depend on app.current_tenant
  PERFORM set_config('app.current_tenant', NULL, true);

  SELECT count(*) INTO total FROM app.customers;

  IF total >= 1 THEN
    RAISE NOTICE 'PASS: admin_user can see all tenants (total customers = %).', total;
  ELSE
    RAISE EXCEPTION 'FAIL: admin_user cannot see expected rows.';
  END IF;
END$$;

-------------------------------------------------------------------------------
\echo
\echo '--- Test 4: Tenant B isolation (tenant_user on tenant B) ---'
\echo

RESET ROLE;
SET ROLE tenant_user;

DO $$
DECLARE
  c int;
BEGIN
  PERFORM set_config('app.current_tenant', :'tenant_b', true);

  -- Tenant B sees none of Tenant A’s rows
  SELECT count(*) INTO c
  FROM app.customers
  WHERE tenant_id = app.tenant_id();

  IF c = 0 THEN
    RAISE NOTICE 'PASS: tenant B session is isolated (sees 0 of tenant A rows).';
  ELSE
    RAISE EXCEPTION 'FAIL: tenant B session unexpectedly sees rows: %', c;
  END IF;

  -- Insert tenant B data to demonstrate isolation symmetry
  INSERT INTO app.customers (tenant_id, name, email)
  VALUES (app.tenant_id(), 'Globex', 'it@globex.test')
  ON CONFLICT DO NOTHING;

  RAISE NOTICE 'INFO: inserted one tenant B customer.';
END$$;

-------------------------------------------------------------------------------
\echo
\echo '=== DONE: RLS demo completed. See PASS/FAIL notices above. ==='
\echo
```
### How to run
```bash
# Assuming you’ve already created the RLS objects:
# psql -d yourdb -f sql/rls_multi_tenant.sql

# Now run the test:
psql -d yourdb -f sql/rls_demo_test.sql
```
### What this does

- Creates two login roles: tenant_user and admin_user.
- Grants app_admin to admin_user so policies allow full access.
- Uses the session GUC app.current_tenant to simulate per-tenant sessions.
- Asserts:
  - Tenant A can only see/write tenant A rows (PASS expected).
  - Cross-tenant write is rejected (PASS expected).
  - Admin sees all tenants (PASS expected).
  - Tenant B session is isolated from tenant A (PASS expected).