import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QLocale

from otripy import routing
from otripy.translations import install_translators

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "src" / "otripy" / "i18n"
TS_FILES = sorted(I18N.glob("otripy_*.ts"))
PLACEHOLDER = re.compile(r"\{(\w+)[^}]*\}")


def tool(name):
    for candidate in (Path(sys.executable).parent / name, Path(sys.executable).parent / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return shutil.which(name) or pytest.skip(f"{name} is not available")


def messages(ts):
    root = ET.parse(ts).getroot()
    return {(ctx.findtext("name"), m.findtext("source")): m.find("translation")
            for ctx in root.iter("context") for m in ctx.iter("message")}


def test_there_is_a_french_translation():
    assert I18N / "otripy_fr.ts" in TS_FILES


@pytest.mark.parametrize("ts", TS_FILES, ids=lambda p: p.name)
def test_translation_files_list_every_string(ts, tmp_path):
    """Run scripts/translations.py after changing user-visible strings."""
    copy = tmp_path / ts.name
    shutil.copy(ts, copy)
    sources = sorted(str(p) for p in (ROOT / "src" / "otripy").glob("*.py"))
    subprocess.run([tool("pyside6-lupdate"), *sources, "-locations", "relative", "-no-obsolete",
                    "-ts", str(copy)], check=True, capture_output=True)
    assert set(messages(copy)) == set(messages(ts))


@pytest.mark.parametrize("ts", TS_FILES, ids=lambda p: p.name)
def test_translations_are_complete(ts):
    for (context, source), translation in messages(ts).items():
        assert translation.get("type") != "unfinished" and (translation.text or "").strip(), (context, source)
        # A missing or extra placeholder would break str.format at run time
        assert set(PLACEHOLDER.findall(translation.text)) == set(PLACEHOLDER.findall(source)), (context, source)


@pytest.mark.parametrize("ts", TS_FILES, ids=lambda p: p.name)
def test_compiled_translations_are_up_to_date(ts, tmp_path):
    """Run scripts/translations.py (or its compile command) after editing a .ts file."""
    compiled = tmp_path / ts.with_suffix(".qm").name
    subprocess.run([tool("pyside6-lrelease"), "-silent", str(ts), "-qm", str(compiled)], check=True)
    assert compiled.read_bytes() == ts.with_suffix(".qm").read_bytes()


@pytest.fixture
def french(qapp):
    translators = install_translators(qapp, QLocale("fr"))
    yield translators
    for translator in translators:
        qapp.removeTranslator(translator)


def test_french_interface(french, qtbot, monkeypatch):
    from otripy import main
    assert {t.filePath().rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for t in french} == {"qtbase_fr.qm", "otripy_fr.qm"}
    window = main.MapApp()
    qtbot.addWidget(window)
    monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
    assert [a.text() for a in window.menuBar().actions()] == ["Fichier", "Outils", "Paramètres"]
    assert window.del_btn.text() == "Supprimer"
    assert routing.mode_label("bike") == "Vélo"
    assert routing.format_duration(93_600) == "1 j 2 h 00"
    assert "corriger la carte" in routing.attribution_html()


def test_language_override(monkeypatch):
    from otripy.translations import ui_locale
    monkeypatch.setenv("OTRIPY_LANGUAGE", "fr")
    assert ui_locale().language() == QLocale.French
