import os

from fabric import Connection
from invoke import task


@task()
def deploy(c):
    """Make sure proxy_user is set to your neuf username."""
    project_path = '/opt/mdb'
    proxy_user = os.getenv('DEPLOY_USER', os.getenv('USER'))

    c = Connection(host='gitdeploy@sega.neuf.no', gateway=Connection('login.neuf.no', user=proxy_user))

    with c.cd(project_path), c.prefix('source {}/venv/bin/activate'.format(project_path)):
        c.run('git pull')  # Get source
        c.run('pip install -U pip poetry')
        c.run('poetry install --no-dev')  # install deps in virtualenv
        c.run('python manage.py collectstatic --noinput')  # Collect static
        c.run('python manage.py migrate')  # Run DB migrations

    # Reload gunicorn
    c.sudo('/usr/bin/supervisorctl pid mdb.neuf.no | xargs kill -HUP', shell=False)
