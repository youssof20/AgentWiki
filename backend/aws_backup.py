"""
Simple S3 backup of Method Cards. Option 1: after each run, upload snapshot to AWS.
"""
from __future__ import annotations

import json
from typing import Any

from utils import getenv, get_logger

logger = get_logger(__name__)


def backup_method_cards_to_s3() -> bool:
    """
    Upload recent Method Cards to S3 as JSON. Returns True on success.
    Env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, AWS_BUCKET_NAME.
    """
    bucket = getenv("AWS_BUCKET_NAME")
    if not bucket:
        logger.debug("S3 backup skipped: no AWS_BUCKET_NAME")
        return False
    if not getenv("AWS_ACCESS_KEY_ID") or not getenv("AWS_SECRET_ACCESS_KEY"):
        logger.debug("S3 backup skipped: no AWS keys")
        return False
    try:
        from memory import get_recent_cards
        cards: list[dict[str, Any]] = get_recent_cards(top_n=200)
        body = json.dumps(cards, indent=2)
    except Exception as e:
        logger.warning("S3 backup: failed to get cards: %s", e)
        return False
    try:
        import boto3
        kwargs = dict(
            aws_access_key_id=getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=getenv("AWS_DEFAULT_REGION") or "us-east-1",
        )
        if getenv("AWS_SESSION_TOKEN"):
            kwargs["aws_session_token"] = getenv("AWS_SESSION_TOKEN")
        s3 = boto3.client("s3", **kwargs)
        s3.put_object(
            Bucket=bucket,
            Key="agentwiki/method_cards_backup.json",
            Body=body,
            ContentType="application/json",
        )
        logger.info("S3 backup: uploaded %d cards to s3://%s/agentwiki/method_cards_backup.json", len(cards), bucket)
        return True
    except Exception as e:
        logger.warning("S3 backup failed: %s", e)
        return False
