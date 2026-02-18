"""
Claude Code hook handlers for cc-logger.

These handlers are invoked by Claude Code via the hooks configuration in ~/.claude/settings.json.

Hooks:
  - SessionStart: Shows status message when session starts
  - Stop: Triggers upload when Claude finishes responding
  - SessionEnd: Triggers final upload when session ends
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from cc_logger.uploader import upload_transcript


def _read_hook_input() -> dict:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def _upload_from_hook() -> int:
    """Upload transcript from hook input."""
    hook_input = _read_hook_input()
    transcript_path = hook_input.get("transcript_path")

    if not transcript_path:
        print("WARNING: No transcript_path in hook input", file=sys.stderr)
        return 1

    try:
        upload_transcript(transcript_path=Path(transcript_path))
        return 0
    except Exception as e:
        print(f"WARNING: upload failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Internal entry point invoked by Claude Code hooks."""
    if len(sys.argv) > 1 and sys.argv[1] == "session-start":
        print('{"systemMessage": "[cc-logger] Session logging active."}')
        return 0
    return _upload_from_hook()
