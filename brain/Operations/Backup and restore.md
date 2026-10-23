---
type: operation
aliases: []
tags: [operations]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/backup.py, scripts/backup.py, scripts/restore.py, docs/adr/0005-backup-and-restore.md]
---

# Backup and restore

Backup and restore preserves durable application records and verifies that recovered work can continue.

## Recovery model

- The portable database backup is a versioned JSON representation, with validation before replacement.
- Restore replaces database content rather than merging arbitrary current rows into the backup.
- A useful drill verifies resumed work and spent approvals, not merely the existence of an output file.
- Local file-based memory must be considered separately from database-backed hosted memory.
- Backup files contain user data. Protect their storage; neither encryption nor an operational backup schedule is implied by having the scripts.

## Related

- [[Run lifecycle]] defines what must resume.
- [[Approval gate]] must retain its decisions after recovery.
- [[Release acceptance]] includes operational recovery evidence.
- [[Soul]] keeps backup data out of Git.
- [[Home]] maps operational controls.
