"""How mdbsite.settings loads production's settings, in a fresh interpreter each time,
since the settings module is imported once per process."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRINT = (
    "import django, os; os.environ['DJANGO_SETTINGS_MODULE'] = 'mdbsite.settings'; "
    "django.setup(); from django.conf import settings as s; print(s.ALLOWED_HOSTS, s.DEBUG)"
)


def run(env):
    return subprocess.run(
        [sys.executable, "-c", PRINT],
        cwd=ROOT,
        env={
            k: v
            for k, v in os.environ.items()
            if k not in ("MDB_SETTINGS", "DJANGO_DEBUG")
        }
        | env,
        capture_output=True,
        text=True,
    )


def test_settings_file_overrides(tmp_path):
    f = tmp_path / "settings.py"
    f.write_text("ALLOWED_HOSTS = ['mdb.example.org']\n")
    result = run({"MDB_SETTINGS": str(f)})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['mdb.example.org'] False"


def test_failing_settings_file_stops_mdb(tmp_path):
    # As on sega after the 24.04 upgrade: python-ldap would not load, and the old
    # `except ImportError: pass` left MDB running on the defaults.
    f = tmp_path / "settings.py"
    f.write_text("import a_module_that_does_not_exist\n")
    result = run({"MDB_SETTINGS": str(f)})
    assert result.returncode != 0
    assert "a_module_that_does_not_exist" in result.stderr


def test_missing_settings_file_stops_mdb(tmp_path):
    result = run({"MDB_SETTINGS": str(tmp_path / "missing.py")})
    assert result.returncode != 0


def test_debug_is_off_unless_asked():
    assert run({}).stdout.strip().endswith("False")
    assert run({"DJANGO_DEBUG": "1"}).stdout.strip().endswith("True")
