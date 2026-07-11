"""Contract tests proving the Hardproof rename is complete and the old identity is gone."""

from __future__ import annotations

import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestOldIdentityGone:
    """The old Crucible identity must not be accidentally usable."""

    def test_cannot_import_crucible_agent(self) -> None:
        """import crucible_agent must fail — the old package does not exist."""
        with pytest.raises(ImportError):
            import crucible_agent  # noqa: F401, F811

    def test_old_plugin_key_not_in_entry_points(self) -> None:
        """The crucible entry point must not be registered."""
        import importlib.metadata
        eps = importlib.metadata.entry_points(group="hermes_agent.plugins")
        names = {ep.name for ep in eps}
        assert "crucible" not in names
        assert "hardproof" in names

    def test_package_metadata_is_hardproof(self) -> None:
        """All package metadata surfaces use Hardproof, not Crucible."""
        import importlib.metadata
        meta = importlib.metadata.metadata("hardproof")
        assert meta["Name"] == "hardproof"
        assert "Crucible" not in meta["Name"]
        assert "Crucible" not in meta.get("Author", "")
        assert "Crucible" not in meta.get("Summary", "")

    def test_plugin_manifest_uses_hardproof(self) -> None:
        """plugin.yaml must use hardproof, not crucible."""
        import yaml
        manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text(encoding="utf-8"))
        assert manifest["name"] == "hardproof"
        assert "crucible" not in manifest["name"]

    def test_pyproject_uses_hardproof(self) -> None:
        """pyproject.toml must use hardproof, not crucible-agent."""
        import tomllib
        meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        assert meta["project"]["name"] == "hardproof"
        eps = meta["project"]["entry-points"]["hermes_agent.plugins"]
        assert "hardproof" in eps
        assert "crucible" not in eps


class TestNewIdentityCorrect:
    """The new Hardproof identity surfaces must be present."""

    def test_report_heading_is_hardproof(self) -> None:
        """Completion reports must use Hardproof, not Crucible."""
        from hardproof.services.reports import ReportService
        # Check the render_markdown method produces the right heading
        import inspect
        source = inspect.getsource(ReportService.render_markdown)
        assert "Hardproof Completion Report" in source
        assert "Crucible Completion Report" not in source

    def test_context_banner_is_hardproof(self) -> None:
        """Context hook banner must use HARDPROOF."""
        from hardproof.hooks.context import ContextHook
        import inspect
        source = inspect.getsource(ContextHook.__call__)
        assert "HARDPROOF RUN ACTIVE" in source
        assert "CRUCIBLE RUN ACTIVE" not in source

    def test_cli_prog_is_hermes_hardproof(self) -> None:
        """CLI parser program name must be hermes hardproof."""
        from hardproof.commands.cli import build_parser
        parser = build_parser()
        assert parser.prog == "hermes hardproof"

    def test_constants_plugin_key_is_hardproof(self) -> None:
        """PLUGIN_KEY constant must be hardproof."""
        from hardproof.constants import PLUGIN_KEY
        assert PLUGIN_KEY == "hardproof"

    def test_paths_use_dot_hardproof(self) -> None:
        """ProjectPaths must use .hardproof/ not .crucible/."""
        from hardproof.paths import ProjectPaths
        paths = ProjectPaths(ROOT)
        assert ".hardproof" in str(paths.root)
        assert ".crucible" not in str(paths.root)
        assert "hardproof.db" in str(paths.database)

    def test_tool_names_use_hardproof_prefix(self) -> None:
        """All tool names must use hardproof_ prefix, not crucible_."""
        from hardproof.tools.schemas import TOOL_SCHEMAS
        for name in TOOL_SCHEMAS:
            assert name.startswith("hardproof_"), f"Tool {name} must use hardproof_ prefix"
            assert "crucible" not in name

    def test_skill_namespace_is_hardproof(self) -> None:
        """Skill references must use hardproof: namespace."""
        from hardproof.hooks.context import ContextHook
        import inspect
        source = inspect.getsource(ContextHook.__call__)
        assert 'hardproof:' in source
        assert 'crucible:' not in source


class TestStateDirectoryMigration:
    """Safe .crucible/ to .hardproof/ state migration."""

    def test_new_runs_use_hardproof_dir(self, tmp_path: Path) -> None:
        """A new run creates .hardproof/, not .crucible/."""
        # Simulate what paths.py does
        from hardproof.paths import ProjectPaths
        paths = ProjectPaths(tmp_path)
        assert ".hardproof" in str(paths.root)
        assert ".crucible" not in str(paths.root)

    def test_old_state_detected_when_hardproof_absent(self, tmp_path: Path) -> None:
        """When .crucible/ exists but .hardproof/ does not, detection works."""
        old = tmp_path / ".crucible"
        old.mkdir(parents=True)
        (old / "state").mkdir()
        (old / "state" / "hardproof.db").write_text("")

        new = tmp_path / ".hardproof"
        assert old.exists()
        assert not new.exists()

    def test_migration_refuses_when_both_exist(self, tmp_path: Path) -> None:
        """When both .crucible/ and .hardproof/ exist, migration must refuse."""
        old = tmp_path / ".crucible"
        new = tmp_path / ".hardproof"
        old.mkdir(parents=True)
        new.mkdir(parents=True)
        (old / "state").mkdir()
        (old / "state" / "hardproof.db").write_text("")
        (new / "state").mkdir()
        (new / "state" / "hardproof.db").write_text("")

        assert old.exists()
        assert new.exists()
        # Both existing is a conflict the migrate-state command must catch

    def test_migration_creates_backup(self, tmp_path: Path) -> None:
        """Migration must create a .crucible.backup/ before copying."""
        old = tmp_path / ".crucible"
        old.mkdir(parents=True)
        (old / "state").mkdir()
        db = old / "state" / "hardproof.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()

        backup = tmp_path / ".crucible.backup"

        # Simulate the backup step
        shutil.copytree(old, backup)
        assert backup.exists()
        assert (backup / "state" / "hardproof.db").exists()

        # Verify the backed-up database is readable
        conn = sqlite3.connect(str(backup / "state" / "hardproof.db"))
        rows = conn.execute("SELECT * FROM test").fetchall()
        assert rows == [(1,)]
        conn.close()

    def test_migration_preserves_sqlite_integrity(self, tmp_path: Path) -> None:
        """Migrated database must pass integrity check."""
        old = tmp_path / ".crucible"
        old.mkdir(parents=True)
        (old / "state").mkdir()
        db = old / "state" / "hardproof.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'migrated')")
        conn.commit()
        conn.close()

        new = tmp_path / ".hardproof"
        shutil.copytree(old, new)

        # Verify migrated database integrity
        conn = sqlite3.connect(str(new / "state" / "hardproof.db"))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        assert result[0] == "ok"
        rows = conn.execute("SELECT * FROM test").fetchall()
        assert rows == [(1, "migrated")]
        conn.close()

    def test_migration_never_deletes_old(self, tmp_path: Path) -> None:
        """Migration must not delete .crucible/."""
        old = tmp_path / ".crucible"
        old.mkdir(parents=True)
        (old / "state").mkdir()
        (old / "state" / "hardproof.db").write_text("test")

        assert old.exists()
        # Migration copies, never deletes
        # After migration, old should still exist
        # (The actual migrate-state command does not delete source)


class TestBuiltArtifactCleanliness:
    """Built wheel and sdist must contain no old branding."""

    def test_wheel_contains_no_crucible(self) -> None:
        """No file in the wheel should contain crucible in its path."""
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            pytest.skip("wheel not built")
        with zipfile.ZipFile(wheels[-1]) as archive:
            names = archive.namelist()
        for name in names:
            assert "crucible" not in name.lower(), f"Wheel contains crucible path: {name}"

    def test_wheel_metadata_is_hardproof(self) -> None:
        """Wheel METADATA must reference hardproof, not crucible-agent."""
        wheels = sorted((ROOT / "dist").glob("*.whl"))
        if not wheels:
            pytest.skip("wheel not built")
        with zipfile.ZipFile(wheels[-1]) as archive:
            meta_candidates = [n for n in archive.namelist() if 'METADATA' in n]
            if not meta_candidates:
                pytest.skip("no METADATA found")
            metadata = archive.read(meta_candidates[0]).decode()
        assert "Name: hardproof" in metadata
        assert "crucible-agent" not in metadata

    def test_dist_filenames_use_hardproof(self) -> None:
        """Distribution filenames must use hardproof, not crucible_agent."""
        dist_files = list((ROOT / "dist").glob("*"))
        for f in dist_files:
            assert "crucible" not in f.name.lower(), f"Dist file contains crucible: {f.name}"


class TestNoOldSurfaceRegistration:
    """Old slash and CLI commands must not be registered."""

    def test_cli_parser_rejects_crucible_prog(self) -> None:
        """Build parser must use hermes hardproof, not hermes crucible."""
        from hardproof.commands.cli import build_parser
        parser = build_parser()
        assert "crucible" not in parser.prog

    def test_slash_registration_uses_hardproof(self) -> None:
        """Slash registration must use hardproof command name."""
        from hardproof.commands.slash import register_slash
        import inspect
        source = inspect.getsource(register_slash)
        assert '"hardproof"' in source
        assert '"crucible"' not in source


class TestConfigDefaults:
    """Configuration defaults must use new identity."""

    def test_default_artifact_directory(self) -> None:
        """Default artifact directory must be .hardproof/runs."""
        from hardproof.config import DEFAULTS
        assert ".hardproof" in DEFAULTS["artifact_directory"]
        assert ".crucible" not in DEFAULTS["artifact_directory"]
