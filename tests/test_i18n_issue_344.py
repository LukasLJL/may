"""Compiled catalogues are build artefacts, not tracked files (#344).

Every `app/translations/<lang>/LC_MESSAGES/messages.mo` used to be committed.
Git cannot merge a compiled catalogue, so a translation pull request that
touched one the target branch had also touched conflicted unresolvably (#339
against #340), and a committed binary could quietly drift from the `.po` the
application is supposed to be showing.

These tests pin the replacement: the binaries are ignored and untracked, they
are produced from the `.po` sources, and what is produced is byte-for-byte
what `pybabel compile` produces.
"""
import logging
import os
import shutil
import subprocess
import sys

import pytest
from flask_babel import force_locale, gettext

from app import LANGUAGES
from app.i18n import (
    catalogues,
    compile_catalogue,
    compile_catalogues,
    is_stale,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args):
    """Run git in the repository, or skip when that is not possible.

    A released tarball or an installed copy is not a checkout, and neither is
    a container built from one, so these assertions are about the repository
    rather than about the code under test.
    """
    if shutil.which('git') is None:
        pytest.skip('git is not available')
    inside = subprocess.run(
        ['git', 'rev-parse', '--is-inside-work-tree'],
        cwd=BASE_DIR, capture_output=True, text=True,
    )
    if inside.returncode != 0 or inside.stdout.strip() != 'true':
        pytest.skip('not a git checkout')
    return subprocess.run(
        ['git', *args], cwd=BASE_DIR, capture_output=True, text=True,
    )


def _read(path):
    with open(path, 'rb') as handle:
        return handle.read()


class TestCataloguesAreNotTracked:
    def test_no_compiled_catalogue_is_tracked(self):
        # The whole point: a .po-only pull request cannot collide with a
        # binary that nobody can merge.
        tracked = _git('ls-files', 'app/translations').stdout.split()
        binaries = [path for path in tracked if path.endswith('.mo')]
        assert binaries == [], (
            f"compiled catalogues are tracked again: {binaries}"
        )

    def test_sources_are_still_tracked(self):
        # Untracking the artefacts must not take the sources with them.
        tracked = _git('ls-files', 'app/translations').stdout.split()
        sources = {
            path.split('/')[2] for path in tracked
            if path.endswith('/LC_MESSAGES/messages.po')
        }
        expected = {code for code in LANGUAGES if code != 'en'}
        assert expected <= sources, (
            f"languages offered without a tracked .po: {sorted(expected - sources)}"
        )

    def test_every_compiled_catalogue_is_ignored(self):
        # Ignored as well as untracked, or the next `git add -A` puts them
        # straight back.
        paths = [
            os.path.relpath(mo_path, BASE_DIR) for _, _, mo_path in catalogues()
        ]
        result = _git('check-ignore', '--', *paths)
        ignored = set(result.stdout.split())
        assert set(paths) == ignored, (
            f"not covered by .gitignore: {sorted(set(paths) - ignored)}"
        )


class TestCataloguesAreBuilt:
    def test_all_nineteen_languages_have_a_source(self):
        codes = {code for code, _, _ in catalogues()}
        expected = {code for code in LANGUAGES if code != 'en'}
        assert codes == expected

    def test_compiling_produces_every_catalogue(self, tmp_path, monkeypatch):
        # A bare checkout has no .mo at all; compiling must yield one per
        # language rather than only the ones touched recently.
        for code, po_path, _ in catalogues():
            target = tmp_path / code / 'LC_MESSAGES'
            target.mkdir(parents=True)
            shutil.copy(po_path, target / 'messages.po')

        import app.i18n as i18n

        monkeypatch.setattr(i18n, 'TRANSLATIONS_DIR', str(tmp_path))
        compiled = compile_catalogues()

        assert compiled == sorted(code for code in LANGUAGES if code != 'en')
        for code in compiled:
            built = tmp_path / code / 'LC_MESSAGES' / 'messages.mo'
            assert built.is_file() and built.stat().st_size > 0

    def test_output_matches_pybabel_compile(self, tmp_path):
        # The Dockerfile and the documented developer step use the pybabel
        # command line; startup and the test suite use compile_catalogue().
        # If those two ever diverged, what ships would depend on which one ran.
        source_dir = tmp_path / 'cli'
        for code, po_path, _ in catalogues():
            target = source_dir / code / 'LC_MESSAGES'
            target.mkdir(parents=True)
            shutil.copy(po_path, target / 'messages.po')

        result = subprocess.run(
            [sys.executable, '-m', 'babel.messages.frontend',
             'compile', '-d', str(source_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        for code, po_path, _ in catalogues():
            ours = tmp_path / 'ours' / code / 'LC_MESSAGES'
            ours.mkdir(parents=True)
            compile_catalogue(code, po_path, str(ours / 'messages.mo'))
            assert _read(str(ours / 'messages.mo')) == _read(
                str(source_dir / code / 'LC_MESSAGES' / 'messages.mo')
            ), f"{code}: compiled catalogue differs from pybabel compile"

    def test_shipped_catalogues_match_their_sources(self):
        # Nothing on disk may lag its .po: the suite compiles at collection,
        # so a mismatch here means the build step failed to keep up.
        stale = [code for code, po, mo in catalogues() if is_stale(po, mo)]
        assert stale == [], f"compiled catalogues older than their source: {stale}"


class TestStaleness:
    def _catalogue(self, tmp_path, msgstr):
        target = tmp_path / 'xx' / 'LC_MESSAGES'
        target.mkdir(parents=True, exist_ok=True)
        (target / 'messages.po').write_text(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=utf-8\\n"\n'
            '\n'
            'msgid "Fuel"\n'
            f'msgstr "{msgstr}"\n',
            encoding='utf-8',
        )
        return target

    def test_edited_source_is_recompiled(self, tmp_path, monkeypatch):
        import app.i18n as i18n

        target = self._catalogue(tmp_path, 'first')
        monkeypatch.setattr(i18n, 'TRANSLATIONS_DIR', str(tmp_path))

        assert compile_catalogues() == ['xx']
        assert b'first' in _read(str(target / 'messages.mo'))

        # Nothing to do the second time round: an unchanged checkout should
        # not rewrite catalogues on every start.
        assert compile_catalogues() == []

        self._catalogue(tmp_path, 'second')
        os.utime(
            target / 'messages.po',
            (os.path.getmtime(target / 'messages.mo') + 10,) * 2,
        )
        assert compile_catalogues() == ['xx']
        assert b'second' in _read(str(target / 'messages.mo'))

    def test_write_is_atomic(self, tmp_path, monkeypatch):
        # A failed compile must leave the previous catalogue intact rather
        # than a half-written file every locale would then fail to load.
        import app.i18n as i18n

        target = self._catalogue(tmp_path, 'first')
        monkeypatch.setattr(i18n, 'TRANSLATIONS_DIR', str(tmp_path))
        compile_catalogues()
        good = _read(str(target / 'messages.mo'))

        def boom(*args, **kwargs):
            raise OSError('disk full')

        monkeypatch.setattr(i18n, 'write_mo', boom)
        with pytest.raises(OSError):
            compile_catalogues(force=True)

        assert _read(str(target / 'messages.mo')) == good
        leftovers = [
            name for name in os.listdir(target)
            if name not in {'messages.po', 'messages.mo'}
        ]
        assert leftovers == []

    def test_unwritable_tree_is_survivable(self, tmp_path, monkeypatch):
        # A read-only deployment keeps the catalogues baked into the image and
        # says so, rather than refusing to start.
        import app.i18n as i18n

        self._catalogue(tmp_path, 'first')
        monkeypatch.setattr(i18n, 'TRANSLATIONS_DIR', str(tmp_path))
        monkeypatch.setattr(
            i18n, 'compile_catalogue',
            lambda *args: (_ for _ in ()).throw(OSError('read-only file system')),
        )

        # A handler on the module logger rather than caplog, which does not
        # see this record once the rest of the suite has run.
        messages = []

        class Collector(logging.Handler):
            def emit(self, record):
                messages.append(record.getMessage())

        handler = Collector(level=logging.WARNING)
        previous_level = i18n.logger.level
        # Alembic's env.py calls fileConfig(), which disables every logger
        # that already exists — including this one — once any test has taken
        # the app through its migrations. Re-enable it for the duration.
        previously_disabled = i18n.logger.disabled
        i18n.logger.addHandler(handler)
        i18n.logger.setLevel(logging.WARNING)
        i18n.logger.disabled = False
        try:
            assert i18n.ensure_catalogues_compiled() == []
        finally:
            i18n.logger.removeHandler(handler)
            i18n.logger.setLevel(previous_level)
            i18n.logger.disabled = previously_disabled

        assert any('pybabel compile' in message for message in messages)
        assert any('read-only file system' in message for message in messages)


class TestGeneratedCataloguesTranslate:
    def test_generated_catalogue_is_used_at_runtime(self, app):
        # End to end: what the build produced is what the interface reads.
        with app.test_request_context():
            with force_locale('hu'):
                assert gettext('Fuel') != 'Fuel'
            with force_locale('de'):
                assert gettext('Fuel') != 'Fuel'


class TestBuildStepIsDocumented:
    def test_dockerfile_compiles_the_catalogues(self):
        with open(os.path.join(BASE_DIR, 'Dockerfile'), encoding='utf-8') as handle:
            dockerfile = handle.read()
        assert 'pybabel compile -d app/translations' in dockerfile

    @pytest.mark.parametrize('document', ['README.md', 'CLAUDE.md'])
    def test_setup_instructions_mention_the_compile_step(self, document):
        with open(os.path.join(BASE_DIR, document), encoding='utf-8') as handle:
            text = handle.read()
        assert 'pybabel compile -d app/translations' in text
