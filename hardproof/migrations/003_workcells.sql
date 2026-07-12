CREATE TABLE workcell_graph_revisions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK(revision > 0),
    approved_plan_artifact_id TEXT REFERENCES artifacts(id) ON DELETE RESTRICT,
    approved_plan_sha256 TEXT,
    graph_sha256 TEXT NOT NULL CHECK(length(graph_sha256) = 64),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    rationale TEXT NOT NULL,
    UNIQUE(run_id, revision)
);
CREATE INDEX workcell_graph_revisions_run_revision
ON workcell_graph_revisions(run_id, revision);

CREATE TABLE workcell_tasks (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    graph_revision_id TEXT NOT NULL REFERENCES workcell_graph_revisions(id) ON DELETE RESTRICT,
    task_key TEXT NOT NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    acceptance_json TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0, 1)),
    read_scope_json TEXT NOT NULL,
    write_scope_json TEXT NOT NULL,
    brief_path TEXT,
    context_manifest_path TEXT,
    result_path TEXT,
    wave_number INTEGER CHECK(wave_number IS NULL OR wave_number > 0),
    priority INTEGER NOT NULL DEFAULT 0,
    model_tier TEXT NOT NULL,
    maximum_attempts INTEGER NOT NULL CHECK(maximum_attempts BETWEEN 1 AND 10),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
    status TEXT NOT NULL,
    blocking_reason TEXT,
    escalation_state TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(run_id, task_key)
);
CREATE INDEX workcell_tasks_run_status ON workcell_tasks(run_id, status, priority, task_key);

CREATE TABLE workcell_task_dependencies (
    task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE CASCADE,
    dependency_task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE RESTRICT,
    required INTEGER NOT NULL CHECK(required IN (0, 1)),
    created_at TEXT NOT NULL,
    PRIMARY KEY(task_id, dependency_task_id),
    CHECK(task_id <> dependency_task_id)
);
CREATE INDEX workcell_task_dependencies_dependency ON workcell_task_dependencies(dependency_task_id);

CREATE TABLE workcell_attempts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE RESTRICT,
    attempt_number INTEGER NOT NULL CHECK(attempt_number > 0),
    state TEXT NOT NULL,
    launch_token TEXT NOT NULL UNIQUE,
    model_tier TEXT NOT NULL,
    context_sha256 TEXT NOT NULL CHECK(length(context_sha256) = 64),
    brief_path TEXT NOT NULL,
    context_manifest_path TEXT NOT NULL,
    result_path TEXT NOT NULL,
    child_session_id TEXT,
    child_handle_json TEXT,
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    terminal_reason TEXT,
    UNIQUE(task_id, attempt_number)
);
CREATE INDEX workcell_attempts_task_state ON workcell_attempts(task_id, state, attempt_number);
CREATE UNIQUE INDEX workcell_attempts_one_active_per_task
ON workcell_attempts(task_id)
WHERE state IN ('starting', 'running');

CREATE TABLE workcell_claims (
    task_id TEXT PRIMARY KEY REFERENCES workcell_tasks(id) ON DELETE CASCADE,
    attempt_id TEXT NOT NULL UNIQUE REFERENCES workcell_attempts(id) ON DELETE CASCADE,
    claim_token TEXT NOT NULL UNIQUE,
    claimant TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    CHECK(expires_at > acquired_at)
);

CREATE TABLE workcell_lifecycle_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE CASCADE,
    attempt_id TEXT NOT NULL REFERENCES workcell_attempts(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    child_session_id TEXT,
    previous_state TEXT,
    new_state TEXT,
    details_json TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX workcell_lifecycle_events_attempt_sequence
ON workcell_lifecycle_events(attempt_id, sequence);

CREATE TABLE workcell_retry_decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE CASCADE,
    previous_attempt_id TEXT NOT NULL REFERENCES workcell_attempts(id) ON DELETE RESTRICT,
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    material_change TEXT NOT NULL,
    old_context_sha256 TEXT NOT NULL CHECK(length(old_context_sha256) = 64),
    new_context_sha256 TEXT NOT NULL CHECK(length(new_context_sha256) = 64),
    old_model_tier TEXT NOT NULL,
    new_model_tier TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK(old_context_sha256 <> new_context_sha256 OR old_model_tier <> new_model_tier OR length(trim(material_change)) > 0)
);

CREATE TABLE workcell_escalations (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES workcell_tasks(id) ON DELETE CASCADE,
    attempt_id TEXT REFERENCES workcell_attempts(id) ON DELETE SET NULL,
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution TEXT
);
