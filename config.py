import os
from pathlib import Path

from dotenv import load_dotenv

basedir = Path(__file__).parent.absolute()

# Load the .env file sitting next to this module before anything reads the
# environment (#297). Values already present in the real environment win, so
# Docker deployments that set these via compose are unaffected.
load_dotenv(basedir / '.env')


APP_VERSION = '0.35.2'
RELEASE_CHANNEL = os.environ.get('RELEASE_CHANNEL', 'stable')
GIT_SHA = os.environ.get('GIT_SHA', '')[:7]  # Short SHA
GITHUB_REPO = 'dannymcc/may'
TAILWIND_ASSET_URL = os.environ.get('TAILWIND_ASSET_URL', '/static/vendor/tailwindcss.js')
TAILWIND_CDN_URL = os.environ.get('TAILWIND_CDN_URL', 'https://cdn.tailwindcss.com')
HTMX_ASSET_URL = os.environ.get('HTMX_ASSET_URL', '/static/vendor/htmx.min.js')
HTMX_CDN_URL = os.environ.get('HTMX_CDN_URL', 'https://unpkg.com/htmx.org@1.9.10')
FLATPICKR_JS_ASSET_URL = os.environ.get('FLATPICKR_JS_ASSET_URL', '/static/vendor/flatpickr.min.js')
FLATPICKR_JS_CDN_URL = os.environ.get('FLATPICKR_JS_CDN_URL', 'https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/flatpickr.min.js')
FLATPICKR_CSS_ASSET_URL = os.environ.get('FLATPICKR_CSS_ASSET_URL', '/static/vendor/flatpickr.min.css')
FLATPICKR_CSS_CDN_URL = os.environ.get('FLATPICKR_CSS_CDN_URL', 'https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/flatpickr.min.css')

# Build display version (e.g., "0.5.0" for stable, "0.5.0-dev+abc1234" for dev)
if RELEASE_CHANNEL == 'dev' and GIT_SHA:
    DISPLAY_VERSION = f"{APP_VERSION}-dev+{GIT_SHA}"
elif RELEASE_CHANNEL == 'dev':
    DISPLAY_VERSION = f"{APP_VERSION}-dev"
else:
    DISPLAY_VERSION = APP_VERSION


SECRET_KEY_FILE = basedir / 'data' / '.secret_key'


def _load_or_create_secret_key(path=SECRET_KEY_FILE):
    """Return a session-signing key, generating and persisting one if needed.

    A generated key has to be stable across processes as well as restarts:
    gunicorn runs several workers, each importing this module separately, so a
    key held only in memory differs per worker. A session cookie signed by one
    worker then fails validation on another and the user is bounced back to
    the login page on the next request (#317). Keeping the key in a file under
    the data directory gives every worker the same key, and sessions survive a
    restart too.

    If the file cannot be written (a read-only filesystem, say) this falls
    back to the previous behaviour: an in-memory key, with a warning.
    """
    import secrets

    try:
        key = path.read_text().strip()
        if key:
            return key
    except OSError:
        pass

    key = secrets.token_hex(32)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Exclusive create so two workers booting together cannot clobber
            # each other's key; the loser reads the winner's instead.
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            existing = path.read_text().strip()
            if existing:
                return existing
            raise
        try:
            os.write(fd, key.encode())
        finally:
            os.close(fd)
    except OSError:
        import warnings
        warnings.warn(
            "SECRET_KEY environment variable not set and the generated key "
            f"could not be saved to {path}. Sessions will not persist across "
            "restarts, and will break between worker processes. "
            "Set SECRET_KEY for production.",
            RuntimeWarning
        )
    return key


class Config:
    APP_VERSION = APP_VERSION
    DISPLAY_VERSION = DISPLAY_VERSION
    RELEASE_CHANNEL = RELEASE_CHANNEL
    GIT_SHA = GIT_SHA
    GITHUB_REPO = GITHUB_REPO
    TAILWIND_ASSET_URL = TAILWIND_ASSET_URL
    TAILWIND_CDN_URL = TAILWIND_CDN_URL
    HTMX_ASSET_URL = HTMX_ASSET_URL
    HTMX_CDN_URL = HTMX_CDN_URL
    FLATPICKR_JS_ASSET_URL = FLATPICKR_JS_ASSET_URL
    FLATPICKR_JS_CDN_URL = FLATPICKR_JS_CDN_URL
    FLATPICKR_CSS_ASSET_URL = FLATPICKR_CSS_ASSET_URL
    FLATPICKR_CSS_CDN_URL = FLATPICKR_CSS_CDN_URL
    SECRET_KEY = os.environ.get('SECRET_KEY') or _load_or_create_secret_key()
    _database_url = os.environ.get('DATABASE_URL') or f'sqlite:///{basedir}/data/may.db'
    # SQLAlchemy 2.x dropped the legacy 'postgres://' scheme still emitted by
    # some hosting providers; normalise it so those URLs keep working (#239).
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(basedir / 'data' / 'uploads')
    MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # 300MB max upload
