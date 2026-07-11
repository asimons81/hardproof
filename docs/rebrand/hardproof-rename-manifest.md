# Hardproof Rename Manifest

Complete identity surface audit and migration plan for the Crucible → Hardproof rename.

Generated: 2026-07-11 | Baseline: 310 tests, Ruff pass, mypy strict pass

## Rename Surface Inventory

| Surface | Old Value | New Value | Files Affected | Compatibility Requirement | Migration Requirement | Verification Method | Status |
|---------|-----------|-----------|----------------|--------------------------|----------------------|---------------------|--------|
| Product name | Crucible | Hardproof | All docs, README, CHANGELOG, ROADMAP, ADRs, codex docs | None (name change) | None | grep for "Crucible" in prose | PENDING |
| Display wordmark | Crucible / CRUCIBLE | HARDPROOF | README, docs headers, reports | None | None | grep for "CRUCIBLE" | PENDING |
| Python distribution | crucible-agent | hardproof | pyproject.toml, scripts/smoke_install.py, scripts/build_sbom.py, CI workflows, docs | pip install name changes | User must uninstall old, install new | `pip install hardproof` | PENDING |
| Python import package | crucible_agent | hardproof | All 50 .py files, pyproject.toml [tool.setuptools], CI, tests (90 files) | Import path changes | None (new install) | `import hardproof` works | PENDING |
| Package directory | crucible_agent/ | hardproof/ | Entire package tree rename | Directory rename | None | `ls hardproof/` | PENDING |
| Plugin key | crucible | hardproof | plugin.yaml, constants.py, commands/cli.py, commands/slash.py, tools/handlers.py, all tests | Plugin registration | Users must `hermes plugins enable hardproof` | Plugin discovery | PENDING |
| Entry point | crucible = crucible_agent.plugin | hardproof = hardproof.plugin | pyproject.toml [project.entry-points] | Entry point rename | None | `importlib.metadata.entry_points` | PENDING |
| Slash command | /crucible | /hardproof | commands/slash.py, README, docs, tests | Slash command name | User muscle memory | `/hardproof status` | PENDING |
| CLI command | hermes crucible | hermes hardproof | commands/cli.py, README, docs, tests | CLI command name | User muscle memory | `hermes hardproof status` | PENDING |
| Tool names | crucible_run, crucible_record, crucible_task, crucible_transition, crucible_verify, crucible_report | hardproof_run, hardproof_record, hardproof_task, hardproof_transition, hardproof_verify, hardproof_report | tools/schemas.py, tools/handlers.py, plugin.yaml, all test files (~100 refs) | Tool name change | None (new install) | Tool registration verified | PENDING |
| Toolset name | crucible | hardproof | tools/handlers.py (register_tools) | Toolset name | None | Toolset registered correctly | PENDING |
| Configuration namespace | crucible | hardproof | config.py (class names), constants.py | Class name change | Existing .crucible/config.yaml continues working | Config load works | PENDING |
| State directory | .crucible/ | .hardproof/ | paths.py, config.py, commands/shared.py, README, docs, tests (16 files) | New runs use .hardproof/ | Migration command required | New runs use .hardproof/ | PENDING |
| Database file | .crucible/state/crucible.db | .hardproof/state/hardproof.db | paths.py, storage/*.py | Database path | Migration copies old DB | New DB at correct path | PENDING |
| Environment variable prefix | CRUCIBLE_ | HARDPROOF_ | config.py (env expansion), tests | Env var prefix | None (new install) | HARDPROOF_ env vars work | PENDING |
| Log prefix | [crucible] | [hardproof] | handlers.py (logger messages) | Log format | None | Log output says [hardproof] | PENDING |
| Report heading | # Crucible Completion Report | # Hardproof Completion Report | services/reports.py line 203 | Report format | None | Report heading changed | PENDING |
| Terminal banners | "CRUCIBLE RUN ACTIVE" etc. | "HARDPROOF RUN ACTIVE" etc. | hooks/context.py | Display text | None | Context banner says HARDPROOF | PENDING |
| Skill namespace | crucible:orchestrate, etc. | hardproof:orchestrate, etc. | plugin.py, hooks/context.py, skill SKILL.md files (9 skills) | Skill namespace | None | `skill_view("hardproof:orchestrate")` works | PENDING |
| Skill descriptions | "Crucible run" | "Hardproof run" | plugin.py (SKILL_DESCRIPTIONS) | Description text | None | Skill descriptions updated | PENDING |
| GitHub repository | asimons81/crucible-agent | asimons81/hardproof | README, CI badges, CONTRIBUTING, SECURITY, SUPPORT, docs, workflows | Repo URL | User updates clone URL | Badge links resolve | PENDING |
| CI workflow name | CI (ci.yml) | CI (unchanged) | .github/workflows/ci.yml | Workflow names | None | CI passes | PENDING |
| Release workflow | release.yml | release.yml (unchanged) | .github/workflows/release.yml | Release automation | None | Release builds | PENDING |
| SBOM metadata | name: crucible-agent | name: hardproof | scripts/build_sbom.py | SBOM metadata | None | SBOM generated correctly | PENDING |
| Python wheel filename | crucible_agent-0.1.0-py3-none-any.whl | hardproof-0.1.0-py3-none-any.whl | CI smoke test references | Wheel name | None | Build produces correct name | PENDING |
| Changelog title | Crucible Agent | Hardproof | CHANGELOG.md line 3 | Doc text | None | Title says Hardproof | PENDING |
| ROADMAP title | Crucible ships by... | Hardproof ships by... | ROADMAP.md line 3 | Doc text | None | Title says Hardproof | PENDING |
| ADR titles | (various Crucible references) | (Hardproof equivalents) | docs/adr/*.md (6 files) | Doc text | None | ADR references updated | PENDING |
| Codex docs | Crucible references throughout | Hardproof equivalents | docs/codex/*.md (~12 files) | Doc text | None | Codex docs updated | PENDING |
| Issue templates | Crucible references | Hardproof equivalents | .github/ISSUE_TEMPLATE/*.yml | Template text | None | Templates updated | PENDING |
| PR template | (any Crucible references) | Hardproof equivalents | .github/pull_request_template.md | Template text | None | PR template updated | PENDING |
| CODEOWNERS | (any Crucible references) | Hardproof equivalents | .github/CODEOWNERS | Owner references | None | CODEOWNERS updated | PENDING |
| Migration SQL files | crucible_agent.migrations path | hardproof.migrations path | storage/migrations.py | Import path | None | Migration loads correct SQL | PENDING |
| Package data includes | crucible_agent = [...] | hardproof = [...] | pyproject.toml [tool.setuptools.package-data] | Package data | None | Skills/templates included in wheel | PENDING |
| License NOTICE | Crucible Agent contributors | Hardproof contributors | NOTICE | Attribution text | None | NOTICE updated | PENDING |
| Image filenames/alt text | (any Crucible references) | Hardproof equivalents | docs/, README | Image metadata | None | Images updated | PENDING |
| Badge alt text | Crucible Agent CI | Hardproof CI | README.md | Badge alt text | None | Badge alt text updated | PENDING |
| pip-audit reference | crucible-agent | hardproof | CI workflow (pip-audit) | Audit target | None | pip-audit passes | PENDING |

## State Directory Migration Details

| Aspect | Detail |
|--------|--------|
| Old directory | .crucible/ |
| New directory | .hardproof/ |
| Database | .crucible/state/crucible.db → .hardproof/state/hardproof.db |
| Active run pointer | .crucible/state/active-run → .hardproof/state/active-run |
| Config | .crucible/config.yaml → .hardproof/config.yaml |
| Runs directory | .crucible/runs/ → .hardproof/runs/ |
| Auto-delete | NEVER |
| Silent merge | NEVER |
| Detection | Check for .crucible/ when .hardproof/ absent |
| Migration command | hermes hardproof migrate-state |
| Backup | Create .crucible.backup/ before migration |
| Conflict | When both exist, report conflict and do nothing |
| Rollback | Print rollback instruction after migration |
| Report | Write migration report to .hardproof/migration-report.json |
| Integrity | Verify SQLite integrity after copy |
| Timestamps | Preserve file modification times where practical |

## Historical References (Allowed Retention Categories)

Old-name references may remain only in:
1. State migration code and docs
2. Historical changelog entries (v0.1.0 section)
3. Historical commit documentation
4. Clean-room inspiration documentation (INSPIRATION.md)
5. ADR explaining the rename
6. Tests verifying old-name removal
7. Source comments explaining compatibility

All other matches are rename failures. Every retained match must be documented in the residual audit.

## Verification Gates

- [ ] All 310 existing tests pass after rename
- [ ] New rename-specific tests added (target: >310 total)
- [ ] Ruff passes on both branches
- [ ] mypy strict passes on both branches
- [ ] Wheel builds and installs
- [ ] Sdist builds and installs
- [ ] Package imports as `hardproof`
- [ ] Hermes plugin discovers as `hardproof`
- [ ] `/hardproof` slash command registered
- [ ] `hermes hardproof` CLI registered
- [ ] Tools registered as hardproof_*
- [ ] Skills registered under hardproof:*
- [ ] New runs use .hardproof/
- [ ] Old .crucible/ detection works
- [ ] Migration command functions
- [ ] No accidental crucible import works
- [ ] Old plugin key not registered
- [ ] Old slash command not registered
- [ ] Old CLI command not registered
- [ ] No old branding in built artifacts
- [ ] Secret scan clean
- [ ] No telemetry
- [ ] No private Hermes API use
