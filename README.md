A Django app for managing computer equipment.

## Installation
    sudo apt-get install libmysqlclient-dev python-dev libldap2-dev libsasl2-dev bind9utils
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver

## Features

* Creates DHCPD configuration files
* Creates DNS zone files for BIND
* TODO: Creates PXE config files (with random secret for use with Puppet autosign)