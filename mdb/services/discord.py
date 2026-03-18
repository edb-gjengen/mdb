import json

import requests
from django.conf import settings

MAX_CONTENT_LENGTH = 2000


def notify(subject, message, preformatted=None):
    """Send a notification to the configured Discord webhook.

    Args:
        subject: Bold title line.
        message: Plain text body.
        preformatted: Optional content shown as a diff code block.
    """
    webhook_url = getattr(settings, "DISCORD_NOTIFICATION_WEBHOOK", None)
    if not webhook_url:
        return

    content = f"**{subject}**"
    if message:
        content += f"\n{message}"
    if preformatted:
        content += f"\n```diff\n{preformatted}\n```"

    if len(content) <= MAX_CONTENT_LENGTH:
        _send_json(webhook_url, content)
    else:
        _send_as_file(webhook_url, subject, content)


def _send_json(url, content):
    resp = requests.post(url, json={"username": "MDB", "content": content})
    resp.raise_for_status()


def _send_as_file(url, subject, content):
    payload = {"username": "MDB", "content": f"**{subject}** *(see attachment)*"}
    resp = requests.post(
        url,
        data={"payload_json": json.dumps(payload)},
        files={"files[0]": ("notification.txt", content.encode(), "text/plain")},
    )
    resp.raise_for_status()
