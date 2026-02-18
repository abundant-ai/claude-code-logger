from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3

from cc_logger.auth import _api_base_url, _http_json, _load_github_token


def _s3_client_from_sts(sts_payload: dict[str, Any]) -> Any:
    return boto3.client(
        "s3",
        aws_access_key_id=sts_payload.get("access_key_id"),
        aws_secret_access_key=sts_payload.get("secret_access_key"),
        aws_session_token=sts_payload.get("session_token"),
    )

def _sts_payload() -> dict[str, Any]:
    base = _api_base_url()
    token = _load_github_token()
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("missing github_token (run: cc-logger auth)")
    sts = _http_json("POST", f"{base}/sts/issue", payload={}, headers={"Authorization": f"Bearer {token.strip()}"})
    return sts


def upload_transcript(*, transcript_path: Path) -> None:
    """Upload a single transcript and its subagents to S3."""
    transcript_file = transcript_path.expanduser().resolve()
    if not transcript_file.exists() or not transcript_file.is_file():
        raise RuntimeError(f"transcript not found: {transcript_file}")

    sts = _sts_payload()
    bucket = sts.get("bucket")
    prefix = sts.get("prefix")
    if not isinstance(bucket, str) or not bucket.strip():
        raise RuntimeError("bad sts response: bucket")
    if not isinstance(prefix, str):
        prefix = ""
    prefix = prefix.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    s3 = _s3_client_from_sts(sts)

    # Determine the projects root (two levels up from transcript)
    project_dir = transcript_file.parent
    projects_root = project_dir.parent

    # Upload main transcript
    rel = transcript_file.relative_to(projects_root).as_posix()
    s3.upload_file(str(transcript_file), bucket, f"{prefix}{rel}")

    # Upload entire session directory if it exists (subagents, tool-results, context, etc.)
    session_id = transcript_file.stem
    session_dir = project_dir / session_id
    if session_dir.exists() and session_dir.is_dir():
        for p in session_dir.rglob("*"):
            if not p.is_file():
                continue
            rel2 = p.relative_to(projects_root).as_posix()
            s3.upload_file(str(p), bucket, f"{prefix}{rel2}")
