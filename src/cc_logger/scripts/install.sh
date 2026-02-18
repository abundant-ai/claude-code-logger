#!/usr/bin/env sh
set -e

CLAUDE_SETTINGS_DIR="$HOME/.claude"
CLAUDE_SETTINGS_FILE="$CLAUDE_SETTINGS_DIR/settings.json"

# Configure Claude Code hooks in settings.json
# This is the PRIMARY integration method that survives Claude updates
configure_hooks() {
  mkdir -p "$CLAUDE_SETTINGS_DIR"

  # Use absolute path to cc-logger-hook to avoid PATH issues in hook execution context
  HOOK_BIN="$(command -v cc-logger-hook)"
  if [ -z "$HOOK_BIN" ]; then
    echo "ERROR: cc-logger-hook not found on PATH."
    echo "Make sure cc-logger is installed: pip install cc-logger"
    exit 1
  fi

  if command -v jq >/dev/null 2>&1; then
    # Use jq to build and merge hooks (avoids shell escaping issues)
    if [ -f "$CLAUDE_SETTINGS_FILE" ]; then
      # Append to existing hooks, removing any old cc-logger entries first
      jq --arg hook_bin "$HOOK_BIN" '
        .hooks.SessionStart = (
          ((.hooks.SessionStart // []) | map(select((.hooks // []) | all(.command // "" | contains("cc-logger") | not))))
          + [{"matcher": "", "hooks": [{"type": "command", "command": ($hook_bin + " session-start")}]}]
        ) |
        .hooks.Stop = (
          ((.hooks.Stop // []) | map(select((.hooks // []) | all(.command // "" | contains("cc-logger") | not))))
          + [{"matcher": "", "hooks": [{"type": "command", "command": $hook_bin}]}]
        ) |
        .hooks.SessionEnd = (
          ((.hooks.SessionEnd // []) | map(select((.hooks // []) | all(.command // "" | contains("cc-logger") | not))))
          + [{"matcher": "", "hooks": [{"type": "command", "command": $hook_bin}]}]
        )
      ' "$CLAUDE_SETTINGS_FILE" > "$CLAUDE_SETTINGS_FILE.tmp" && mv "$CLAUDE_SETTINGS_FILE.tmp" "$CLAUDE_SETTINGS_FILE"
    else
      jq -n --arg hook_bin "$HOOK_BIN" '
        {
          hooks: {
            SessionStart: [{"matcher": "", "hooks": [{"type": "command", "command": ($hook_bin + " session-start")}]}],
            Stop: [{"matcher": "", "hooks": [{"type": "command", "command": $hook_bin}]}],
            SessionEnd: [{"matcher": "", "hooks": [{"type": "command", "command": $hook_bin}]}]
          }
        }
      ' > "$CLAUDE_SETTINGS_FILE"
    fi
    echo "Configured Claude Code hooks in $CLAUDE_SETTINGS_FILE"
  elif command -v python3 >/dev/null 2>&1; then
    # Fall back to Python for JSON manipulation
    python3 << PYEOF
import json
import os

settings_file = "$CLAUDE_SETTINGS_FILE"
hook_bin = "$HOOK_BIN"

hooks_config = {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": f"{hook_bin} session-start"}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": f"{hook_bin}"}]}],
    "SessionEnd": [{"matcher": "", "hooks": [{"type": "command", "command": f"{hook_bin}"}]}]
}

if os.path.exists(settings_file):
    with open(settings_file, 'r') as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
else:
    settings = {}

# Add hooks (append to existing, removing old cc-logger entries first)
if 'hooks' not in settings:
    settings['hooks'] = {}

for hook_type, hook_config in hooks_config.items():
    # Get existing configs
    existing = settings['hooks'].get(hook_type, [])
    # Filter out any cc-logger configs
    filtered = [
        config for config in existing
        if not any('cc-logger' in h.get('command', '') for h in config.get('hooks', []))
    ]
    # Append our config
    settings['hooks'][hook_type] = filtered + [hook_config]

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"Configured Claude Code hooks in {settings_file}")
PYEOF
  else
    # No jq or python3 available
    echo "WARNING: jq and python3 not found."
    echo "Please manually add hooks to $CLAUDE_SETTINGS_FILE"
    echo "See: https://github.com/abundant-ai/cc-logger for configuration"
  fi
}

# cc-logger is already installed (this script is running via the installed CLI)
echo "Configuring cc-logger..."
echo ""
configure_hooks

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""
echo "cc-logger is configured via Claude Code hooks."
echo ""
echo "Authenticating (a browser window may open)..."
if cc-logger auth; then
  echo ""
  echo "Done. Run Claude normally (CLI/VSCode/Desktop) and logs will upload automatically."
else
  echo ""
  echo "ERROR: authentication failed."
  echo "Re-run to retry: cc-logger install"
  exit 1
fi
