CREATE TABLE waivers (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id) ON DELETE CASCADE,
    name TEXT NOT NULL UNIQUE,
    rule_key TEXT NOT NULL CHECK(rule_key NOT LIKE 'terminal.immutable.%'),
    tool_name TEXT,
    command_sha256 TEXT CHECK(command_sha256 IS NULL OR length(command_sha256) = 64),
    path_scope TEXT,
    profile TEXT,
    stage TEXT,
    rationale TEXT NOT NULL,
    actor TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL CHECK(expires_at > created_at),
    revoked_at TEXT,
    revoked_by TEXT,
    revocation_reason TEXT,
    CHECK(
        (revoked_at IS NULL AND revoked_by IS NULL AND revocation_reason IS NULL)
        OR (revoked_at IS NOT NULL AND revoked_by IS NOT NULL AND revocation_reason IS NOT NULL)
    )
);
CREATE INDEX waivers_run_created ON waivers(run_id, created_at, id);

CREATE TABLE waiver_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    waiver_id TEXT NOT NULL REFERENCES waivers(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK(event_type IN ('created', 'revoked', 'expired')),
    actor TEXT NOT NULL,
    source TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX waiver_events_waiver_sequence ON waiver_events(waiver_id, sequence);
CREATE UNIQUE INDEX waiver_events_terminal_once
ON waiver_events(waiver_id, event_type)
WHERE event_type IN ('revoked', 'expired');

CREATE TABLE policy_decisions (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('allow', 'block', 'approval')),
    rule_key TEXT NOT NULL,
    reason TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    arguments_sha256 TEXT NOT NULL CHECK(length(arguments_sha256) = 64),
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256) = 64),
    waiver_id TEXT REFERENCES waivers(id),
    suggested_risk TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX policy_decisions_run_sequence ON policy_decisions(run_id, sequence);

CREATE TABLE risk_suggestions (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    suggested_risk TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    accepted_risk TEXT,
    override_rationale TEXT,
    created_at TEXT NOT NULL,
    accepted_by TEXT,
    accepted_source TEXT,
    decided_at TEXT,
    CHECK(
        (accepted_risk IS NULL AND accepted_by IS NULL AND accepted_source IS NULL AND decided_at IS NULL)
        OR (accepted_risk IS NOT NULL AND accepted_by IS NOT NULL AND accepted_source IS NOT NULL AND decided_at IS NOT NULL)
    ),
    CHECK(accepted_risk IS NULL OR accepted_risk = suggested_risk OR length(trim(override_rationale)) > 0)
);
CREATE INDEX risk_suggestions_run_sequence ON risk_suggestions(run_id, sequence);
