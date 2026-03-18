from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from mdb.management.commands.zone_sync import Command as CommandClass


@pytest.fixture
def cmd():
    c = CommandClass()
    c.stdout = StringIO()
    c.stderr = StringIO()
    return c


def make_service(changes=None):
    svc = MagicMock()
    svc.changes = changes or {
        "example.org": {"errors": None, "diff": "- old\n+ new", "success": True}
    }
    svc.run_reload_commands.return_value = (True, "", "")
    return svc


# --- run_reload_commands ---

def test_run_reload_commands_calls_all_on_success(service):
    with patch("mdb.services.zone_sync.getstatusoutput", return_value=(0, "")) as mock:
        success, _, _ = service.run_reload_commands()
    assert success is True
    assert mock.call_count == 3


def test_run_reload_commands_stops_on_first_failure(service):
    with patch(
        "mdb.services.zone_sync.getstatusoutput",
        side_effect=[(0, ""), (1, "connection refused"), (0, "")],
    ) as mock:
        success, failed_cmd, output = service.run_reload_commands()
    assert success is False
    assert "reload" in failed_cmd
    assert output == "connection refused"
    assert mock.call_count == 2  # thaw never reached


# --- reload_and_notify ---

def test_reload_and_notify_success_writes_ok(cmd):
    svc = make_service()
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        cmd.reload_and_notify(svc, errors="", diffs="diff", zones=["example.org"])
    assert "ok" in cmd.stdout.getvalue()


def test_reload_and_notify_success_calls_discord(cmd):
    svc = make_service()
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        cmd.reload_and_notify(svc, errors="", diffs="diff", zones=["example.org"])
    mock_discord.notify.assert_called_once()
    assert "✅" in mock_discord.notify.call_args.kwargs["subject"]
    assert "- example.org" in mock_discord.notify.call_args.kwargs["message"]


def test_reload_and_notify_success_passes_diff_as_preformatted(cmd):
    svc = make_service()
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        cmd.reload_and_notify(svc, errors="", diffs="- old\n+ new", zones=["example.org"])
    assert mock_discord.notify.call_args.kwargs["preformatted"] == "- old\n+ new"


def test_reload_and_notify_failure_writes_fail_and_exits(cmd):
    svc = make_service()
    svc.run_reload_commands.return_value = (False, "/usr/sbin/rndc freeze", "timed out")
    with patch("mdb.management.commands.zone_sync.discord"):
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit) as exc:
                cmd.reload_and_notify(svc, errors="", diffs="", zones=["example.org"])
    assert exc.value.code == 1
    assert "fail" in cmd.stdout.getvalue()


def test_reload_and_notify_failure_discord_includes_command_and_output(cmd):
    svc = make_service()
    svc.run_reload_commands.return_value = (False, "/usr/sbin/rndc freeze", "timed out")
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit):
                cmd.reload_and_notify(svc, errors="", diffs="", zones=["example.org"])
    subject = mock_discord.notify.call_args.kwargs["subject"]
    message = mock_discord.notify.call_args.kwargs["message"]
    assert "⚠️" in subject
    assert "rndc freeze" in message
    assert "timed out" in message
    assert "- example.org" in message


# --- handle ---

@pytest.mark.django_db
def test_handle_exits_if_zone_not_found(cmd):
    with pytest.raises(SystemExit) as exc:
        cmd.handle(debug=True, force=False, zone="nonexistent.example")
    assert exc.value.code == 1
    assert "nonexistent.example" in cmd.stderr.getvalue()


@pytest.mark.django_db
def test_handle_skips_reload_in_debug_mode(cmd, db_domain):
    with patch.object(cmd, "reload_and_notify") as mock_reload:
        cmd.handle(debug=True, force=True, zone="example.org")
    mock_reload.assert_not_called()


@pytest.mark.django_db
def test_handle_calls_reload_and_notify_when_changes_exist(cmd, db_domain):
    with patch.object(cmd, "reload_and_notify") as mock_reload:
        cmd.handle(debug=False, force=True, zone="example.org")
    mock_reload.assert_called_once()
