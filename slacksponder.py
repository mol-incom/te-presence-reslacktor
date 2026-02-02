#!/usr/bin/env python3
"""Add reactions to a Slack message."""

import argparse
import os
import re
import sys

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

day_to_emoji = {
    'monday': 'red_circle',
    'tuesday': 'large_orange_circle',
    'wednesday': 'large_yellow_circle',
    'thursday': 'large_green_circle',
    'friday': 'large_blue_circle',
}


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


def submit_reactions(token: str, channel: str, timestamp: str, reactions: list[str]) -> None:
    """Add reactions to a Slack message."""
    client = WebClient(token=token)

    for reaction in reactions:
        # Remove colons if user included them (e.g., :thumbsup: -> thumbsup)
        reaction = reaction.strip(":")
        try:
            client.reactions_add(channel=channel, timestamp=timestamp, name=reaction)
            print(f"Added :{reaction}:")
        except SlackApiError as e:
            if e.response["error"] == "already_reacted":
                print(f"Already reacted with :{reaction}:")
            else:
                print(f"Failed to add :{reaction}: - {e.response['error']}", file=sys.stderr)


def select_days() -> list[str]:
    """Prompt user to select days and return corresponding emoji names."""
    days = list(day_to_emoji.keys())
    print("Select days (comma-separated numbers, or 'all'):")
    for i, day in enumerate(days, 1):
        print(f"  {i}. {day} (:{day_to_emoji[day]}:)")

    selection = input("> ").strip().lower()

    if selection == "all":
        return list(day_to_emoji.values())

    selected_emojis = []
    for part in selection.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(days):
                selected_emojis.append(day_to_emoji[days[idx]])
        elif part in day_to_emoji:
            selected_emojis.append(day_to_emoji[part])

    return selected_emojis


def main():
    parser = argparse.ArgumentParser(description="Add reactions to a Slack message")
    parser.add_argument("link", help="Slack message link")
    args = parser.parse_args()

    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        print("Error: SLACK_USER_TOKEN environment variable not set", file=sys.stderr)
        print("\nTo get a user token:", file=sys.stderr)
        print("1. Create a Slack app at https://api.slack.com/apps", file=sys.stderr)
        print("2. Add 'reactions:write' to User Token Scopes", file=sys.stderr)
        print("3. Install the app to your workspace", file=sys.stderr)
        print("4. Copy the User OAuth Token (starts with xoxp-)", file=sys.stderr)
        sys.exit(1)
    try:
        channel, timestamp = parse_slack_url(args.link)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    reactions = select_days()
    if not reactions:
        print("No days selected")
        sys.exit(0)

    submit_reactions(token, channel, timestamp, reactions)


if __name__ == "__main__":
    main()
