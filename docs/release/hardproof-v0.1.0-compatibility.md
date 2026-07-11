# Hardproof v0.1.0 Compatibility Report

## Hermes Agent

| Version | Status | Notes |
|---------|--------|-------|
| 0.18.2 | Compatible | Primary test target (Windows) |
| 0.18.x | Expected compatible | Public API surface stable |

## Operating Systems

| OS | Status | Notes |
|----|--------|-------|
| Windows 10 (native) | Tested | 217 tests passing |
| Ubuntu (latest) | CI-enforced | GitHub Actions matrix |
| macOS (latest) | CI-enforced | GitHub Actions matrix |

## Python Versions

| Version | Status |
|---------|--------|
| 3.11 | Tested (217 passing) |
| 3.12 | CI-enforced |

## Public API Surface

Hardproof uses only documented public Hermes Agent APIs:

- Plugin registration (entry_points)
- Slash command registration
- CLI command registration
- Tool registration with schemas
- Hook registration (pre_llm_call, pre_tool_call, post_tool_call, pre_verify, session lifecycle)
- Skill registration
- Context injection

No private Hermes attributes are accessed. Verified by:
- `scripts/inspect_hermes_api.py` contract test
- `tests/contract/test_hermes_api_contract.py` assertions
- `tests/contract/test_local_only_runtime.py` local-only verification

## Plugin Compatibility

- Plugin remains opt-in (no auto-enablement)
- No global instruction modification
- Skills installed under hardproof:* namespace
- Compatible with other Hermes plugins
