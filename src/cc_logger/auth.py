from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Optional


def _config_path() -> Path:
    return Path.home() / ".config" / "cclogger" / "config.json"


def _load_config() -> dict[str, Any]:
    p = _config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(cfg: dict[str, Any]) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass


def _api_base_url() -> str:
    return "https://claude-code-logger.vercel.app"


def _http_json(method: str, url: str, payload: Optional[dict[str, Any]] = None, headers: Optional[dict[str, str]] = None) -> Any:
    body = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8", errors="replace")) if data else {}
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error calling {url}: {e}") from e
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {raw}") from e


def _load_github_token() -> Optional[str]:
    cfg = _load_config()
    v = cfg.get("github_token")
    return v.strip() if isinstance(v, str) and v.strip() else None


# GitHub OAuth App Client ID (Device Flow enabled)
_GITHUB_CLIENT_ID = "Ov23li1uY6U6Blcj89FW"


def _github_client_id() -> str:
    """Get GitHub client ID."""
    return _GITHUB_CLIENT_ID


def _github_device_start(client_id: str) -> dict[str, Any]:
    """POST to GitHub's device code endpoint."""
    body = urllib.parse.urlencode({"client_id": client_id, "scope": "read:user"}).encode("utf-8")
    req = urllib.request.Request(
        "https://github.com/login/device/code",
        data=body,
        method="POST",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _github_device_poll(client_id: str, device_code: str) -> dict[str, Any]:
    """Poll GitHub's token endpoint for device flow completion."""
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=body,
        method="POST",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _github_get_user(token: str) -> str:
    """Get GitHub username from access token."""
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cc-logger",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    login = data.get("login")
    if not isinstance(login, str) or not login.strip():
        raise RuntimeError("GitHub API did not return a login")
    return login.strip()


def _auth_login(argv: list[str]) -> int:
    cfg = _load_config()

    # Check if already logged in with a valid token
    token = _load_github_token()
    if isinstance(token, str) and token.strip():
        try:
            user_id = _github_get_user(token)
            print(f"Already logged in as: {user_id}")
            return 0
        except Exception:
            print("Existing token is invalid, re-authenticating...")
            cfg.pop("github_token", None)
            _save_config(cfg)

    client_id = _github_client_id()

    # Start GitHub Device Flow
    try:
        start = _github_device_start(client_id)
    except Exception as e:
        print(f"ERROR: failed to start device flow: {e}", file=sys.stderr)
        return 2

    device_code = start.get("device_code")
    user_code = start.get("user_code")
    verification_uri = start.get("verification_uri")
    expires_in = int(start.get("expires_in") or 900)
    interval = int(start.get("interval") or 5)

    if not device_code or not user_code or not verification_uri:
        print("ERROR: unexpected response from GitHub device flow", file=sys.stderr)
        return 2

    print(f"Open this URL and enter the code: {user_code}")
    print(f"  {verification_uri}")
    try:
        webbrowser.open(verification_uri, new=2)
    except Exception:
        pass

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        try:
            resp = _github_device_poll(client_id, device_code)
        except Exception:
            continue

        error = resp.get("error")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval = int(resp.get("interval") or interval + 5)
            continue
        elif error == "expired_token":
            print("ERROR: device code expired", file=sys.stderr)
            return 2
        elif error == "access_denied":
            print("ERROR: authorization denied by user", file=sys.stderr)
            return 2
        elif error:
            print(f"ERROR: {error}: {resp.get('error_description', '')}", file=sys.stderr)
            return 2

        access_token = resp.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            continue

        # Get GitHub username for display
        try:
            user_id = _github_get_user(access_token)
        except Exception as e:
            print(f"ERROR: failed to get GitHub user: {e}", file=sys.stderr)
            return 2

        # Only save the token, not user_id (we can fetch it when needed)
        cfg["github_token"] = access_token
        _save_config(cfg)
        print(f"Logged in as: {user_id}")
        return 0

    print("ERROR: timed out waiting for authorization", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="cc-logger auth", add_help=True)
    p.parse_args(argv)
    return _auth_login(argv)
