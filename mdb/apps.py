from django.apps import AppConfig


class MdbAppConfig(AppConfig):
    name = 'mdb'
    verbose_name = 'Machine Database'

    def ready(self):
        # all models are loaded, now attach signals
        import mdb.signals  # noqa
