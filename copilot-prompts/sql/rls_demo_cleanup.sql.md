## RLS Demo Cleanup Script
Removes the demo users, tenant data, and test artifacts but leaves the core RLS objects (schema, roles, policies) untouched so you can re-run tests later.

```sql
\echo
\echo '=== PostgreSQL RLS Demo Cleanup ==='
\echo

\set ON_ERROR_STOP 1

-- Optional: confirm before dropping users
-- \prompt 'This will delete demo users and data. Continue? [y/N] ' _ans
-- \if :_ans != 'y'
--   \echo 'Aborted.'
--   \quit
-- \endif

-- Drop demo data safely
DO $$
BEGIN
  IF to_regclass('app.projects') IS NOT NULL THEN
    DELETE FROM app.projects;
  END IF;

  IF to_regclass('app.customers') IS NOT NULL THEN
    DELETE FROM app.customers;
  END IF;
END$$;

-- Drop demo roles if they exist
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user') THEN
    REASSIGN OWNED BY tenant_user TO CURRENT_USER;
    DROP OWNED BY tenant_user;
    DROP ROLE tenant_user;
    RAISE NOTICE 'Dropped role tenant_user';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_user') THEN
    REASSIGN OWNED BY admin_user TO CURRENT_USER;
    DROP OWNED BY admin_user;
    DROP ROLE admin_user;
    RAISE NOTICE 'Dropped role admin_user';
  END IF;
END$$;

-- Clear test tenants if you prefer a clean baseline
-- You can safely TRUNCATE if you don’t want to lose structural metadata
TRUNCATE TABLE app.customers RESTART IDENTITY CASCADE;
TRUNCATE TABLE app.projects  RESTART IDENTITY CASCADE;

\echo
\echo '=== Cleanup complete. Demo users and data removed. ==='
\echo
```

### How to run
```bash
psql -d yourdb -f sql/rls_demo_cleanup.sql
```
### What it does
- Deletes all rows from app.customers and app.projects.
- Drops the two demo roles: tenant_user and admin_user.
- Keeps all RLS infrastructure (app_admin, policies, tenant_id() function, etc.) intact.
- Emits clear notices so you can tell what happened.