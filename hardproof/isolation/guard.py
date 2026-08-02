"""Workspace isolation guard."""
from pathlib import Path

class IsolationError(Exception):
    pass

def enforce_workspace_isolation(workspace: Path, cross_profile: bool = False) -> None:
    """Block cross-profile writes unless flag set. 1-2 line comment."""
    if not cross_profile and "profiles" in str(workspace):
        raise IsolationError("cross-profile write blocked")
