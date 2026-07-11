from __future__ import annotations

import inspect

import pytest


def test_installed_hermes_plugin_context_public_contract() -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    context = plugins.PluginContext
    expected = {
        "register_tool",
        "register_hook",
        "register_skill",
        "register_command",
        "register_cli_command",
        "dispatch_tool",
    }
    assert expected <= set(vars(context))
    assert "toolset" in inspect.signature(context.register_tool).parameters
    assert "path" in inspect.signature(context.register_skill).parameters
    assert "args" in inspect.signature(context.dispatch_tool).parameters


def test_installed_hermes_hook_contracts_are_declared() -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    for hook in (
        "pre_llm_call",
        "pre_tool_call",
        "post_tool_call",
        "pre_verify",
        "on_session_start",
        "on_session_finalize",
        "on_session_reset",
    ):
        assert hook in plugins.VALID_HOOKS
