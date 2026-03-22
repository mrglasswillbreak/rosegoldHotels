from django.apps import AppConfig


class HotelappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'HotelApp'

    def ready(self):
        from . import signals  # noqa: F401
