import json
import os
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.telegram_auth import validate_init_data
from backend.models import User


class InitDataPayload(BaseModel):
    init_data: str


def _extract_user_id(init_data: str) -> str:
    raw = dict(parse_qsl(init_data.replace("\n", "&"), keep_blank_values=True))
    user_raw = raw.get("user")
    if not user_raw:
        raise HTTPException(status_code=400, detail="init_data missing user")
    try:
        user_obj = json.loads(user_raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid user data in init_data") from exc
    uid = user_obj.get("id")
    if uid is None:
        raise HTTPException(status_code=400, detail="user.id not found in init_data")
    return str(uid)


def resolve_user_from_init_data(init_data: str, db: Session, allow_unsafe: bool = False) -> User:
    """
    Разрешает пользователя из init_data с валидацией подписи.
    
    Args:
        init_data: Telegram WebApp initData string
        db: Database session
        allow_unsafe: Если True, при ошибке валидации подписи извлекает user.id без проверки (только для истории)
    """
    import logging
    auth_logger = logging.getLogger(__name__)
    
    if not init_data:
        auth_logger.warning("[Auth] init_data is required")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="init_data is required")

    # TEST_INIT_DATA работает только в тестовом окружении (CI/smoke)
    test_init = os.getenv("TEST_INIT_DATA")
    env_type = os.getenv("ENV", "").lower()
    is_ci = env_type in ("ci", "test") or os.getenv("ALLOW_TEST_INIT_DATA", "").lower() in ("1", "true", "yes")
    
    if test_init and init_data == test_init and is_ci:
        telegram_id = _extract_user_id(init_data)
    else:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not set")
        try:
            data = validate_init_data(init_data, bot_token)
            user_obj = data.get("user")
            if isinstance(user_obj, str):
                user_obj = json.loads(user_obj)
            if not isinstance(user_obj, dict) or "id" not in user_obj:
                raise HTTPException(status_code=400, detail="Invalid init_data: missing user.id")
            telegram_id = str(user_obj["id"])
        except HTTPException as exc:
            auth_logger.warning("[Auth] validation failed: detail=%s (init_data_len=%s)", exc.detail, len(init_data))
            if allow_unsafe and "signature" in str(exc.detail).lower():
                # Fallback для истории: извлекаем user.id без проверки подписи
                telegram_id = _extract_user_id(init_data)
            else:
                raise

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
