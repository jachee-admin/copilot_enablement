# Prompt: Row-Level Audit Trail Trigger (PostgreSQL)

## Goal
Generate an idempotent, schema-safe **PostgreSQL audit trail** that records every `INSERT`, `UPDATE`, and `DELETE` in a centralized audit table.
The trigger should log the **table name**, **operation type**, **primary key**, **changed columns**, **old/new values (as JSON)**, **username**, and **timestamp**.

This prompt demonstrates prompt discipline, data governance, and enterprise auditing principles.

---

## Context / Constraints
- PostgreSQL 15+ (supports `jsonb`, `current_user`, `TG_TABLE_NAME`, etc.)
- Use **`plpgsql`** for the trigger function.
- Use a shared audit schema: `audit`.
- Create table `audit.event_log` with columns:
  - `id` (bigserial, PK)
  - `table_name text`
  - `operation text`
  - `primary_key jsonb`
  - `changed_fields jsonb`
  - `old_data jsonb`
  - `new_data jsonb`
  - `username text`
  - `event_ts timestamptz default now()`
- Ensure the function is **reusable** — can be attached to any table.
- Detect and store only changed columns on `UPDATE`.
- Handle `INSERT`, `UPDATE`, and `DELETE` separately in a clean case block.
- No circular logging (skip audit tables themselves).
- Must be **schema-qualified** and **idempotent** (safe to re-run).
- Return `NEW` (or `OLD`) as required for trigger type.

---

## Primary Prompt (for Copilot)
> Write an idempotent PostgreSQL script that creates a shared audit trail mechanism.
> Requirements:
> 1. Create schema `audit` if it doesn’t exist.
> 2. Create table `audit.event_log` (see structure above).
> 3. Create function `audit.fn_log_event()` in PL/pgSQL that:
>    - Handles `INSERT`, `UPDATE`, and `DELETE`.
>    - On `UPDATE`, only log columns that changed.
>    - Skip logging any table inside the `audit` schema.
>    - Convert rows to `jsonb` via `to_jsonb(NEW)` and `to_jsonb(OLD)`.
>    - Derive primary key dynamically using `jsonb_build_object()` and `pg_get_constraintdef()`.
> 4. Create a helper `audit.attach_trigger(target_table)` procedure that dynamically attaches the trigger.
> 5. Make all objects `IF NOT EXISTS` safe and schema-qualified.
> 6. Include a demonstration attaching the audit trigger to a sample table `public.orders`.

---

## Acceptance Criteria
- Script is **idempotent** — re-running doesn’t duplicate objects.
- Trigger fires on all DML events, logging full JSON snapshots.
- Works generically for any table with a primary key.
- Skip auditing the `audit` schema itself.
- Lintable with `psql -f` or `pg_format`.
- Does not raise permission errors for standard users with `INSERT` rights on target tables.

---

## Reference SQL
```sql
-- audit_trail_trigger.sql
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.event_log (
    id              bigserial PRIMARY KEY,
    table_name      text NOT NULL,
    operation       text NOT NULL,
    primary_key     jsonb,
    changed_fields  jsonb,
    old_data        jsonb,
    new_data        jsonb,
    username        text DEFAULT current_user,
    event_ts        timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION audit.fn_log_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    pk_cols text[];
    pk_json jsonb;
    diff jsonb;
BEGIN
    IF TG_TABLE_SCHEMA = 'audit' THEN
        RETURN NULL;
    END IF;

    -- Build primary key JSON dynamically
    SELECT array_agg(a.attname::text)
      INTO pk_cols
      FROM pg_index i
      JOIN pg_attribute a
        ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
     WHERE i.indrelid = TG_RELID AND i.indisprimary;

    IF pk_cols IS NOT NULL THEN
        pk_json := jsonb_build_object();
        FOREACH key IN ARRAY pk_cols LOOP
            pk_json := pk_json || jsonb_build_object(key, to_jsonb(NEW.*)->key);
        END LOOP;
    END IF;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit.event_log(table_name, operation, primary_key, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, pk_json, to_jsonb(NEW));
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        -- Compute changed columns
        diff := (
          SELECT jsonb_object_agg(k, new_val)
          FROM jsonb_each(to_jsonb(NEW)) AS n(k,new_val)
          JOIN jsonb_each(to_jsonb(OLD)) AS o(k,old_val)
            ON n.k = o.k
          WHERE n.new_val IS DISTINCT FROM o.old_val
        );

        INSERT INTO audit.event_log(table_name, operation, primary_key, changed_fields, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, pk_json, diff, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit.event_log(table_name, operation, primary_key, old_data)
        VALUES (TG_TABLE_NAME, TG_OP, pk_json, to_jsonb(OLD));
        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION audit.fn_log_event() IS
'Generic trigger function for full-row JSONB audit logging.';

CREATE OR REPLACE PROCEDURE audit.attach_trigger(target_table regclass)
LANGUAGE plpgsql
AS $$
DECLARE
    tname text := quote_ident(TG_TABLE_NAME);
BEGIN
    EXECUTE format(
        'CREATE TRIGGER trg_audit_%I
         AFTER INSERT OR UPDATE OR DELETE
         ON %s
         FOR EACH ROW
         EXECUTE FUNCTION audit.fn_log_event();',
         target_table::text, target_table::text
    );
END;
$$;

-- Example usage
CREATE TABLE IF NOT EXISTS public.orders (
    id serial PRIMARY KEY,
    customer text,
    amount numeric,
    status text DEFAULT 'pending'
);

DROP TRIGGER IF EXISTS trg_audit_orders ON public.orders;
CREATE TRIGGER trg_audit_orders
AFTER INSERT OR UPDATE OR DELETE ON public.orders
FOR EACH ROW EXECUTE FUNCTION audit.fn_log_event();
```

### Verification
```bash
psql -f audit_trail_trigger.sql
psql -c "INSERT INTO public.orders (customer, amount) VALUES ('Alice', 42.50);"
psql -c "UPDATE public.orders SET status = 'paid' WHERE customer='Alice';"
psql -c "DELETE FROM public.orders WHERE customer='Alice';"
psql -c "TABLE audit.event_log;"
```

Expected: three audit entries (INSERT, UPDATE, DELETE) with proper JSON data.

---

### Follow-up Refinement Prompts

- “Enhance to log session_user, application_name, and client IP (from inet_client_addr()).”
- “Add retention policy: delete audit rows older than 90 days.”
- “Add partitioning by month on audit.event_log for scalability.”
- “Wrap creation logic in a DO \$$ ... $$ block for full idempotency.”
- “Integrate with RLS (Row-Level Security) to let auditors view only certain tables.”

