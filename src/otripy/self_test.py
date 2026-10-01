"""`otripy --self-test [REPORT_FILE]`: smoke test of an installed or packaged build.

Packaged (frozen) builds typically break by missing a data file, a library or
package metadata that a pip install has. This runs the parts of Otripy that
depend on them, headless, and reports each check. The release workflow runs it
on every freshly built bundle.

The report goes to stdout and, when given, to REPORT_FILE.
"""
import os
import sys
import traceback
from importlib import metadata, resources

CHECKS = []


def check(function):
    CHECKS.append(function)
    return function


@check
def resource_files():
    """Icons are package data, not code: frozen builds must collect them."""
    package = resources.files("otripy.resources")
    for name in [f"icon-{size}.png" for size in (16, 32, 64, 128, 256, 512)]:
        assert (package / name).is_file(), f"missing {name}"
    assert (package / "icons" / "location-dot.svg").is_file(), "missing marker icons"


@check
def journey_round_trip():
    from otripy.journey import Journey
    from otripy.location import Location

    journey = Journey([Location(48.8584, 2.2945, {"markdown": "# Tour Eiffel", "images": {}}, marker="star")])
    again = Journey.from_json_str(journey.to_json_str())
    assert [loc.to_dict() for loc in again] == [loc.to_dict() for loc in journey]


@check
def map_page_generation():
    """folium renders the map page from jinja2 templates shipped as package data."""
    from otripy.location import Location
    from otripy.map_view import build_map_html

    html = build_map_html([Location(48.8584, 2.2945, {"markdown": "# Tour Eiffel"})])
    assert "L.AwesomeMarkers.icon" in html


@check
def translations():
    """Otripy's compiled translations and Qt's own are data files too."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    otripy = QTranslator()
    with resources.as_file(resources.files("otripy") / "i18n") as directory:
        assert otripy.load(QLocale("fr"), "otripy", "_", str(directory)), "missing otripy_fr.qm"
    assert otripy.translate("MapApp", "Quit") == "Quitter"
    qt = QTranslator()
    assert qt.load(QLocale("fr"), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)), \
        "missing Qt translations (qtbase_fr.qm)"


@check
def keyring_backends():
    """keyring finds its backends through package metadata entry points."""
    assert metadata.entry_points(group="keyring.backends"), "no keyring backend entry points"


@check
def nextcloud_client():
    import nc_py_api
    assert nc_py_api.Nextcloud


@check
def main_window_and_web_engine():
    """Build the main window and check the map page loads and runs JavaScript.

    This needs the QtWebEngineProcess helper and its resources to be bundled.
    """
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from otripy.main import MapApp

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MapApp()
    window.dirty = False  # never ask about unsaved changes
    results = {}
    loop = QEventLoop()

    def loaded(ok):
        results["loaded"] = ok
        window.map_page.runJavaScript("6 * 7", 0, evaluated)

    def evaluated(value):
        results["javascript"] = value
        loop.quit()

    window.map_page.loadFinished.connect(loaded)
    window.update_map()
    QTimer.singleShot(60_000, loop.quit)
    loop.exec()
    window.close()
    app.processEvents()
    assert results.get("loaded"), f"map page did not load: {results}"
    assert results.get("javascript") == 42, f"JavaScript did not run: {results}"


def run(report_file=None) -> int:
    """Run all checks, report them, and return the process exit code."""
    # Never show a window
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from otripy import __version__

    lines = [f"Otripy {__version__} self-test, Python {sys.version.split()[0]}, "
             f"{'frozen' if getattr(sys, 'frozen', False) else 'not frozen'}"]
    failures = 0
    for function in CHECKS:
        try:
            function()
            lines.append(f"OK   {function.__name__}")
        except Exception:
            failures += 1
            lines.append(f"FAIL {function.__name__}\n{traceback.format_exc()}")
    lines.append("All checks passed" if not failures else f"{failures} check(s) failed")
    report = "\n".join(lines) + "\n"
    print(report, end="")
    if report_file:
        with open(report_file, "w", encoding="utf-8") as file:
            file.write(report)
    return 1 if failures else 0
