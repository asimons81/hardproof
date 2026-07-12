# ADR 0012: Transactional Workcell Claims

- Status: Accepted
- Date: 2026-07-11

SQLite `BEGIN IMMEDIATE` claims a ready task before launch and associates a
unique attempt and launch token with that claim. At most one active attempt is
permitted for a task. Expired or interrupted claims are reconciled explicitly;
they are never silently stolen or relaunched.
