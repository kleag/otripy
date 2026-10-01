# Translating Otripy

Otripy is available in English and French. Translations of other languages are welcome, and so are corrections of the existing ones.

Otripy uses Qt's translation system. Each language has two files in [`src/otripy/i18n/`](https://github.com/kleag/otripy/tree/main/src/otripy/i18n):

* `otripy_<language>.ts`: the translation itself, an XML file listing each English text with its translation. This is the file you edit.
* `otripy_<language>.qm`: the compiled translation that Otripy loads. It is generated from the `.ts` file: never edit it.

`<language>` is a language code, such as `fr` for French or `pt_BR` for Brazilian Portuguese. Otripy shows the translation matching your system's language, and English when there is none.

Buttons and dialogs that come from Qt itself, such as *Yes*, *No* or *Cancel*, are translated by Qt, not by Otripy.

## Translating without a development setup

You only need the `.ts` file and a way to edit it:

1. Download the file of your language from [`src/otripy/i18n/`](https://github.com/kleag/otripy/tree/main/src/otripy/i18n), or ask for a new language in an [issue](https://github.com/kleag/otripy/issues).
2. Edit it with [Qt Linguist](https://doc.qt.io/qt-6/linguist-translators.html), Qt's translation tool, or with a text editor (see [the file format](#editing-a-ts-file) below).
3. Send it back in a pull request, or attach it to an issue: the maintainers compile and test it.

## Translating with a development setup

With the [development setup](contributing.md#development-setup), you can see your translation in Otripy as you work.

### Improving an existing translation

1. Open the translation in Qt Linguist, which comes with Otripy's development tools:

    ```sh
    uv run pyside6-linguist src/otripy/i18n/otripy_fr.ts
    ```

    Linguist shows each text in its context (the dialog or part of Otripy it belongs to), marks the texts still to translate, and warns about mistakes such as missing placeholders. Mark each text you translate as done (Ctrl+Enter).

2. Compile the translations and try them. The `OTRIPY_LANGUAGE` environment variable chooses the language, whatever your system's:

    ```sh
    uv run python scripts/translations.py compile
    OTRIPY_LANGUAGE=fr uv run otripy
    ```

    On Windows (PowerShell): `$env:OTRIPY_LANGUAGE="fr"; uv run otripy`.

3. Run the tests, which check that every text is translated and that placeholders are kept, then open a pull request with both the `.ts` and the `.qm` files:

    ```sh
    uv run pytest tests/test_translations.py
    ```

### Adding a language

```sh
uv run python scripts/translations.py add de     # here German
```

This creates `src/otripy/i18n/otripy_de.ts`, with every text to translate, and its `.qm` file. Translate it as above. Otripy picks it up automatically: there is no list of languages to update.

## Editing a `.ts` file

Each text is a `<message>`, in the `<context>` of the part of Otripy it belongs to:

```xml
<context>
    <name>MapApp</name>
    <message>
        <location filename="../main.py" line="+12"/>
        <source>Failed to load file: {error}</source>
        <translation>Impossible d'ouvrir le fichier : {error}</translation>
    </message>
</context>
```

Write the translation in `<translation>`, and remove its `type="unfinished"` attribute once done; leave the rest unchanged. Some rules apply to all languages:

* **Keep the placeholders** between braces, such as `{error}`, `{path}` or `{minutes:02d}`, with exactly the same names: Otripy replaces them with values, and fails if one is missing or misspelled. You can move them within the sentence.
* **Keep HTML tags and links** (`<a href="…">…</a>`, `<b>`): translate only the visible text between them. In the route attribution, the links are required by the services Otripy uses.
* **Keep `\n` line breaks and `…`** where they are, as they shape the message boxes and menus.
* **Follow your language's typography.** For instance, the French translation puts a non-breaking space before `:`, `?` and `!`.
* **Keep a single text for each source text in a context**, even if it appears in several places: the same translation is used everywhere.

## For developers: making texts translatable

Every text shown to users must be translatable. After adding or changing one, run `uv run python scripts/translations.py` to update the `.ts` files: the tests fail if a text is missing from them. New texts appear untranslated (in English) until translators handle them.

* In classes derived from Qt objects (windows, dialogs, widgets), wrap texts in `self.tr("…")`. The class name is the translation context.
* Elsewhere, use `QCoreApplication.translate("Context", "…")`.
* For texts defined before Otripy starts, such as module constants, mark them with `QT_TRANSLATE_NOOP("Context", "…")` and translate them where they are shown, with `QCoreApplication.translate("Context", text)`.
* Translation tools can only extract literal strings: never pass an f-string or a variable to `tr()`. Use named placeholders with `format`:

    ```python
    self.tr("Failed to load file: {error}").format(error=e)
    ```

* Give whole sentences, never fragments to assemble: word order differs between languages.
