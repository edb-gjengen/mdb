from unittest.mock import MagicMock, patch

import pytest

from mdb.services.dhcp_sync import DhcpSyncService


def make_config(serial=2, active_serial=1):
    config = MagicMock()
    config.serial = serial
    config.active_serial = active_serial
    config.dhcpd_configuration.return_value = "# dhcpd config\nsubnet 10.0.0.0 netmask 255.255.255.0 {}\n"
    return config


@pytest.fixture
def service():
    return DhcpSyncService()


# --- needs_update ---

def test_needs_update_true_when_serials_differ(service):
    config = make_config(serial=2, active_serial=1)
    assert service.needs_update(config) is True


def test_needs_update_false_when_serials_match(service):
    config = make_config(serial=1, active_serial=1)
    assert service.needs_update(config) is False


def test_needs_update_true_when_force_even_if_serials_match():
    svc = DhcpSyncService(force=True)
    config = make_config(serial=1, active_serial=1)
    assert svc.needs_update(config) is True


# --- calculate_diff ---

def test_calculate_diff_identical_returns_empty(service):
    config = make_config()
    assert service.calculate_diff(config, "line\n", "line\n") == ""


def test_calculate_diff_format(service):
    config = make_config(serial=2, active_serial=1)
    diff = service.calculate_diff(config, "new line\n", "old line\n")
    assert "*** 1" in diff
    assert "--- 2" in diff
    assert "! old line" in diff
    assert "! new line" in diff


# --- write_config ---

def test_write_config_creates_file_with_config_contents(service, tmp_path):
    config = make_config()
    output_path = str(tmp_path / "dhcpd.conf")

    service.write_config(config, output_path)

    with open(output_path) as f:
        assert f.read() == config.dhcpd_configuration.return_value


def test_write_config_updates_active_serial(service, tmp_path):
    config = make_config(serial=5, active_serial=3)
    output_path = str(tmp_path / "dhcpd.conf")

    service.write_config(config, output_path)

    assert config.active_serial == 5
    config.save.assert_called_once()


def test_write_config_returns_old_serial(service, tmp_path):
    config = make_config(serial=2, active_serial=1)
    output_path = str(tmp_path / "dhcpd.conf")

    old_serial, diff = service.write_config(config, output_path)

    assert old_serial == 1


def test_write_config_diff_reflects_changes(service, tmp_path):
    output_path = str(tmp_path / "dhcpd.conf")
    with open(output_path, "w") as f:
        f.write("old content\n")

    config = make_config(serial=2, active_serial=1)
    config.dhcpd_configuration.return_value = "new content\n"

    old_serial, diff = service.write_config(config, output_path)

    assert "old content" in diff
    assert "new content" in diff


# --- restart_service ---

def test_restart_service_returns_true_on_success(service):
    with patch("mdb.services.dhcp_sync.getstatusoutput", return_value=(0, "")):
        success, output = service.restart_service()
    assert success is True
    assert output == ""


def test_restart_service_returns_false_on_failure(service):
    with patch("mdb.services.dhcp_sync.getstatusoutput", return_value=(1, "Job failed")):
        success, output = service.restart_service()
    assert success is False
    assert output == "Job failed"
