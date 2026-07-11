# Hardproof Hermes Agent Guide

This guide serves two audiences:

- **Audience A:** Hermes Agent working on Hardproof itself (developing the plugin)
- **Audience B:** A user asking Hermes Agent to install and use Hardproof in another repository

## Audience A: Working on Hardproof

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/asimons81/hardproof.git
   cd hardproof
   ```

2. Install development dependencies:
   ```bash
   python -m pip install -e ".[dev]"
   ```

3. Start Hermes from the repository root:
   ```bash
   hermes
   ```

4. Confirm `AGENTS.md` was loaded. Hermes prints a context-file banner on startup indicating which project context files were loaded.

### Development Cycle

1. Read the relevant `AGENTS.md` files before editing:
   - `AGENTS.md` — root project instructions
   - `hardproof/AGENTS.md` — package architecture
   - `tests/AGENTS.md` — testing rules
   - `docs/AGENTS.md` — documentation rules

2. Inspect the current status:
   ```bash
   cat STATUS.md
   cat ROADMAP.md
   gh pr list --repo asimons81/hardproof --state open
   ```

3. Run the development baseline before editing:
   ```bash
   python -m pytest -q
   python -m ruff check hardproof tests scripts
   ```

4. Respect the release and security invariants documented in `AGENTS.md`.

5. Use a focused branch:
   ```bash
   git checkout -b <type>/<description>  # e.g., fix/issue-42
   ```

6. Run focused tests during development, full suite before commit:
   ```bash
   python -m pytest tests/unit/test_my_module.py -q
   python -m pytest
   ```

7. Open a PR with evidence of what was tested, what changed, and what didn't change.

### Copy-Paste Prompt for Hermes

When you want Hermes to start working on the Hardproof repo, use this prompt:

```
Read AGENTS.md and every relevant nested AGENTS.md before editing. Inspect the current repository, open pull requests, architecture, tests, and status documents. Summarize the task boundary, affected invariants, and validation plan before making changes. Do not begin future roadmap work unless the user explicitly authorizes it.
```

## Audience B: Using Hardproof in Another Repository

### Step-by-Step: Install and Prepare

1. **Confirm the current directory is a Git repository:**
   ```bash
   git rev-parse --git-dir
   ```

2. **Confirm it has at least one commit:**
   ```bash
   git rev-parse HEAD
   ```

3. **Check installed Hermes version:**
   ```bash
   hermes --version
   ```

4. **Install Hardproof from PyPI:**
   ```bash
   pip install hardproof
   ```

5. **Enable the plugin:**
   ```bash
   hermes plugins enable hardproof
   ```

6. **Verify plugin discovery:**
   ```bash
   hermes hardproof doctor
   ```

7. **Run diagnostics:**
   ```bash
   hermes hardproof doctor
   hermes hardproof config explain
   hermes hardproof db status
   ```

8. **Recommend a profile.** The agent should examine the work and recommend Quick (typos, docs, one-line), Standard (feature work, refactors), or Critical (auth, data, production config). Stop and explain the recommendation before starting a run.

9. **Start a run:**
   ```bash
   hermes hardproof start standard "description of work"
   ```

10. **Check status:**
    ```bash
    hermes hardproof status
    ```

11. **When blocked, diagnose:**
    ```bash
    hermes hardproof doctor
    hermes hardproof config explain
    hermes hardproof db status
    hermes hardproof policy explain
    ```

12. **Complete only after fresh verification evidence:**
    ```bash
    hermes hardproof evidence          # Verify evidence exists
    hermes hardproof approve completion "reason"  # Human approval
    ```

### Copy-Paste Prompts for Hermes

#### Install and Prepare

Use this prompt to ask Hermes to set up Hardproof in a repository:

```
Inspect the current Git repository. Install and enable Hardproof from PyPI. Verify the version and plugin discovery. Run doctor and config diagnostics. Recommend a profile (Quick, Standard, or Critical) based on the repository and typical work. Explain the recommendation and stop before starting a run until I accept the profile.
```

#### Start a Feature

```
Start a Standard Hardproof run for: [describe the feature work]. Walk me through the stages and explain what approvals you will need from me.
```

#### Handle Sensitive Work

```
Start a Critical Hardproof run for: [describe auth/data/production work]. Explain the additional approvals, checks, and rollback material required. Do not proceed past each gate without my explicit approval.
```

#### Diagnose a Blocked Run

```
Inspect the current Hardproof run status, policy configuration, database state, approvals, waivers, and evidence freshness. Explain why the run is blocked and what I need to do to unblock it. Do not bypass gates.
```

#### Continue an Existing Run

```
Inspect the .hardproof/ directory for an existing Hardproof run state. Summarize the active run, its current stage, pending approvals, and next steps. Resume the run safely.
```

#### Uninstall

To remove the Hardproof Python package:

```bash
pip uninstall hardproof
```

This does not delete `.hardproof/` project state. To remove state, delete the directory manually:

```bash
rm -rf .hardproof/   # Linux/macOS
rm -r .hardproof\    # Windows
```

Hardproof state is local to each project repository. Uninstalling the package does not affect existing run data.
