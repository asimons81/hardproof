import pytest

from crucible_agent.compat import inspect_context


def test_real_hermes_public_context_surface_when_installed() -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    context = object.__new__(plugins.PluginContext)
    report = inspect_context(context)
    assert report.compatible
    assert report.hermes_version
