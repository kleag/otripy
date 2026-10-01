"""Update Otripy's translation files.

    uv run python scripts/translations.py           # refresh every .ts from the sources, then compile the .qm
    uv run python scripts/translations.py add de    # start a new language (here German)
    uv run python scripts/translations.py compile   # only compile the .ts into .qm

Translators edit src/otripy/i18n/otripy_<language>.ts, with Qt Linguist
(uv run pyside6-linguist) or any text editor. See docs/translating.md.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted((ROOT / "src" / "otripy").glob("*.py"))
I18N = ROOT / "src" / "otripy" / "i18n"


def tool(name: str) -> str:
    """Find a PySide6 tool next to the running Python, or on the PATH."""
    candidates = [Path(sys.executable).parent / name, Path(sys.executable).parent / f"{name}.exe"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if not found:
        sys.exit(f"{name} not found: run this script with the project's environment (uv run python ...)")
    return found


def update(ts: Path) -> None:
    language = ts.stem.split("_", 1)[1]
    subprocess.run([tool("pyside6-lupdate"), *map(str, SOURCES), "-locations", "relative", "-no-obsolete",
                    "-source-language", "en", "-target-language", language, "-ts", str(ts)], check=True)


def compile_all() -> None:
    for ts in sorted(I18N.glob("otripy_*.ts")):
        subprocess.run([tool("pyside6-lrelease"), "-silent", str(ts), "-qm", str(ts.with_suffix(".qm"))], check=True)
        print(f"Compiled {ts.with_suffix('.qm').relative_to(ROOT)}")


def main(args: list) -> None:
    if args[:1] == ["add"] and len(args) == 2:
        ts = I18N / f"otripy_{args[1]}.ts"
        if ts.exists():
            sys.exit(f"{ts.relative_to(ROOT)} already exists")
        update(ts)
    elif args == ["compile"]:
        pass
    elif not args:
        for ts in sorted(I18N.glob("otripy_*.ts")):
            update(ts)
    else:
        sys.exit(__doc__)
    compile_all()


if __name__ == "__main__":
    main(sys.argv[1:])
