import jsonschema

from hardproof.tools.schemas import TOOL_SCHEMAS


EXPECTED = {
    "hardproof_run", "hardproof_record", "hardproof_task",
    "hardproof_transition", "hardproof_verify", "hardproof_report",
}


def test_exact_six_tools_have_valid_json_schemas() -> None:
    assert set(TOOL_SCHEMAS) == EXPECTED
    for name, schema in TOOL_SCHEMAS.items():
        assert schema["name"] == name
        assert schema["description"]
        jsonschema.Draft7Validator.check_schema(schema["parameters"])
        assert schema["parameters"]["additionalProperties"] is False


def test_model_tools_have_no_human_approval_action() -> None:
    serialized = str(TOOL_SCHEMAS).lower()
    assert '"approve"' not in serialized
    assert "create_approval" not in serialized
    assert "waivers_create" not in serialized
    report_actions = TOOL_SCHEMAS["hardproof_report"]["parameters"]["properties"]["action"]["enum"]
    assert "policy_explain" in report_actions
    assert "risk_suggest" in report_actions
