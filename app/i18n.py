"""Compiling the gettext catalogues (#344).

`app/translations/<lang>/LC_MESSAGES/messages.po` is the tracked source. The
`messages.mo` beside it is a build artefact and is no longer tracked: git
cannot merge a compiled catalogue, so any translation pull request that
touched one another branch had also touched conflicted unresolvably, and a
tracked binary can quietly drift from the `.po` the app is supposed to be
showing.

The binaries are produced from the `.po` files instead — at image build time
(`pybabel compile -d app/translations` in the Dockerfile), when the test suite
starts, and here on startup as a safety net for anyone running from a bare
checkout. Compilation only happens when a catalogue is missing or older than
its source, so a warm checkout pays nothing but a handful of stat calls.

`compile_catalogue()` writes byte-for-byte what `pybabel compile` writes: both
go through Babel's own reader and writer, and fuzzy entries are skipped by
both. `tests/test_i18n_issue_344.py` pins that equivalence.
"""
import logging
import os
import tempfile

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations')

logger = logging.getLogger(__name__)


def catalogues():
    """Every shipped catalogue as (language code, .po path, .mo path)."""
    found = []
    for code in sorted(os.listdir(TRANSLATIONS_DIR)):
        po_path = os.path.join(TRANSLATIONS_DIR, code, 'LC_MESSAGES', 'messages.po')
        if os.path.isfile(po_path):
            found.append((code, po_path, po_path[:-3] + '.mo'))
    return found


def is_stale(po_path, mo_path):
    """True when the compiled catalogue is missing or older than its source."""
    if not os.path.isfile(mo_path):
        return True
    return os.path.getmtime(mo_path) < os.path.getmtime(po_path)


def compile_catalogue(code, po_path, mo_path):
    """Compile one catalogue, replacing the .mo atomically.

    Two gunicorn workers can reach this at the same time on a cold start, and
    a torn .mo would break every translated string rather than one of them, so
    the new catalogue is written to a temporary file in the same directory and
    moved into place in a single step.
    """
    with open(po_path, 'rb') as source:
        catalog = read_po(source, locale=code)

    directory = os.path.dirname(mo_path)
    handle, temp_path = tempfile.mkstemp(dir=directory, prefix='messages.', suffix='.mo')
    try:
        with os.fdopen(handle, 'wb') as target:
            write_mo(target, catalog, use_fuzzy=False)
        os.replace(temp_path, mo_path)
    except BaseException:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def compile_catalogues(force=False):
    """Compile the stale catalogues (all of them when *force*).

    Returns the language codes that were compiled.
    """
    compiled = []
    for code, po_path, mo_path in catalogues():
        if force or is_stale(po_path, mo_path):
            compile_catalogue(code, po_path, mo_path)
            compiled.append(code)
    return compiled


def ensure_catalogues_compiled():
    """Compile anything stale, tolerating a read-only or missing tree.

    A deployment that cannot write to the application directory keeps whatever
    catalogues the image was built with; it should say so in the log rather
    than refuse to start.
    """
    try:
        compiled = compile_catalogues()
    except OSError as exc:
        logger.warning(
            'Could not compile the translation catalogues (%s). The interface '
            'may show untranslated or outdated text; run '
            '"pybabel compile -d app/translations" where the files are writable.',
            exc,
        )
        return []

    if compiled:
        logger.info('Compiled translation catalogues: %s', ', '.join(compiled))
    return compiled
