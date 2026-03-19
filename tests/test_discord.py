from unittest.mock import MagicMock, patch

import pytest

from mdb.services import discord


@pytest.fixture(autouse=True)
def webhook_url(settings):
    settings.DISCORD_NOTIFICATION_WEBHOOK = "https://discord.example/webhook"


def test_notify_does_nothing_without_webhook(settings):
    settings.DISCORD_NOTIFICATION_WEBHOOK = None
    with patch("mdb.services.discord._send_json") as mock:
        discord.notify("Subject", "message")
    mock.assert_not_called()


def test_notify_sends_json_for_short_content():
    with patch("mdb.services.discord._send_json") as mock:
        discord.notify("Subject", "message")
    mock.assert_called_once()
    _, content = mock.call_args.args
    assert "**Subject**" in content
    assert "message" in content


def test_notify_includes_preformatted_as_diff_code_block():
    with patch("mdb.services.discord._send_json") as mock:
        discord.notify("Subject", "message", preformatted="- old\n+ new")
    _, content = mock.call_args.args
    assert "```diff\n- old\n+ new\n```" in content


def test_notify_sends_file_when_content_exceeds_limit():
    long_diff = "x" * discord.MAX_CONTENT_LENGTH
    with patch("mdb.services.discord._send_as_file") as mock:
        discord.notify("Subject", "message", preformatted=long_diff)
    mock.assert_called_once()


def test_notify_sends_json_when_content_fits():
    with patch("mdb.services.discord._send_json") as mock:
        discord.notify("Subject", "short message")
    mock.assert_called_once()


def test_send_json_posts_with_mdb_username():
    mock_resp = MagicMock()
    with patch("requests.post", return_value=mock_resp) as mock_post:
        discord._send_json("https://discord.example/webhook", "hello")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["username"] == "MDB"
    assert payload["content"] == "hello"
    mock_resp.raise_for_status.assert_called_once()


def test_send_as_file_posts_multipart_with_attachment():
    mock_resp = MagicMock()
    with patch("requests.post", return_value=mock_resp) as mock_post:
        discord._send_as_file(
            "https://discord.example/webhook", "Subject", "full content"
        )
    assert mock_post.call_args.kwargs.get("files") or "files" in str(
        mock_post.call_args
    )
    mock_resp.raise_for_status.assert_called_once()


def test_send_as_file_content_mentions_attachment():
    import json

    mock_resp = MagicMock()
    with patch("requests.post", return_value=mock_resp) as mock_post:
        discord._send_as_file(
            "https://discord.example/webhook", "MySubject", "full content"
        )
    data = mock_post.call_args.kwargs["data"]
    payload = json.loads(data["payload_json"])
    assert "MySubject" in payload["content"]
    assert "attachment" in payload["content"]
