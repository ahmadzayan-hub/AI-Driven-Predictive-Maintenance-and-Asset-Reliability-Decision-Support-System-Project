# Local resource lifecycle during regression checks

SQLite connection context managers commit or roll back transactions but do not
close the connection. Motion operations now explicitly close each connection in
finally, retaining transaction commit/rollback and the existing lock. This fixes
Windows fixture cleanup failures and releases production operation handles too.
There is no data deletion, schema change, renderer activation or permission change.

Three subprocess tests supplied a minimal environment without SystemRoot. Windows
could not initialize _overlapped in those children. Retain that existing OS path
alongside PATH/PYTHONPATH and the no-bytecode flag. Continue excluding provider
credentials and application configuration; do not inherit the whole environment.
No OS, network, execution policy or security settings change.

Regression checks assert persisted commits, rolled-back inserts, unusable closed
connections, exclusion of credentials/configuration, and absence of invented OS
paths. Existing authorization, concurrent approval, crash/replay and privacy
assertions remain unchanged. Test-only memory and unavailable-model corrections
already on main are reused rather than weakening production resource admission.
