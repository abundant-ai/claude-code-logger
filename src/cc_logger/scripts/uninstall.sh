#!/usr/bin/env sh
set -e

CLAUDE_SETTINGS_FILE="$HOME/.claude/settings.json"

# Remove cc-logger hooks from Claude settings.json
remove_hooks() {
  [ -f "$CLAUDE_SETTINGS_FILE" ] || return 0

  if command -v jq >/dev/null 2>&1; then
    # Use jq to remove cc-logger hooks.
    # Keep any hook config whose hooks[].command does NOT contain "cc-logger".
    if UPDATED="$(jq '
      if (type == "object" and (.hooks? | type) == "object") then
        .hooks |= with_entries(
          .value |= (if type == "array" then
            map(select((.hooks? | type) != "array" or ((.hooks | map(.command? // "" | contains("cc-logger")) | any) | not)))
          else . end)
        )
        | .hooks |= with_entries(select((.value | type) != "array" or (.value | length) > 0))
        | if (.hooks | length) == 0 then del(.hooks) else . end
      else .
      end
    ' "$CLAUDE_SETTINGS_FILE" 2>/dev/null)"; then
      echo "$UPDATED" > "$CLAUDE_SETTINGS_FILE"
      echo "Removed cc-logger hooks from $CLAUDE_SETTINGS_FILE"
    else
      echo "WARNING: could not parse $CLAUDE_SETTINGS_FILE with jq; leaving it unchanged." >&2
    fi
  elif command -v python3 >/dev/null 2>&1; then
    python3 << PYEOF
import json
import os

settings_file = "$CLAUDE_SETTINGS_FILE"
if not os.path.exists(settings_file):
    exit(0)

with open(settings_file, 'r') as f:
    try:
        settings = json.load(f)
    except json.JSONDecodeError:
        exit(0)

if 'hooks' not in settings:
    exit(0)

# Remove any hook configs that contain cc-logger commands
for hook_type in list(settings['hooks'].keys()):
    settings['hooks'][hook_type] = [
        config for config in settings['hooks'][hook_type]
        if not any(
            'cc-logger' in h.get('command', '')
            for h in config.get('hooks', [])
        )
    ]
    # Remove empty hook type
    if not settings['hooks'][hook_type]:
        del settings['hooks'][hook_type]

# Remove hooks key if empty
if not settings['hooks']:
    del settings['hooks']

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"Removed cc-logger hooks from {settings_file}")
PYEOF
  else
    echo "WARNING: jq and python3 not found. Please manually remove cc-logger hooks from $CLAUDE_SETTINGS_FILE"
  fi
}

echo "Uninstalling cc-logger..."

# Remove hooks from Claude settings
remove_hooks

# Remove config
rm -rf "$HOME/.config/cclogger"

echo ""
echo "Removed cc-logger configuration."
echo ""
echo "To fully uninstall, run: pip uninstall cc-logger"
echo ""
echo "Note: Your Claude Code logs in ~/.claude/projects/ have been preserved."
