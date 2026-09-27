A Django app for managing computer equipment.

## Installation

Install system dependencies:

    sudo apt install python-dev libldap2-dev libsasl2-dev bind9-utils

Use [mise](https://mise.jdx.dev/) to manage Python and uv:

    mise trust
    mise install

Install Python dependencies with uv:

    uv sync

Run migrations and start the development server:

    uv run python manage.py migrate
    uv run python manage.py runserver

## Development tasks

Dump test data:

    uv run python manage.py dumpdata mdb --natural-foreign --indent=4 > mdb/fixtures/test_data.json

## Features

- Creates DHCPD configuration files
- Creates DNS zone files for BIND
- Creates PXE config files (with random secret for use with Puppet autosign)
- Partial IPv6 support
