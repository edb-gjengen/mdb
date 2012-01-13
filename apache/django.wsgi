import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# fix path
def map_path(target_name=''):
    '''Enables path names to be decided at runtime.'''
    return join(dirname(__file__), target_name).replace('\\', '/')

path = map_path("..")
if path not in sys.path:
    sys.path.append(path)

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
