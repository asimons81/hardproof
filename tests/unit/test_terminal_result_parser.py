import json

from crucible_agent.services.evidence import parse_terminal_result


def test_parses_known_hermes_terminal_forms() -> None:
    assert parse_terminal_result('{"output":"ok","exit_code":0}').exit_code == 0
    assert parse_terminal_result({"output": "bad", "returncode": 3}).exit_code == 3
    nested = json.dumps({"result": {"stdout": "ok", "exitCode": 0}})
    assert parse_terminal_result(nested).exit_code == 0


def test_unknown_or_malformed_shape_is_indeterminate() -> None:
    assert parse_terminal_result("not-json").exit_code is None
    assert parse_terminal_result({"output": "success"}).exit_code is None
    assert parse_terminal_result(None).exit_code is None
