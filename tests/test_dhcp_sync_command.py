from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from mdb.management.commands.dhcp_sync import Command as CommandClass


@pytest.fixture
def cmd():
    c = CommandClass()
    c.stdout = StringIO()
    c.stderr = StringIO()
    return c


def make_service(serial=2, active_serial=1, restart_success=True, restart_output=""):
    svc = MagicMock()
    svc.force = False
    svc.restart_command = "/usr/sbin/service isc-dhcp-server restart"
    config = MagicMock()
    config.serial = serial
    config.active_serial = active_serial
    config.dhcpd_configuration.return_value = "# dhcpd config\n"
    svc.get_config.return_value = config
    svc.needs_update.return_value = serial != active_serial
    svc.write_config.return_value = (active_serial, "- old\n+ new")
    svc.restart_service.return_value = (restart_success, restart_output)
    return svc, config


# --- handle: nothing to do ---


def test_handle_prints_nothing_to_do_when_no_update_needed(cmd):
    svc, config = make_service(serial=1, active_serial=1)
    svc.needs_update.return_value = False
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        cmd.handle(output=None, force=False, restart=False)
    assert "Nothing to do" in cmd.stdout.getvalue()


# --- handle: stdout mode ---


def test_handle_prints_config_to_stdout_when_no_output_path(cmd):
    svc, config = make_service()
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        cmd.handle(output=None, force=False, restart=False)
    assert "# dhcpd config" in cmd.stdout.getvalue()
    assert "Not writing to file" in cmd.stdout.getvalue()


def test_handle_does_not_write_file_when_no_output_path(cmd):
    svc, config = make_service()
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        cmd.handle(output=None, force=False, restart=False)
    svc.write_config.assert_not_called()


# --- handle: file mode ---


def test_handle_calls_write_config_when_output_given(cmd, tmp_path):
    svc, config = make_service()
    output_path = str(tmp_path / "dhcpd.conf")
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        cmd.handle(output=output_path, force=False, restart=False)
    svc.write_config.assert_called_once_with(config, output_path)


def test_handle_does_not_restart_when_restart_false(cmd, tmp_path):
    svc, config = make_service()
    output_path = str(tmp_path / "dhcpd.conf")
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        with patch.object(cmd, "restart_and_notify") as mock_restart:
            cmd.handle(output=output_path, force=False, restart=False)
    mock_restart.assert_not_called()


def test_handle_calls_restart_and_notify_when_restart_true(cmd, tmp_path):
    svc, config = make_service()
    output_path = str(tmp_path / "dhcpd.conf")
    with patch("mdb.management.commands.dhcp_sync.DhcpSyncService", return_value=svc):
        with patch.object(cmd, "restart_and_notify") as mock_restart:
            cmd.handle(output=output_path, force=False, restart=True)
    mock_restart.assert_called_once()


# --- restart_and_notify ---


def test_restart_and_notify_success_writes_ok(cmd):
    svc, config = make_service(restart_success=True)
    with patch("mdb.management.commands.dhcp_sync.discord"):
        cmd.restart_and_notify(svc, config, old_serial=1, diff="- old\n+ new")
    assert "ok" in cmd.stdout.getvalue()


def test_restart_and_notify_success_calls_discord(cmd):
    svc, config = make_service(restart_success=True)
    with patch("mdb.management.commands.dhcp_sync.discord") as mock_discord:
        cmd.restart_and_notify(svc, config, old_serial=1, diff="- old\n+ new")
    mock_discord.notify.assert_called_once()
    assert "✅" in mock_discord.notify.call_args.kwargs["subject"]


def test_restart_and_notify_success_passes_diff_as_preformatted(cmd):
    svc, config = make_service(restart_success=True)
    with patch("mdb.management.commands.dhcp_sync.discord") as mock_discord:
        cmd.restart_and_notify(svc, config, old_serial=1, diff="- old\n+ new")
    assert mock_discord.notify.call_args.kwargs["preformatted"] == "- old\n+ new"


def test_restart_and_notify_failure_writes_fail_and_exits(cmd):
    svc, config = make_service(restart_success=False, restart_output="Job failed")
    with patch("mdb.management.commands.dhcp_sync.discord"):
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit) as exc:
                cmd.restart_and_notify(svc, config, old_serial=1, diff="")
    assert exc.value.code == 1
    assert "fail" in cmd.stdout.getvalue()


def test_restart_and_notify_failure_discord_includes_command_and_output(cmd):
    svc, config = make_service(restart_success=False, restart_output="Job failed")
    with patch("mdb.management.commands.dhcp_sync.discord") as mock_discord:
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit):
                cmd.restart_and_notify(svc, config, old_serial=1, diff="")
    subject = mock_discord.notify.call_args.kwargs["subject"]
    message = mock_discord.notify.call_args.kwargs["message"]
    assert "⚠️" in subject
    assert "isc-dhcp-server" in message
    assert "Job failed" in message
