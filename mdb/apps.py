from django.apps import AppConfig
from suit.apps import DjangoSuitConfig
from suit.menu import ParentItem, ChildItem


class MdbAppConfig(AppConfig):
    name = 'mdb'
    verbose_name = 'Machine Database'

    def ready(self):
        # all models are loaded, now attach signals
        import mdb.signals  # noqa


class SuitConfig(DjangoSuitConfig):
    # Configuration for django-suit
    # See super class for configuration options
    # Ref: https://github.com/darklow/django-suit/blob/v2/demo/demo/apps.py#L6
    verbose_name = 'MDB'
    list_per_page = 25
    SEARCH_URL = '/admin/mdb/host/'  # TODO
    layout = 'vertical'

    menu = [
        ParentItem('MDB', children=[ChildItem(model='mdb.host')]),
        ParentItem('Settings', children=[
            ChildItem(model='auth.user'),
            ChildItem(model='auth.group')
        ], icon='fa fa-cog')
    ]
