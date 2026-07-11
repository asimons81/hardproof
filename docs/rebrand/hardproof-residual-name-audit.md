# Hardproof Residual Name Audit

Every retained match of the old working name "Crucible" must be listed here.
An unexplained old-name match is a failed rename.

Generated: 2026-07-11 | Branch: chore/hardproof-rename

## Retained References

| Exact Match | File | Context | Reason Retained | Publicly Visible | Approved Category |
|-------------|------|---------|-----------------|------------------|-------------------|
| Crucible | docs/rebrand/hardproof-rename-manifest.md | Old value column in rename surface table | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| crucible-agent | docs/rebrand/hardproof-rename-manifest.md | Old dist name in manifest | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| crucible_agent | docs/rebrand/hardproof-rename-manifest.md | Old import package in manifest | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| CRUCIBLE | docs/rebrand/hardproof-rename-manifest.md | Old wordmark in manifest | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| .crucible | docs/rebrand/hardproof-rename-manifest.md | Old state dir in manifest | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| CRUCIBLE_ | docs/rebrand/hardproof-rename-manifest.md | Old env prefix in manifest | Rename manifest documents old→new mapping | Yes (dev docs) | Migration documentation |
| Crucible | docs/adr/0007-public-rebrand-hardproof.md | ADR context: "project previously operated under the working name 'Crucible'" | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| crucible-agent | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| crucible_agent | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| CRUCIBLE | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| /crucible | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| hermes crucible | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| .crucible/ | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| CRUCIBLE_ | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| crucible_ | docs/adr/0007-public-rebrand-hardproof.md | ADR old-value column | ADR explaining the rename | Yes (public ADR) | ADR explaining rename |
| Crucible | tests/contract/test_hardproof_rename.py | Test class and assertions: "old Crucible identity must not be accidentally usable" | Tests verifying old-name removal | No (test code) | Tests verifying old-name removal |
| crucible | tests/contract/test_hardproof_rename.py | Test assertions like "crucible" not in X | Tests verifying old-name removal | No (test code) | Tests verifying old-name removal |
| .crucible | tests/contract/test_hardproof_rename.py | State migration test fixtures | Tests verifying migration behavior | No (test code) | Migration tests |
| crucible_agent | tests/contract/test_hardproof_rename.py | import crucible_agent assertion | Tests proving old import fails | No (test code) | Tests verifying old-name removal |
| CRUCIBLE RUN ACTIVE | tests/contract/test_hardproof_rename.py | Assertion checking old banner is absent | Tests verifying old-name removal | No (test code) | Tests verifying old-name removal |
| Crucible Completion Report | tests/contract/test_hardproof_rename.py | Assertion checking old heading is absent | Tests verifying old-name removal | No (test code) | Tests verifying old-name removal |
| crucible-agent | tests/contract/test_hardproof_rename.py | Assertion checking old name absent from metadata | Tests verifying old-name removal | No (test code) | Tests verifying old-name removal |
| .crucible | hardproof/commands/shared.py | migrate-state method: old_dir reference | Migration implementation | No (source code) | Migration code |
| crucible | hardproof/commands/shared.py | migrate-state method: backup dir "hardproof.backup" | Migration implementation | No (source code) | Migration code |

## Verification Summary

- Source files outside the allowed categories: **0**
- Unexplained matches: **0**
- Rename completeness: **PASS**

## Allowed Categories Reference

1. State migration code and docs
2. Historical changelog entries
3. Historical commit or release documentation
4. Clean-room inspiration documentation
5. ADR explaining the rename
6. Tests verifying old-name removal
7. Source comments explaining compatibility
