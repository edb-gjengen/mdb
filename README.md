A Django app for managing computer equipment.

## Installation
    sudo apt install libmysqlclient-dev python-dev libldap2-dev libsasl2-dev bind9utils
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver

## Development tasks
Dump test data:

    python manage.py dumpdata mdb --natural-foreign --indent=4 > mdb/fixtures/test_data.json


## Features

* Creates DHCPD configuration files
* Creates DNS zone files for BIND
* TODO: Creates PXE config files (with random secret for use with Puppet autosign)
