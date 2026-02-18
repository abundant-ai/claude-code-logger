# Claude-Code Logger

> Collect Claude Code logs automatically.

## Install

```bash
pip install cc-logger
cc-logger install
```

After running install, you'll be prompted to authenticate with GitHub (a browser window will open).

## Instructions

Run Claude normally:

```bash
claude "your task"
```

Logs are uploaded automatically when Claude finishes responding and when sessions end.

## Supported Environments

cc-logger supports sessions from:

- **Claude Code CLI** (`claude` command)
- **Claude Code VSCode Extension**
- **Claude Code Desktop App**


## Uninstall

```bash
cc-logger uninstall
```

## Troubleshooting / verify setup

- Verify `cc-logger` is on your PATH (default install location is `~/.local/bin`, or `$XDG_BIN_HOME` if you set it):

```bash
command -v cc-logger
```

- If `cc-logger` is not found, add this to your shell startup file and restart your shell:

```bash
export PATH="${XDG_BIN_HOME:-$HOME/.local/bin}:$PATH"
```

- To manually configure hooks, get the hook path:

```bash
command -v cc-logger-hook
```

Then add this snippet to `~/.claude/settings.json`, replacing `/ABSOLUTE/PATH/TO/cc-logger-hook` with the output above:

<details>
<parameter name="summary">Show hooks configuration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/ABSOLUTE/PATH/TO/cc-logger-hook session-start"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/ABSOLUTE/PATH/TO/cc-logger-hook"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/ABSOLUTE/PATH/TO/cc-logger-hook"
          }
        ]
      }
    ]
  }
}
```

</details>
