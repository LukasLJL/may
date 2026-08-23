"""Tests for language selection — LANGUAGES vs the shipped catalogues (#300)."""
import os

from flask_babel import force_locale, gettext

from app import LANGUAGES

TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'translations',
)


def _catalogue_dirs():
    """Language codes that have a directory under app/translations/."""
    return sorted(
        name for name in os.listdir(TRANSLATIONS_DIR)
        if os.path.isdir(os.path.join(TRANSLATIONS_DIR, name))
    )


class TestLanguageCatalogues:
    def test_every_translation_dir_is_listed(self):
        # A merged translation that never reaches LANGUAGES is dead weight:
        # it cannot be picked in settings and Babel never negotiates it.
        missing = [code for code in _catalogue_dirs() if code not in LANGUAGES]
        assert missing == [], (
            f"translation directories not listed in LANGUAGES: {missing}"
        )

    def test_every_language_has_a_catalogue(self):
        # The opposite mismatch: a code offered in the picker with no
        # catalogue behind it falls back to English without saying so.
        # 'en' is the Babel default/source locale and has no catalogue.
        missing = [
            code for code in LANGUAGES
            if code != 'en' and not os.path.isfile(
                os.path.join(TRANSLATIONS_DIR, code, 'LC_MESSAGES', 'messages.mo')
            )
        ]
        assert missing == [], (
            f"languages listed without a compiled catalogue: {missing}"
        )

    def test_hungarian_is_listed(self):
        assert LANGUAGES.get('hu') == 'Magyar'


class TestLanguagePicker:
    def test_hungarian_in_settings_picker(self, auth_client):
        response = auth_client.get('/auth/settings')
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'value="hu"' in body
        assert 'Magyar' in body


class TestHungarianStrings:
    def test_hungarian_strings_render(self, app):
        # Assert the translation differs from the English source rather than
        # pinning the exact wording, so revising the catalogue is not a
        # breaking change.
        with force_locale('hu'):
            assert gettext('Dashboard') != 'Dashboard'
