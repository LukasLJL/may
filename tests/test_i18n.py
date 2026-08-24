"""Tests for language selection — LANGUAGES vs the shipped catalogues (#300)."""
import os

from flask_babel import force_locale, gettext

from app import LANGUAGES, db

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


class TestUnitsAndValuesTranslation:
    """The Units & Values options on the settings page must go through
    gettext like the rest of the page (#310).

    "Liters (L)" already has a French catalogue entry ("Litres (L)")
    because it is marked for translation in vehicles/part_form.html and
    app/models.py. The settings page reuses the same English wording for
    its volume_unit option, but as a hard-coded literal rather than a
    gettext call, so it never picks up that existing translation no matter
    what language the user has selected.
    """

    def test_volume_unit_options_are_translated(self, client, test_user):
        test_user.language = 'fr'
        db.session.commit()

        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'TestPass123!',
        }, follow_redirects=True)

        response = client.get('/auth/settings')
        assert response.status_code == 200
        body = response.get_data(as_text=True)

        assert 'Litres (L)' in body, (
            "the volume_unit option 'Liters (L)' is not passed through "
            "gettext() in settings.html, so it is never translated even "
            "though a French translation for it already exists in the "
            "catalogue"
        )

    def _french_settings_page(self, client, test_user):
        test_user.language = 'fr'
        db.session.commit()

        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'TestPass123!',
        }, follow_redirects=True)

        response = client.get('/auth/settings')
        assert response.status_code == 200
        return response.get_data(as_text=True)

    def test_date_format_options_are_translated(self, client, test_user):
        body = self._french_settings_page(client, test_user)

        assert 'JJ/MM/AAAA (15/01/2024)' in body
        assert 'AAAA-MM-JJ (2024-01-15)' in body

    def test_distance_and_consumption_options_are_translated(
            self, client, test_user):
        body = self._french_settings_page(client, test_user)

        assert 'Kilomètres (km)' in body
        assert 'Gallons impériaux (gal)' in body
        assert 'Gallons américains (gal)' in body

    def test_option_values_stay_untranslated(self, client, test_user):
        # Only the labels are localised — the submitted values are what the
        # user record stores, so they must remain the English/unit codes.
        body = self._french_settings_page(client, test_user)

        for value in ('DD/MM/YYYY', 'YYYY-MM-DD', 'km', 'gal', 'us_gal',
                      'L/100km', 'mpg_us'):
            assert 'value="%s"' % value in body

    def test_every_catalogue_translates_the_unit_options(self, app):
        # Wrapping the options only helps if each shipped catalogue has an
        # entry for them; a missing entry renders as English.
        msgids = [
            'DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'DD.MM.YYYY',
            'Kilometres (km)', 'Liters (L)', 'UK Gallons (gal)',
            'US Gallons (gal)',
        ]
        missing = []
        for code in _catalogue_dirs():
            with force_locale(code):
                missing += [
                    f'{code}: {msgid}' for msgid in msgids
                    if gettext(msgid) == msgid
                ]
        assert missing == [], (
            f"unit option labels with no catalogue entry: {missing}"
        )
