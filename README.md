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

### Report presence (default)

Select which days to react to interactively:

```
uv run slackspond.py --channel C1234567890
uv run slackspond.py --channel C1234567890 report
uv run slackspond.py --link "https://yourworkspace.slack.com/archives/C1234567890/p1234567890123456" report
```

Without `--link` or `--channel`, falls back to the `SLACK_CHANNEL` environment variable and searches for the latest message since last Friday with one emoji per weekday.

### Check status

Show which days you've already registered for:

```
uv run slackspond.py --channel C1234567890 status
uv run slackspond.py status
```

### Selection Controls (report)

- **↑/↓** - move between options
- **Space** - toggle selection
- **a** - select all
- **i** - invert selection
- **Enter** - confirm
