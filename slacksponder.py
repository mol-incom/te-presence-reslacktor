#!/usr/bin/env python3
"""Add reactions to a Slack message."""

import argparse
import os
import re
import sys

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def parse_slack_link(link: str) -> tuple[str, str]:
    """Extract channel ID and message timestamp from a Slack message link.

    Links look like: https://workspace.slack.com/archives/C1234567890/p1234567890123456
    """
    match = re.search(r"/archives/([A-Z0-9]+)/p(\d+)", link)
    if not match:
        raise ValueError(f"Could not parse Slack link: {link}")

    channel_id = match.group(1)
    # Convert p1234567890123456 to 1234567890.123456
    raw_ts = match.group(2)
    timestamp = f"{raw_ts[:-6]}.{raw_ts[-6:]}"

    return channel_id, timestamp


def add_reactions(token: str, channel: str, timestamp: str, reactions: list[str]) -> None:
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


def main():
    parser = argparse.ArgumentParser(description="Add reactions to a Slack message")
    parser.add_argument("link", help="Slack message link")
    parser.add_argument("reactions", nargs="+", help="Reaction names (e.g., thumbsup wave)")
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
        channel, timestamp = parse_slack_link(args.link)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    add_reactions(token, channel, timestamp, args.reactions)


if __name__ == "__main__":
    main()
