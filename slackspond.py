#!/usr/bin/env python3
"""Add reactions to a Slack message."""

import argparse
import os
import re
import sys

import emoji
import questionary
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# day_to_emoji = {
#     "monday": "red_circle",
#     "tuesday": "large_orange_circle",
#     "wednesday": "large_yellow_circle",
#     "thursday": "large_green_circle",
#     "friday": "large_blue_circle",
# }


def log(msg: str):
    print(msg, file=sys.stderr)


def emoji_of_name(name: str) -> str:
    """Convert an emoji name to its Unicode character."""
    name = name.removeprefix("large_")  # Slack-quick: some emoji have prefix "large_" for some reason...
    return emoji.emojize(f":{name}:", language="alias")


def parse_slack_url(url: str) -> tuple[str, str]:
    """Extract channel ID and message timestamp from a Slack message link.

    Links look like: https://workspace.slack.com/archives/C1234567890/p1234567890123456
    """
    match = re.search(r"/archives/([A-Z0-9]+)/p(\d+)", url)
    if not match:
        raise ValueError(f"cannot parse Slack URL: {url}")
    channel_id = match.group(1)
    # Convert p1234567890123456 to 1234567890.123456
    raw_ts = match.group(2)
    timestamp = f"{raw_ts[:-6]}.{raw_ts[-6:]}"
    return channel_id, timestamp


def fetch_message(client: WebClient, channel: str, timestamp: str) -> str:
    """Fetch a message's text from Slack."""
    response = client.conversations_history(channel=channel, latest=timestamp, oldest=timestamp, inclusive=True, limit=1)
    messages = response.get("messages", [])
    if not messages:
        raise ValueError(f"Message not found: {channel}/{timestamp}")
    return messages[0].get("text", "")


def parse_line_day_emoji(line: str) -> tuple[str, str] | None:
    """Parse a day and emoji from a single line.

    Returns (day_id, emoji_name) if found, None otherwise.
    """
    line_lower = line.lower()
    day_id = None
    for weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if weekday in line_lower:
            day_id = weekday
            break
    if not day_id:
        return None
    emoji_match = re.search(r":([a-z_]+):", line)
    if not emoji_match:
        return None
    return day_id, emoji_match.group(1)


def parse_emoji_from_message(text: str) -> dict[str, str]:
    """Parse day-to-emoji mapping from message text."""
    result = {}
    for line in text.splitlines():
        pair = parse_line_day_emoji(line)
        if pair:
            day_id, emoji_name = pair
            result[day_id] = emoji_name
    return result


def submit_reactions(token: str, channel: str, timestamp: str, reactions: dict[str, bool]) -> None:
    """Add reactions to a Slack message."""
    client = WebClient(token=token)

    for reaction, enable in reactions.items():
        # Remove colons if user included them (e.g., :thumbsup: -> thumbsup).
        reaction = reaction.strip(":")
        try:
            if enable:
                log(f"Enabling reaction :{reaction}:")
                client.reactions_add(channel=channel, timestamp=timestamp, name=reaction)
            else:
                log(f"Disabling reaction :{reaction}:")
                client.reactions_remove(channel=channel, timestamp=timestamp, name=reaction)
        except SlackApiError as e:
            if e.response["error"] == "already_reacted":
                log(f"Reaction :{reaction}: already enabled")
            elif e.response["error"] == "no_reaction":
                log(f"Reaction :{reaction}: already disabled")
            else:
                log(f"Failed to add/remove reaction :{reaction}: - {e.response["error"]}")


def select_days(day_emoji_map: dict[str, str]) -> list[str]:
    """Prompt user to select days and return emoji names with checked state."""
    choices = [
        questionary.Choice(f"{emoji_of_name(emoji)}  {day.capitalize()}", value=day)
        for day, emoji in day_emoji_map.items()
    ]
    return questionary.checkbox("Select days:", choices=choices).ask()


def main():
    parser = argparse.ArgumentParser(description="Add reactions to a Slack message")
    parser.add_argument("link", help="Slack message link")
    args = parser.parse_args()

    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        log("Error: SLACK_USER_TOKEN environment variable not set")
        log("\nTo get a user token:")
        log("1. Create a Slack app at https://api.slack.com/apps")
        log("2. Add 'reactions:write' and 'channels:history' to User Token Scopes")
        log("3. Install the app to your workspace")
        log("4. Copy the User OAuth Token (starts with xoxp-)")
        sys.exit(1)
    try:
        channel, timestamp = parse_slack_url(args.link)
    except ValueError as e:
        log(f"Error: {e}")
        sys.exit(1)

    client = WebClient(token=token)
    try:
        message_text = fetch_message(client, channel, timestamp)
    except (SlackApiError, ValueError) as e:
        log(f"Error fetching message: {e}")
        sys.exit(1)

    day_emoji_map = parse_emoji_from_message(message_text)
    if not day_emoji_map:
        log("Could not parse any day/emoji pairs from message")
        log(f"Message text: {message_text}")
        sys.exit(1)

    days = select_days(day_emoji_map)
    reactions = { emoji : day in days for day, emoji in day_emoji_map.items() }
    submit_reactions(token, channel, timestamp, reactions)


if __name__ == "__main__":
    main()
