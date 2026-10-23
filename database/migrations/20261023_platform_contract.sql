-- Additive deployment migration. Review/apply through the database operator;
-- changing this file does not apply it to any hosted database.
BEGIN;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS request_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS runs_idempotency ON runs (owner, idempotency_key);
CREATE INDEX IF NOT EXISTS tasks_role_state_run ON tasks (role, state, run_id);
COMMIT;
