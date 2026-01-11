import os
import hmac
import hashlib
import json
from typing import Dict, Any
from urllib.parse import parse_qsl

from fastapi import HTTPException, status


def _parse_init_data(init_data: str) -> Dict[str, str]:
    """Parse init_data string which may be joined by '\n' or '&' into a dict."""
    normalized = init_data.replace("\n", "&")
    pairs = parse_qsl(normalized, keep_blank_values=True)
    return dict(pairs)


def validate_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """Validate Telegram WebApp initData and return parsed data dict.
    
    Returns dict with keys like 'user', 'auth_date', etc.
    The 'user' key contains a dict with 'id' key.
    """
    if not bot_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server misconfiguration: TELEGRAM_BOT_TOKEN not set")

    data = _parse_init_data(init_data)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="initData missing hash")

    # Build data_check_string
    data_check_list = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_list)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_obj = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)
    computed_hash = hmac_obj.hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid initData signature")

    # Parse user field if it's a JSON string
    if "user" in data and isinstance(data["user"], str):
        try:
            data["user"] = json.loads(data["user"])
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user data in initData")

    return data


def validate_init_data_and_get_user_id(init_data: str, bot_token: str) -> str:
    """Validate Telegram WebApp initData and return user.id as str.

    Follows Telegram docs: compute HMAC-SHA256 with secret = SHA256(bot_token)
    over sorted key=value lines (excluding hash)."""
    if not bot_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server misconfiguration: TELEGRAM_BOT_TOKEN not set")

    data = _parse_init_data(init_data)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="initData missing hash")

    # Build data_check_string
    data_check_list = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_list)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_obj = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)
    computed_hash = hmac_obj.hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid initData signature")

    # parse user field (it's a JSON string)
    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="initData missing user")

    try:
        user = json.loads(user_raw)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user data in initData")

    uid = user.get("id")
    if uid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user.id not found in initData")

    return str(uid)
