# Command Reference

All commands documented here are verified against the actual implementation in `hardproof/commands/` and `hardproof/tools/`.

## Plugin Commands

### Install and enable

```bash
pip install hardproof
hermes plugins enable hardproof
```

From GitHub:

```bash
hermes plugins install asimons81/hardproof --enable
```

### Verify

```bash
hermes hardproof doctor
```

## CLI Subcommands

All subcommands use `hermes hardproof <subcommand> [arguments]`.

| Command | Arguments | Description |
|---------|-----------|-------------|
| `start` | `<quick\|standard\|critical> <request>` | Start a new run with the given profile and request text |
| `status` | (none) | Show active run profile, stage, and pending risk suggestions |
| `approve` | `<design\|plan\|completion> [reason]` | Record human approval for the given gate |
| `waive` | `<gate> <reason>` | Record a human waiver with reason |
| `pause` | `[reason]` | Pause the active run |
| `resume` | `[run-id]` | Resume a paused run, optionally switching to a different run |
| `abort` | `<reason>` | Abort the active run (requires reason) |
| `evidence` | (none) | List verification evidence for the active run |
| `export` | `[path]` | Export run reports (markdown and JSON) |
| `doctor` | (none) | Run comprehensive system diagnostics |
| `runs` | (none) | List all runs in this workspace |
| `show` | `<run-id>` | Show details for a specific run |
| `config init` | (none) | Create a default `.hardproof/config.yaml` |
| `config validate` | (none) | Validate the current configuration |
| `config explain` | (none) | Show detailed configuration explanation |
| `db status` | (none) | Show database migration status |
| `db migrate` | (none) | Apply pending database migrations |
| `db migrate --dry-run` | (none) | Preview pending migrations without applying |
| `complete` | (none) | Complete the active run (requires fresh evidence and human approval) |
| `policy` | `<args>` | Policy operations |
| `migrate-state` | (none) | Migrate `.crucible/` state directory to `.hardproof/` |

## Slash-Command Equivalents

All CLI subcommands work in Hermes messaging interfaces using the slash-command prefix:

```
/hardproof start quick "Fix typo in README"
/hardproof status
/hardproof approve design "Approved"
/hardproof doctor
/hardproof db status
```

The slash handler accepts the same arguments as the CLI, separated by spaces (quoted for multi-word values).

## Registered Tools

Six tools are registered through the `hermes_agent.plugins` entry point. They are model-callable in active Hermes sessions.

| Tool | Purpose |
|------|---------|
| `hardproof_run` | Start, inspect, pause, resume, or abort a run. Actions: `start`, `status`, `pause`, `resume`, `abort`. |
| `hardproof_record` | Record a run artifact, decision, review, learning item, or risk. Kinds: `artifact`, `decision`, `discovery`, `design`, `plan`, `review`, `learning`, `risk`. |
| `hardproof_task` | Create, update, list, or inspect durable implementation tasks. Actions: `create`, `update`, `list`, `get`. |
| `hardproof_transition` | Request a stage transition after recording required artifacts. Target stages: INTAKE, DISCOVERY, DESIGN, PLAN, IMPLEMENT, REVIEW, VERIFY, DELIVER, LEARN, PAUSED, ABORTED, COMPLETE. |
| `hardproof_verify` | Run configured verification checks through Hermes and record workspace-bound evidence. |
| `hardproof_report` | Inspect status or evidence and export run reports. Actions: `status`, `evidence`, `export`, `completion`, `policy_explain`, `risk_suggest`. |

### Tool Limitations

- Tools cannot create human approvals or waivers.
- Tools cannot modify human authority records.
- Tools cannot create, extend, revoke, accept, or override human authority records.
- Risk suggestions from `hardproof_report` with action `risk_suggest` are advisory; they cannot silently alter profile or task risk.

## Profiles

| Profile | Best For | Approvals Required | Evidence Required |
|---------|----------|-------------------|-------------------|
| Quick | Typo fixes, doc updates, one-line changes | None | At least one fresh check |
| Standard | Features, refactors, multi-file changes | Design, Plan, Completion | Fresh verification |
| Critical | Auth, data, migrations, production config | Design, Plan, Completion (all required) + destructive-action approvals | At least two checks, all required |
