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

day_to_emoji = {
    "monday": "red_circle",
    "tuesday": "large_orange_circle",
    "wednesday": "large_yellow_circle",
    "thursday": "large_green_circle",
    "friday": "large_blue_circle",
}


def log(msg: str):
    print(msg, file=sys.stderr)


def emojize(name: str) -> str:
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


def submit_reactions(token: str, channel: str, timestamp: str, reactions: list[str]) -> None:
    """Add reactions to a Slack message."""
    client = WebClient(token=token)

    for reaction in reactions:
        # Remove colons if user included them (e.g., :thumbsup: -> thumbsup).
        reaction = reaction.strip(":")
        log(f"Adding reaction :{reaction}: ...")
        try:
            client.reactions_add(channel=channel, timestamp=timestamp, name=reaction)
        except SlackApiError as e:
            if e.response["error"] == "already_reacted":
                log(f"Already reacted with :{reaction}:")
            else:
                log(f"Failed to add reaction :{reaction}: - {e.response['error']}")


def select_days() -> list[str]:
    """Prompt user to select days and return corresponding emoji names."""
    choices = [
        questionary.Choice(f"{emojize(emoji_name)}  {day.capitalize()}", value=emoji_name)
        for day, emoji_name in day_to_emoji.items()
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
        log("2. Add 'reactions:write' to User Token Scopes")
        log("3. Install the app to your workspace")
        log("4. Copy the User OAuth Token (starts with xoxp-)")
        sys.exit(1)
    try:
        channel, timestamp = parse_slack_url(args.link)
    except ValueError as e:
        log(f"Error: {e}")
        sys.exit(1)

    reactions = select_days()
    if not reactions:
        log("No days selected")
        return
    submit_reactions(token, channel, timestamp, reactions)


if __name__ == "__main__":
    main()
