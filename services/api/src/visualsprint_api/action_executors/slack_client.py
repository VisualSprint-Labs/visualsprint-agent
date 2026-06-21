"""Slack action executor for VisualSprint."""

from __future__ import annotations

import json
from urllib import error, request

from visualsprint_api.config import settings
from visualsprint_api.models import ActionRecommendation, SlackRecommendation


def execute_slack_action(recommendation: ActionRecommendation) -> tuple[bool, str]:
    """Execute a Slack action. Returns (success, detail)."""

    slack_details = recommendation.slackDetails
    if slack_details is None:
        return False, "No Slack details found in recommendation."

    if not settings.slack_bot_token_secret:
        return _execute_slack_stub(slack_details)

    return _post_slack_message(slack_details)


def _looks_like_channel_id(value: str) -> bool:
    # Slack channel/DM IDs start with C, G or D followed by uppercase/digits.
    return len(value) >= 9 and value[0] in {"C", "G", "D"} and value[1:].isalnum() and value.isupper()


# The action agent emits placeholder strings when it has no specific channel in
# mind. These must fall back to the configured default channel, not be posted to.
_PLACEHOLDER_CHANNELS = {"not specified", "not_specified", "none", "n/a", "na", "unknown", ""}


def _resolve_channel(slack_channel: str | None) -> str:
    candidate = (slack_channel or "").strip()
    if candidate.lower().lstrip("#@") in _PLACEHOLDER_CHANNELS:
        candidate = (settings.slack_default_channel or "").strip()
    return candidate or "general"


def _post_slack_message(slack_details: SlackRecommendation) -> tuple[bool, str]:
    url = "https://slack.com/api/chat.postMessage"
    raw = _resolve_channel(slack_details.channel)

    # A channel ID is the most reliable target (works with only chat:write). A
    # plain name requires channels:read for the bot to resolve it.
    if _looks_like_channel_id(raw):
        channel = raw
    else:
        channel = raw if raw.startswith(("#", "@")) else f"#{raw.lstrip('#')}"

    payload = {
        "channel": channel,
        "text": f"*{slack_details.title}*\n{slack_details.message}",
        "unfurl_links": False,
    }

    # Defensive strip: stored secrets can carry a trailing CR/newline.
    token = (settings.slack_bot_token_secret or "").strip()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        response = request.urlopen(
            request.Request(
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            ),
            timeout=10,
        )
        result = json.loads(response.read().decode("utf-8"))
        if result.get("ok"):
            ts = result.get("ts", "unknown")
            return True, f"Slack message posted to {channel} (ts={ts})"
        error_msg = result.get("error", "unknown_error")
        if error_msg in {"channel_not_found", "not_in_channel"}:
            return False, (
                f"Slack error '{error_msg}' for {channel}. Invite the bot to the channel "
                "(/invite @visualsprint_agent) and set SLACK_DEFAULT_CHANNEL to the channel ID, "
                "or grant the bot the channels:read scope so it can resolve channel names."
            )
        if error_msg == "missing_scope":
            return False, "Slack error 'missing_scope': the bot token needs the chat:write scope."
        return False, f"Slack API error: {error_msg}"
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return False, f"Slack HTTP error {e.code}: {body}"
    except error.URLError as e:
        return False, f"Slack connection error: {e.reason}"


def _execute_slack_stub(slack_details: SlackRecommendation) -> tuple[bool, str]:
    channel = slack_details.channel or settings.slack_default_channel or "#general"
    detail = (
        f"[SLACK STUB] {slack_details.type}: '{slack_details.title}' "
        f"to channel {channel}"
    )
    return True, detail
