# Hermes Compatibility

Hardproof currently develops against the public plugin API in Hermes Agent 0.18.2. Run `python scripts/inspect_hermes_api.py` to produce a deterministic local capability report.

The core requires tool, hook, skill, slash-command, CLI-command, and tool-dispatch registration. Optional lifecycle integrations are reported separately. Hardproof never uses private Hermes attributes and does not modify Hermes Agent source.
