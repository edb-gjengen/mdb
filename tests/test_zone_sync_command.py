import os
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from mdb.management.commands.zone_sync import Command as CommandClass
from mdb.services.zone_sync import ZoneSyncService


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
    svc.reload.return_value = (True, "", "")
    return svc


# --- run_commands, freeze, reload ---


def test_run_commands_calls_all_on_success(service):
    with patch("mdb.services.zone_sync.getstatusoutput", return_value=(0, "")) as mock:
        success, _, _ = service.run_commands(["a", "b", "c"])
    assert success is True
    assert mock.call_count == 3


def test_run_commands_stops_on_first_failure(service):
    with patch(
        "mdb.services.zone_sync.getstatusoutput",
        side_effect=[(0, ""), (1, "connection refused"), (0, "")],
    ) as mock:
        success, failed_cmd, output = service.run_commands(["a", "b", "c"])
    assert success is False
    assert failed_cmd == "b"
    assert output == "connection refused"
    assert mock.call_count == 2


def test_freeze_runs_only_freeze(service):
    with patch("mdb.services.zone_sync.getstatusoutput", return_value=(0, "")) as mock:
        service.freeze()
    assert [c.args[0] for c in mock.call_args_list] == [service.freeze_command]


def test_reload_runs_reload_then_thaw(service):
    with patch("mdb.services.zone_sync.getstatusoutput", return_value=(0, "")) as mock:
        service.reload()
    assert [c.args[0] for c in mock.call_args_list] == [
        service.reload_command,
        service.thaw_command,
    ]


# --- reload_and_notify ---


def test_reload_and_notify_success_writes_ok(cmd):
    svc = make_service()
    with patch("mdb.management.commands.zone_sync.discord"):
        cmd.reload_and_notify(svc, svc.changes)
    assert "ok" in cmd.stdout.getvalue()


def test_reload_and_notify_success_calls_discord_once_per_zone(cmd):
    changes = {
        "example.org": {"errors": None, "diff": "- old\n+ new"},
        "other.net": {"errors": None, "diff": "- x\n+ y"},
    }
    svc = make_service(changes=changes)
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        cmd.reload_and_notify(svc, svc.changes)
    assert mock_discord.notify.call_count == 2
    subjects = [c.kwargs["subject"] for c in mock_discord.notify.call_args_list]
    messages = [c.kwargs["message"] for c in mock_discord.notify.call_args_list]
    assert all("✅" in s for s in subjects)
    assert any("`example.org`" in m for m in messages)
    assert any("`other.net`" in m for m in messages)


def test_reload_and_notify_success_passes_diff_as_preformatted(cmd):
    svc = make_service()
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        cmd.reload_and_notify(svc, svc.changes)
    assert mock_discord.notify.call_args.kwargs["preformatted"] == "- old\n+ new"


def test_reload_and_notify_failure_writes_fail_and_exits(cmd):
    svc = make_service()
    svc.reload.return_value = (False, "/usr/sbin/rndc reload", "timed out")
    with patch("mdb.management.commands.zone_sync.discord"):
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit) as exc:
                cmd.reload_and_notify(svc, svc.changes)
    assert exc.value.code == 1
    assert "fail" in cmd.stdout.getvalue()


def test_reload_and_notify_failure_discord_includes_command_and_output(cmd):
    svc = make_service()
    svc.reload.return_value = (False, "/usr/sbin/rndc reload", "timed out")
    with patch("mdb.management.commands.zone_sync.discord") as mock_discord:
        with patch("os.getlogin", return_value="testuser"):
            with pytest.raises(SystemExit):
                cmd.reload_and_notify(svc, svc.changes)
    subject = mock_discord.notify.call_args.kwargs["subject"]
    message = mock_discord.notify.call_args.kwargs["message"]
    assert "⚠️" in subject
    assert "rndc reload" in message
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
    with (
        patch.object(cmd, "freeze"),
        patch.object(cmd, "reload_and_notify") as mock_reload,
    ):
        cmd.handle(debug=False, force=True, zone="example.org")
    mock_reload.assert_called_once()


@pytest.mark.django_db
def test_handle_does_nothing_without_pending_zones(cmd):
    with patch.object(ZoneSyncService, "freeze") as mock_freeze:
        cmd.handle(debug=False, force=False, zone=None)
    mock_freeze.assert_not_called()


@pytest.mark.django_db
def test_handle_freezes_before_writing_and_reloads_after(cmd, db_domain):
    """rndc freeze dumps the in-memory zone, so it must not run after the write."""
    seen = []

    def freeze():
        seen.append(("freeze", os.path.exists(db_domain.domain_filename)))
        return True, "", ""

    def reload():
        seen.append(("reload", os.path.exists(db_domain.domain_filename)))
        return True, "", ""

    with (
        patch.object(ZoneSyncService, "freeze", side_effect=freeze),
        patch.object(ZoneSyncService, "reload", side_effect=reload),
        patch("mdb.management.commands.zone_sync.discord"),
    ):
        cmd.handle(debug=False, force=False, zone=None)

    assert seen == [("freeze", False), ("reload", True)]


@pytest.mark.django_db
def test_handle_writes_nothing_when_freeze_fails(cmd, db_domain):
    with (
        patch.object(
            ZoneSyncService, "freeze", return_value=(False, "rndc freeze", "no")
        ),
        patch.object(ZoneSyncService, "run_commands") as mock_run,
        patch("mdb.management.commands.zone_sync.discord") as mock_discord,
        patch("os.getlogin", return_value="testuser"),
        pytest.raises(SystemExit),
    ):
        cmd.handle(debug=False, force=False, zone=None)

    assert not os.path.exists(db_domain.domain_filename)
    mock_run.assert_called_once_with([ZoneSyncService.thaw_command])
    assert "- example.org" in mock_discord.notify.call_args.kwargs["message"]


@pytest.mark.django_db
def test_handle_thaws_when_sync_raises(cmd, db_domain):
    with (
        patch.object(ZoneSyncService, "freeze", return_value=(True, "", "")),
        patch.object(ZoneSyncService, "reload") as mock_reload,
        patch.object(ZoneSyncService, "sync_zone", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        cmd.handle(debug=False, force=False, zone=None)

    mock_reload.assert_called_once()
