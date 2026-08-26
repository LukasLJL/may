"""Reproduces #342: the msgid "Registration" is shared by the vehicle
number-plate label (vehicles/view.html) and the "registration" expense
category (models.py:EXPENSE_CATEGORIES, the registration/road-tax fee).

One msgid cannot carry both senses. Roughly a dozen of the 19 shipped
catalogues translate it in the sign-up/registering sense (e.g. de
"Registrierung", cs "Registrace"), which is correct for the expense
category but wrong on the vehicle detail page, which needs the
number-plate sense (fr "Immatriculation", es "Matriculación").
"""
import os
import re

from flask_babel import force_locale, gettext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS_DIR = os.path.join(BASE_DIR, 'app', 'translations')


def _read(*parts):
    with open(os.path.join(BASE_DIR, *parts), encoding='utf-8') as f:
        return f.read()


def _catalogue_dirs():
    """Language codes that have a directory under app/translations/."""
    return sorted(
        name for name in os.listdir(TRANSLATIONS_DIR)
        if os.path.isdir(os.path.join(TRANSLATIONS_DIR, name))
    )


def _expense_category_registration_msgid():
    source = _read('app', 'models.py')
    match = re.search(
        r"\(\s*'registration'\s*,\s*_l\(\s*['\"](.+?)['\"]\s*\)\s*\)",
        source,
    )
    assert match is not None, (
        "the 'registration' expense category entry not found in "
        "EXPENSE_CATEGORIES — has it moved?"
    )
    return match.group(1)


def _vehicle_plate_label_msgid():
    source = _read('app', 'templates', 'vehicles', 'view.html')
    match = re.search(
        r"<dt[^>]*>\{\{\s*_\(\s*['\"](.+?)['\"]\s*\)\s*\}\}\s*</dt>\s*"
        r"<dd[^>]*>\{\{\s*vehicle\.registration",
        source,
    )
    assert match is not None, (
        "the vehicle detail page's number-plate <dt>/<dd> pair not found "
        "— has it moved?"
    )
    return match.group(1)


class TestPlateLabelHasItsOwnMsgid:
    def test_plate_label_and_expense_category_use_different_msgids(self):
        expense_msgid = _expense_category_registration_msgid()
        plate_msgid = _vehicle_plate_label_msgid()
        assert plate_msgid != expense_msgid, (
            "the vehicle detail page's number-plate label and the "
            "'registration' expense category (registration/road-tax fee) "
            "share the msgid %r — one msgid cannot carry both senses, so "
            "translations that are correct for the expense category (the "
            "sign-up sense, e.g. German 'Registrierung', Czech "
            "'Registrace') are wrong on the vehicle detail page, which "
            "needs the number-plate sense (#342)" % expense_msgid
        )

    def test_every_catalogue_translates_the_plate_msgid(self, app):
        # Acceptance criterion: once the plate label has its own msgid,
        # every shipped catalogue must carry a translated (non-English)
        # entry for it -- no catalogue may gain an untranslated string.
        plate_msgid = _vehicle_plate_label_msgid()
        missing = []
        for code in _catalogue_dirs():
            with force_locale(code):
                if gettext(plate_msgid) == plate_msgid:
                    missing.append(code)
        assert missing == [], (
            f"catalogues with no translated entry for the plate label "
            f"msgid {plate_msgid!r}: {missing} (#342)"
        )
