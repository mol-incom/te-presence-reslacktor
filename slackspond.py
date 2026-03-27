#!/usr/bin/env python3
"""Add reactions to a Slack message."""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from collections.abc import Container
from typing import NamedTuple

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

weekdays_lower = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']


DayEmojiMap = dict[str, str]
"""Mapping from lowercase weekday name to emoji name."""


class MessageRef(NamedTuple):
    channel: str
    timestamp: str


class Message(NamedTuple):
    ref: MessageRef
    text: str


class ParsedMessage(NamedTuple):
    day_emoji_map: DayEmojiMap
    message: Message


def log(msg: str):
    print(msg, file=sys.stderr)


def emoji_of_name(name: str) -> str:
    """Convert an emoji name to its Unicode character."""
    name = name.removeprefix("large_")  # Slack-quick: some emoji have prefix "large_" for some reason...
    return emoji.emojize(f":{name}:", language="alias")


def parse_slack_url(url: str) -> MessageRef:
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
    return MessageRef(channel_id, timestamp)


def fetch_message(client: WebClient, msg: MessageRef) -> str:
    """Fetch a message's text from Slack."""
    response = client.conversations_history(channel=msg.channel, latest=msg.timestamp, oldest=msg.timestamp, inclusive=True, limit=1)
    messages = response.get("messages", [])
    if not messages:
        raise ValueError(f"Message not found: {msg.channel}/{msg.timestamp}")
    return messages[0].get("text", "")


def parse_line_day_emoji(line: str) -> tuple[str, str] | None:
    """Parse a day and emoji from a single line.

    Returns (day_id, emoji_name) if found, None otherwise.
    """
    line_lower = line.lower()
    day_id = None
    for weekday in weekdays_lower:
        if weekday in line_lower:
            day_id = weekday
            break
    if not day_id:
        return None
    emoji_match = re.search(r":([a-z_]+):", line)
    if not emoji_match:
        return None
    return day_id, emoji_match.group(1)


def parse_emoji_from_message(text: str) -> DayEmojiMap:
    """Parse day-to-emoji mapping from message text."""
    result = {}
    for line in text.splitlines():
        pair = parse_line_day_emoji(line)
        if pair:
            day_id, emoji_name = pair
            result[day_id] = emoji_name
    return result


def find_message_in_history(client: WebClient, channel: str) -> ParsedMessage:
    """Search channel history from now back to latest Friday for a message with exactly 5 day/emoji pairs."""
    now = datetime.now()
    days_since_friday = (now.weekday() - 4) % 7  # Friday is the 4th weekday
    friday = now - timedelta(days=days_since_friday)
    oldest = friday.replace(hour=0, minute=0, second=0, microsecond=0)

    cursor = None
    while True:
        response = client.conversations_history(channel=channel, oldest=str(oldest.timestamp()), limit=100, inclusive=True, cursor=cursor)
        messages = response.get("messages", [])
        # Messages are returned in reverse chronological order.
        for msg in messages:
            text = msg.get("text", "")
            day_emoji_map = parse_emoji_from_message(text)
            if len(day_emoji_map) == len(weekdays_lower):
                return ParsedMessage(day_emoji_map, Message(MessageRef(channel, msg["ts"]), text))
        metadata = response.get("response_metadata", {})
        cursor = metadata.get("next_cursor")
        if not cursor:
            raise ValueError("No message with exactly one day/emoji pair for each weekday found since last Friday")


def fetch_user_reactions(client: WebClient, msg: MessageRef) -> set[str]:
    """Fetch the set of emoji names the current user has reacted with on a message."""
    user_id = client.auth_test()["user_id"]
    response = client.reactions_get(channel=msg.channel, timestamp=msg.timestamp)
    reactions = response.get("message", {}).get("reactions", [])
    return {r["name"] for r in reactions if user_id in r.get("users", [])}


def submit_reactions(client: WebClient, msg: MessageRef, reactions: dict[str, bool]) -> None:
    """Add reactions to a Slack message."""
    for reaction, enable in reactions.items():
        # Remove colons if user included them (e.g., :thumbsup: -> thumbsup).
        reaction = reaction.strip(":")
        try:
            if enable:
                log(f"Enabling reaction :{reaction}:")
                client.reactions_add(channel=msg.channel, timestamp=msg.timestamp, name=reaction)
            else:
                log(f"Disabling reaction :{reaction}:")
                client.reactions_remove(channel=msg.channel, timestamp=msg.timestamp, name=reaction)
        except SlackApiError as e:
            if e.response["error"] == "already_reacted":
                log(f"Reaction :{reaction}: already enabled")
            elif e.response["error"] == "no_reaction":
                log(f"Reaction :{reaction}: already disabled")
            else:
                log(f"Failed to add/remove reaction :{reaction}: - {e.response["error"]}")


def select_days(day_emoji_map: DayEmojiMap, currently_registered: Container[str] = ()) -> list[str]:
    """Prompt user to select days and return emoji names with checked state."""
    choices = [
        questionary.Choice(f"{emoji_of_name(emoji)}  {day.capitalize()}", value=day, checked=day in currently_registered)
        for day, emoji in day_emoji_map.items()
    ]
    # Compared to .ask(), .unsafe_ask() propagates KeyboardInterrupt instead of returning None.
    return questionary.checkbox("Select days:", choices=choices).unsafe_ask()


def resolve_message(client: WebClient, args) -> ParsedMessage:
    """Resolve message reference and day/emoji map from CLI args."""
    if args.link:
        try:
            ref = parse_slack_url(args.link)
            message_text = fetch_message(client, ref)
            day_emoji_map = parse_emoji_from_message(message_text)
            if not day_emoji_map:
                log("Could not parse any day/emoji pairs from message")
                log(f"Message text: {message_text}")
                sys.exit(1)
            return ParsedMessage(day_emoji_map, Message(ref, message_text))
        except SlackApiError as e:
            log(f"Error fetching message: {e}")
            sys.exit(1)
    else:
        channel = args.channel or os.environ.get("SLACK_CHANNEL")
        if not channel:
            log("Error: provide --link or --channel (or set SLACK_CHANNEL)")
            sys.exit(1)
        log("Searching for message since last Friday with one day/emoji pair for each weekday...")
        try:
            parsed_msg = find_message_in_history(client, channel)
            ts_dt = f"{datetime.fromtimestamp(float(parsed_msg.message.ref.timestamp)):%Y-%m-%d %H:%M}"
            log(f"Found message from {ts_dt} [{parsed_msg.message.ref.channel}/{parsed_msg.message.ref.timestamp}]: {first_line_truncated(parsed_msg)}")
            return parsed_msg
        except SlackApiError as e:
            log(f"Error searching channel: {e}")
            sys.exit(1)


def first_line_truncated(parsed_msg: ParsedMessage, max_len = 32) -> str:
    first_line = parsed_msg.message.text.split("\n", 1)[0]
    if len(first_line) > max_len:
        suffix = " [...]"
        first_line = first_line[:max_len - len(suffix)] + suffix
    return first_line


def run_report(client: WebClient, args):
    msg = resolve_message(client, args)
    user_reactions = fetch_user_reactions(client, msg.message.ref)
    currently_registered = {day for day, emoji in msg.day_emoji_map.items() if emoji in user_reactions}
    days = select_days(msg.day_emoji_map, currently_registered)
    reactions = { emoji : day in days for day, emoji in msg.day_emoji_map.items() }
    submit_reactions(client, msg.message.ref, reactions)


def main():
    parser = argparse.ArgumentParser(description="Slack reaction tool")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--link", help="Slack message link")
    source.add_argument("--channel", help="Channel ID for auto-search (or set SLACK_CHANNEL)")
    args = parser.parse_args()

    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        log("Error: SLACK_USER_TOKEN environment variable not set")
        log("\nTo get a user token:")
        log("1. Create a Slack app at https://api.slack.com/apps")
        log("2. Add 'reactions:read', 'reactions:write', and 'channels:history' to User Token Scopes")
        log("3. Install the app to your workspace")
        log("4. Copy the User OAuth Token (starts with xoxp-)")
        sys.exit(1)

    client = WebClient(token=token)
    run_report(client, args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nAborted.")
        sys.exit(130)
