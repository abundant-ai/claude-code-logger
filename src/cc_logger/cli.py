from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cc_logger.auth import main as auth_main


def _find_script(name: str) -> Path | None:
    """Find a script in the scripts directory."""
    pkg_dir = Path(__file__).resolve().parent
    # Check package scripts directory (for pip install)
    script_path = pkg_dir / "scripts" / name
    if script_path.exists():
        return script_path
    # Check repo scripts directory (for editable install)
    script_path = pkg_dir.parent.parent / "scripts" / name
    if script_path.exists():
        return script_path
    return None


def _install() -> int:
    """Run the install script."""
    script_path = _find_script("install.sh")
    if not script_path:
        print("ERROR: Could not locate install script.", file=sys.stderr)
        print("Please run: sh scripts/install.sh", file=sys.stderr)
        return 1

    try:
        result = subprocess.run(["sh", str(script_path)], check=False)
        return result.returncode
    except Exception as e:
        print(f"ERROR: Failed to run install script: {e}", file=sys.stderr)
        return 1


def _uninstall() -> int:
    """Run the uninstall script."""
    script_path = _find_script("uninstall.sh")
    if not script_path:
        print("ERROR: Could not locate uninstall script.", file=sys.stderr)
        print("Please run: sh scripts/uninstall.sh", file=sys.stderr)
        return 1

    try:
        result = subprocess.run(["sh", str(script_path)], check=False)
        return result.returncode
    except Exception as e:
        print(f"ERROR: Failed to run uninstall script: {e}", file=sys.stderr)
        return 1


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help"}:
        print(
            "usage:\n"
            "  cc-logger install     Set up hooks and authenticate\n"
            "  cc-logger uninstall   Remove cc-logger completely\n"
            "  cc-logger auth        Authenticate with GitHub\n"
        )
        return 0

    cmd, rest = argv[0], argv[1:]

    if cmd == "install":
        return _install()
    elif cmd == "uninstall":
        return _uninstall()
    elif cmd == "auth":
        return int(auth_main(rest))

    print("ERROR: unknown command.\nRun: cc-logger --help\n", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
