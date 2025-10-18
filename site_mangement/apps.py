from django.apps import AppConfig


class SiteMangementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'site_mangement'

    def ready(self):
        """
        Import signals when Django starts
        This ensures all signal handlers are registered
        """
        import site_mangement.signals  # noqa
