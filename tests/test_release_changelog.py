import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release_changelog.py"
spec = importlib.util.spec_from_file_location("release_changelog", SCRIPT)
release_changelog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_changelog)

CHANGELOG = """# Changelog

Intro.

## Unreleased

### Fixed

- A bug.

## 1.3.0 - 2026-10-01

### Added

- A feature.
"""


def test_unreleased_entries_go_under_the_new_version():
    assert release_changelog.release(CHANGELOG, "1.3.1", "2026-10-08") == """# Changelog

Intro.

## Unreleased

## 1.3.1 - 2026-10-08

### Fixed

- A bug.

## 1.3.0 - 2026-10-01

### Added

- A feature.
"""


def test_first_release_without_previous_section():
    text = "# Changelog\n\n## Unreleased\n\n- First.\n"
    assert release_changelog.release(text, "0.1.0", "2026-01-01") == \
        "# Changelog\n\n## Unreleased\n\n## 0.1.0 - 2026-01-01\n\n- First.\n\n"


@pytest.mark.parametrize("text, message", [
    ("# Changelog\n\n## Unreleased\n\n## 1.3.0 - 2026-10-01\n\n- A feature.\n", "empty"),
    ("# Changelog\n\n## 1.3.0 - 2026-10-01\n", "no '## Unreleased'"),
    (CHANGELOG.replace("## 1.3.0", "## 1.3.1"), "already has a section"),
])
def test_refuses_to_release(text, message):
    with pytest.raises(release_changelog.ChangelogError, match=message):
        release_changelog.release(text, "1.3.1", "2026-10-08")


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_hook_updates_and_stages_the_changelog(tmp_path):
    """Run the script as bumpver does, in a repository of its own."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / SCRIPT.name)
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org"]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(git + ["add", "."], cwd=tmp_path, check=True)
    subprocess.run(git + ["commit", "-qm", "init"], cwd=tmp_path, check=True)
    env = dict(os.environ, BUMPVER_OLD_VERSION="1.3.0", BUMPVER_NEW_VERSION="1.3.1")
    result = subprocess.run([sys.executable, str(tmp_path / "scripts" / SCRIPT.name)], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "## Unreleased\n\n## 1.3.1 - " in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=tmp_path, capture_output=True,
                            text=True, check=True).stdout.split()
    assert staged == ["CHANGELOG.md"]


def test_hook_needs_bumpver(monkeypatch, capsys):
    monkeypatch.delenv("BUMPVER_NEW_VERSION", raising=False)
    assert release_changelog.main() == 1
