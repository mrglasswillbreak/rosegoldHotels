from django.apps import AppConfig


class HotelappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'HotelApp'

    def ready(self):
        from . import signals  # noqa: F401
        from .bootstrap import ensure_env_receptionist_account

        ensure_env_receptionist_account()
