"""Unit tests for the workspace isolation guard and backend adapters."""
from __future__ import annotations

import pytest

from hardproof.isolation.adapters import BackendLaunch
from hardproof.isolation.guard import IsolationError, enforce_workspace_isolation


def test_guard_allows_ordinary_workspace(tmp_path) -> None:
    enforce_workspace_isolation(tmp_path / "work" / "run-1")  # must not raise


def test_guard_blocks_cross_profile_path(tmp_path) -> None:
    workspace = tmp_path / "profiles" / "researcher" / "run-1"
    with pytest.raises(IsolationError, match="cross-profile write blocked"):
        enforce_workspace_isolation(workspace)


def test_guard_flag_allows_cross_profile(tmp_path) -> None:
    workspace = tmp_path / "profiles" / "researcher" / "run-1"
    # Explicit cross_profile=True must allow the write path
    enforce_workspace_isolation(workspace, cross_profile=True)  # must not raise


def test_guard_isolation_error_is_exception() -> None:
    assert issubclass(IsolationError, Exception)


def test_backend_launch_fields() -> None:
    launch = BackendLaunch(handle="h-1", backend="docker", raw={"image": "python:3.11"})
    assert launch.handle == "h-1"
    assert launch.backend == "docker"
    assert launch.raw == {"image": "python:3.11"}
