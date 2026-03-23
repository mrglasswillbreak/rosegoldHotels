import logging
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError


logger = logging.getLogger(__name__)

BLOCKED_COMMANDS = {"makemigrations", "migrate", "collectstatic", "test"}
_SYNC_ALREADY_ATTEMPTED = False


def receptionist_env_is_configured():
    return bool(settings.DEFAULT_RECEPTIONIST_EMAIL and settings.DEFAULT_RECEPTIONIST_PASSWORD)


def should_sync_default_receptionist():
    if not receptionist_env_is_configured():
        return False
    if any(command in sys.argv for command in BLOCKED_COMMANDS):
        return False
    return True


def ensure_env_receptionist_account(*, force=False):
    global _SYNC_ALREADY_ATTEMPTED

    if _SYNC_ALREADY_ATTEMPTED and not force:
        return None
    if not force and not should_sync_default_receptionist():
        return None

    user_model = get_user_model()
    email = user_model.objects.normalize_email(settings.DEFAULT_RECEPTIONIST_EMAIL)
    password = settings.DEFAULT_RECEPTIONIST_PASSWORD

    try:
        user = user_model.objects.filter(email=email).first()
        if user and user.is_superuser and not user.is_receptionist:
            logger.warning(
                "Skipping default receptionist sync because %s belongs to a superuser account.",
                email,
            )
            _SYNC_ALREADY_ATTEMPTED = True
            return user

        if user is None:
            user = user_model(email=email)

        user.first_name = settings.DEFAULT_RECEPTIONIST_FIRST_NAME
        user.last_name = settings.DEFAULT_RECEPTIONIST_LAST_NAME
        user.phone_number = settings.DEFAULT_RECEPTIONIST_PHONE or None
        user.theme = settings.DEFAULT_RECEPTIONIST_THEME
        user.is_active = settings.DEFAULT_RECEPTIONIST_IS_ACTIVE
        user.is_receptionist = True
        user.is_staff = False
        user.is_superuser = False

        if password and (settings.DEFAULT_RECEPTIONIST_SYNC_PASSWORD or not user.pk):
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()

        user.save()
        _SYNC_ALREADY_ATTEMPTED = True
        return user
    except (OperationalError, ProgrammingError):
        logger.debug("Skipping default receptionist sync because the user table is not ready yet.", exc_info=True)
        return None
