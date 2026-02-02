# te-presence-reslacktor

A CLI tool to react to office presence posts in Slack. Parses a message containing day/emoji pairs and lets you select which days to react with.

## Setup

1. Install dependencies:
   ```
   uv sync
   ```

2. Create a Slack app at https://api.slack.com/apps

3. Add these scopes under **User Token Scopes**:
   - `reactions:write`
   - `channels:history` (or `groups:history` for private channels)

4. Install the app to your workspace

5. Set the User OAuth Token (starts with `xoxp-`):
   ```
   export SLACK_USER_TOKEN=xoxp-your-token-here
   ```

## Usage

```
uv run slackspond.py "https://yourworkspace.slack.com/archives/C1234567890/p1234567890123456"
```

The tool will:
1. Fetch the message
2. Parse lines containing a weekday and an emoji (e.g., `:red_circle: Monday`)
3. Present an interactive selection UI
4. Submit the selected reactions

### Selection Controls

- **↑/↓** - move between options
- **Space** - toggle selection
- **a** - select all
- **i** - invert selection
- **Enter** - confirm
