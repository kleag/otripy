#!/usr/bin/env python3
"""bumpver pre-commit hook: turn the changelog's Unreleased section into the new version's.

    ## Unreleased             ## Unreleased
                        ->
    ### Fixed                 ## 1.3.1 - 2026-10-08
    - ...
                              ### Fixed
                              - ...

bumpver runs it after updating the version, before committing, with the versions
in BUMPVER_OLD_VERSION and BUMPVER_NEW_VERSION. It stages CHANGELOG.md, which
bumpver does not do for files it did not change itself. It refuses to release
when the Unreleased section is empty.
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
UNRELEASED = "## Unreleased\n"


class ChangelogError(Exception):
    pass


def release(text: str, version: str, date: str) -> str:
    """Return the changelog with its Unreleased entries filed under version."""
    start = text.find(UNRELEASED)
    if start == -1:
        raise ChangelogError("CHANGELOG.md has no '## Unreleased' section.")
    body_start = start + len(UNRELEASED)
    next_section = text.find("\n## ", body_start)
    body_end = next_section + 1 if next_section != -1 else len(text)
    entries = text[body_start:body_end].strip()
    if not entries:
        raise ChangelogError("The changelog's Unreleased section is empty: describe the changes of this release first.")
    if f"\n## {version} " in text or f"\n## {version}\n" in text:
        raise ChangelogError(f"CHANGELOG.md already has a section for {version}.")
    return f"{text[:body_start]}\n## {version} - {date}\n\n{entries}\n\n{text[body_end:]}"


def main() -> int:
    version = os.environ.get("BUMPVER_NEW_VERSION")
    if not version:
        print("Run by bumpver: BUMPVER_NEW_VERSION is not set.", file=sys.stderr)
        return 1
    try:
        CHANGELOG.write_text(release(CHANGELOG.read_text(encoding="utf-8"), version,
                                     datetime.date.today().isoformat()), encoding="utf-8")
    except ChangelogError as e:
        print(e, file=sys.stderr)
        print("Release stopped. Undo bumpver's version changes with: "
              "git checkout -- pyproject.toml src/otripy/__init__.py", file=sys.stderr)
        return 1
    subprocess.run(["git", "add", str(CHANGELOG)], check=True)
    print(f"CHANGELOG.md: Unreleased entries filed under {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
