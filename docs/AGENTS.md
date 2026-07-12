# docs/ AGENTS.md — Documentation Instructions

## Current vs Historical Documents

- Files under `docs/release/` are historical release evidence — do not rewrite them to make them look current. They truthfully record what the state was at release time.
- Files under `docs/plans/` are implementation plans — their status headers should reflect current reality (v0.2.0 plans should show it's published; v0.3.0 plans, if any, should show they haven't started).
- `STATUS.md`, `README.md`, `docs/codex/STATUS.md` describe current public reality and must be updated when the release state changes.
- `ROADMAP.md` describes future plans — released versions should be marked as released, not as "unpublished" or "in development."

## Version and Release Truth

- v0.1.0, v0.1.1, v0.2.0, and v0.3.0 are published. Do not write about them as if they are pending, unreleased, or in release-candidate status.
- v0.3.1 is prepared and pending release. v0.4.0 has not started.
- Historical docs that reference a pre-release state for a now-published release should be updated at the top-level status line but the remainder of the document may remain if it is a faithful historical record.

## Link Conventions

- Use relative links within the repository: `[architecture](architecture.md)`. Tools like `markdown-link-check` validate these.
- External links to GitHub issues, PRs, and releases are preferred over internal copies of that content.
- Do not link to absolute local paths (e.g. `file:\\\\...` or `C:\\...` paths on the local filesystem).
- Do not link to private resources or unpublished branches.

## Command Verification

Every CLI command, slash-command, and tool shown in docs must exist in the actual parser. Verify against:
- `hardproof/commands/shared.py` (command dispatch table)
- `hardproof/commands/cli.py` (argparse subcommands)
- `hardproof/commands/slash.py` (slash command dispatch)
- `hardproof/tools/schemas.py` (tool schemas)
- `hardproof/tools/handlers.py` (tool handler registration)

Do not invent aliases or syntax that doesn't exist in the parser.

## Prohibited Content

- No local paths (e.g. `C:\\projects\\secret.txt`, `/var/tmp/data/`)
- No private transcripts
- No environment dumps
- No credentials or secret material
- No generated cache content
- No unredacted verification output

## Updating the Docs Index

When adding a new document to `docs/`, update `docs/README.md` under the appropriate category. Keep the description short (one line).

## Describing Future Roadmap Work

- Future versions are described as planned capabilities, not as shipped features.
- Use future tense or conditional language: "v0.3.0 will add..." or "Workcells is planned to add..."
- Do not claim implementation progress that hasn't happened.
