# te-presence-reslacktor

A CLI tool to react to office presence posts in Slack. Parses a message containing day/emoji pairs and lets you select which days to react with.

## Setup

1. Install dependencies:
   ```
   uv sync
   ```

2. Create a Slack app at https://api.slack.com/apps

3. Add these scopes under **User Token Scopes**:
   - `reactions:read`
   - `reactions:write`
   - `channels:history` (or `groups:history` for private channels)

4. Install the app to your workspace

5. Set the User OAuth Token (starts with `xoxp-`):
   ```
   export SLACK_USER_TOKEN=xoxp-your-token-here
   ```

## Usage

```
uv run slackspond.py --channel C1234567890
uv run slackspond.py --link "https://yourworkspace.slack.com/archives/C1234567890/p1234567890123456"
```

Without `--link` or `--channel`, falls back to the `SLACK_CHANNEL` environment variable and searches for the latest message since last Friday with one emoji per weekday.

Days you've already reacted to are pre-selected.

### Selection Controls

- **↑/↓** - move between options
- **Space** - toggle selection
- **a** - select all
- **i** - invert selection
- **Enter** - confirm
