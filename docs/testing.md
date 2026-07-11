# Testing Hardproof

Hardproof tests observable protocol behavior and refusal paths. The suite is divided into unit, integration, contract, end-to-end, migration, policy, evidence, and package-install checks.

## Local checks

Run the full suite and static gates:

```bash
python -m pytest
python -m ruff check hardproof tests scripts
python -m mypy hardproof
```

Build and inspect distributions:

```bash
python -m build
python -m twine check dist/*
python scripts/smoke_install.py dist/hardproof-0.1.0-py3-none-any.whl
```

The clean-wheel smoke test creates a temporary virtual environment, installs normal dependencies, resolves the `hermes_agent.plugins` entry point, imports the package, and then deletes the environment.

## Evidence tests

Evidence tests use temporary Git repositories and real Git commands. They cover explicit pass, failure, timeout, malformed terminal output, concurrent workspace change, tracked and untracked staleness, secret redaction, bounded output, and profile-required check counts.

## Optional Hermes contract smoke

When Hermes Agent is installed, the suite inspects its public `PluginContext` without starting a model session or requiring paid API access. Live gateway and messaging-surface tests remain separate release evidence because they depend on local runtime availability.
