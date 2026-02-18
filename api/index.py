from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Any, Optional

import boto3
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return default


def _now() -> int:
    return int(time.time())


def _s3_bucket() -> str:
    return str(_env("S3_BUCKET", "cc-sessions"))


def _aws_region() -> Optional[str]:
    return _env("AWS_REGION")


def _assume_role_arn() -> str:
    arn = _env("STS_ASSUME_ROLE_ARN")
    if not arn:
        raise RuntimeError("STS_ASSUME_ROLE_ARN is required")
    return arn


def _github_user_from_token(token: str) -> str:
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cc-logger-server",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=401, detail="invalid github token")
        raise HTTPException(status_code=502, detail=f"github api error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"github api error: {e}")

    login = data.get("login")
    if not isinstance(login, str) or not login.strip():
        raise HTTPException(status_code=502, detail="github did not return login")
    return login.strip()


def _session_policy_for_user(*, user_id: str, bucket: str) -> str:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "WriteOnlyToUserPrefix",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:AbortMultipartUpload",
                ],
                "Resource": f"arn:aws:s3:::{bucket}/{user_id}/*",
            },
            {
                "Sid": "MultipartOps",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucketMultipartUploads",
                    "s3:ListMultipartUploadParts",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket}",
                    f"arn:aws:s3:::{bucket}/{user_id}/*",
                ],
            },
        ],
    }
    return json.dumps(policy)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sts/issue")
def sts_issue(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing Authorization")
    token = authorization.split(" ", 1)[1].strip()

    user_id = _github_user_from_token(token)
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,64}", user_id):
        raise HTTPException(status_code=400, detail="invalid github username")

    bucket = _s3_bucket()
    role_arn = _assume_role_arn()
    region = _aws_region()

    sess_name = f"cc-logger-{user_id}-{_now()}"
    sts = boto3.client("sts", region_name=region)
    resp = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=sess_name[:64],
        DurationSeconds=3600,
        Policy=_session_policy_for_user(user_id=user_id, bucket=bucket),
    )
    creds = resp.get("Credentials") or {}
    return {
        "access_key_id": creds.get("AccessKeyId"),
        "secret_access_key": creds.get("SecretAccessKey"),
        "session_token": creds.get("SessionToken"),
        "expiration": creds.get("Expiration").isoformat().replace("+00:00", "Z") if creds.get("Expiration") else None,
        "bucket": bucket,
        "prefix": f"{user_id}/",
    }
