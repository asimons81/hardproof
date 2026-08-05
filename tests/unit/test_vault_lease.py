"""Unit tests for the Hermes Vault credential lease client."""
from __future__ import annotations

import os

import pytest

from hardproof.vault.lease import VaultLease, fetch_lease


def test_vault_lease_holds_service_and_token() -> None:
    lease = VaultLease("github", "lease-1", "tok-123")
    assert lease.service == "github"
    assert lease.lease_id == "lease-1"
    assert lease.token == "tok-123"


def test_fetch_lease_returns_none_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert fetch_lease("github") is None


def test_fetch_lease_reads_service_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token-abc")
    lease = fetch_lease("github")
    assert lease is not None
    assert lease.service == "github"
    assert lease.lease_id == "local"
    assert lease.token == "env-token-abc"


def test_fetch_lease_env_name_is_upper_cased(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MYAPI_TOKEN", raising=False)
    assert fetch_lease("myapi") is None
    monkeypatch.setenv("MYAPI_TOKEN", "x")
    assert fetch_lease("myapi") is not None


def test_lease_token_roundtrip_preserves_value() -> None:
    lease = VaultLease("svc", "id", "secret-value")
    assert os.environ.get("NOPE") is None  # sanity: no env leakage
    assert lease.token == "secret-value"
