"""Validate Hardproof release-signing policy in the release workflow.

Runs as a deterministic CI check. Does not require actual signing keys.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_CHECKS = {
    "release_workflow_exists": False,
    "tags_trigger_only": False,
    "environment_pypi": False,
    "id_token_write": False,
    "ssh_signing_configured": False,
    "tag_verification_present": False,
    "allowed_signers_exists": False,
    "allowed_signers_format_valid": False,
    "no_static_pypi_token": False,
    "no_v02_trigger_paths": False,
}


def validate() -> bool:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "release.yml"
    signers_path = REPO_ROOT / ".github" / "release-signers"

    # 1. Workflow exists
    if not workflow_path.is_file():
        print("FAIL: .github/workflows/release.yml not found")
        return False
    REQUIRED_CHECKS["release_workflow_exists"] = True

    workflow = workflow_path.read_text()

    # 2. Triggers only on v* tags
    has_tag_trigger = bool(re.search(r'tags:\s*\["v\*"\]', workflow))
    if not has_tag_trigger:
        print("FAIL: release.yml must trigger on tags: ['v*']")
        return False
    REQUIRED_CHECKS["tags_trigger_only"] = True

    # 3. Has environment: pypi
    if "environment: pypi" not in workflow:
        print("FAIL: release.yml must use environment: pypi")
        return False
    REQUIRED_CHECKS["environment_pypi"] = True

    # 4. Has id-token: write
    if "id-token: write" not in workflow:
        print("FAIL: release.yml must request id-token: write")
        return False
    REQUIRED_CHECKS["id_token_write"] = True

    # 5. SSH signing configured before git tag -v
    if "gpg.format ssh" not in workflow:
        print("FAIL: release.yml must configure gpg.format ssh")
        return False
    if "gpg.ssh.allowedSignersFile" not in workflow:
        print("FAIL: release.yml must configure gpg.ssh.allowedSignersFile")
        return False
    REQUIRED_CHECKS["ssh_signing_configured"] = True

    # 6. git tag -v is called
    if 'git tag -v "${GITHUB_REF_NAME}"' not in workflow:
        print("FAIL: release.yml must call git tag -v")
        return False
    REQUIRED_CHECKS["tag_verification_present"] = True

    # 7. Allowed-signers file exists
    if not signers_path.is_file():
        print("FAIL: .github/release-signers not found")
        return False
    REQUIRED_CHECKS["allowed_signers_exists"] = True

    # 8. Allowed-signers format: email key-type key-data
    signers_content = signers_path.read_text().strip()
    if not signers_content:
        print("FAIL: .github/release-signers is empty")
        return False
    for line in signers_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            print(f"FAIL: invalid allowed-signers line: {line}")
            return False
        if "@" not in parts[0]:
            print(f"FAIL: first field must be email: {line}")
            return False
    REQUIRED_CHECKS["allowed_signers_format_valid"] = True

    # 9. No PyPI token secret referenced
    if re.search(r'(PYPI_TOKEN|PYPI_PASSWORD|TWINE_PASSWORD)', workflow):
        print("FAIL: release.yml must not reference a static PyPI token")
        return False
    REQUIRED_CHECKS["no_static_pypi_token"] = True

    # 10. No v0.2.0 trigger paths
    if "v0.2" in workflow or "gatehouse" in workflow.lower():
        print("FAIL: release.yml must not reference v0.2.0")
        return False
    REQUIRED_CHECKS["no_v02_trigger_paths"] = True

    print("All release-signing policy checks passed:")
    for check, status in REQUIRED_CHECKS.items():
        print(f"  {'PASS' if status else 'FAIL'}: {check}")

    return True


if __name__ == "__main__":
    ok = validate()
    raise SystemExit(0 if ok else 1)
