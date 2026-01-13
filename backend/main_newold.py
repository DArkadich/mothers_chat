import os
import uuid
import json
from datetime import datetime
from typing import List, Literal, Optional, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.core.limiter import limiter
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    or_,
)
from sqlalchemy import Integer
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from openai import OpenAI
from backend.app.ai.client import OpenAIClient

# =========================
# Настройки и инициализация
# =========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # В отсутствии переменной окружения используем sqlite в памяти для локального импорта/тестов.
    # В продакшне через docker-compose передаётся Postgres DATABASE_URL.
    "sqlite:///:memory:",
)

def env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1-mini")
ENABLE_FAKE_OPENAI = env_bool("ENABLE_FAKE_OPENAI", "0")

# Проверка: нужен либо API ключ, либо fake режим
if not OPENAI_API_KEY and not ENABLE_FAKE_OPENAI:
    raise RuntimeError("OpenAI API key is not set")

# Инициализация клиента OpenAI
openai_client = None
if OPENAI_API_KEY and not ENABLE_FAKE_OPENAI:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    except Exception:
        openai_client = None

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

async def get_current_user_optional(
    request: Request = None,
) -> Optional[Any]:
    """
    Optional dependency. В тестах переопределяется.
    Сейчас возвращаем None (по умолчанию неавторизован).
    """
    return None

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========
# RATE LIMITING
# ==========

async def rate_limit_dep(
    request: Request,
    db=Depends(get_db),  # без аннотации Session
    current_user: Optional[Any] = Depends(get_current_user_optional),
) -> None:
    # твоя логика лимитов
    key = request.client.host if request.client else "anon"
    if not limiter.allowed(key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    return None


# ==========
# МОДЕЛИ БД
# ==========

from .models import Base, User, Assistant, ChatSession, ChatMessage



# В реальности структуры мигрируются через Alembic.
# Здесь create_all можно оставить закомментированным,
# если Alembic уже настроен под эти модели.
# Base.metadata.create_all(bind=engine)


# ==========
# СХЕМЫ API
# ==========

class ChatSessionCreate(BaseModel):
    assistant_slug: str = Field(..., examples=["newborn_sleep"])
    telegram_id: Optional[str] = Field(None, examples=["123456789"])
    init_data: Optional[str] = Field(None, description="Telegram WebApp initData string. Server will validate signature and extract user.id as telegram_id.")


class ChatSessionResponse(BaseModel):
    session_id: int


class ChatSendRequest(BaseModel):
    session_id: int
    assistant_slug: str
    message: str


class ChatMessageDTO(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str


class ChatSendResponse(BaseModel):
    reply: str
    messages: List[ChatMessageDTO]


# ==============
# ВСПОМОГАТЕЛЬНОЕ
# ==============

def get_or_create_user_by_telegram(
    db: Session,
    telegram_id: str,
) -> User:
    # Avoid selecting columns that may not exist in older DB schema (e.g., 'profile')
    from sqlalchemy import inspect

    inspector = inspect(engine)
    cols = [c['name'] for c in inspector.get_columns('users')]

    select_cols = [User.id, User.telegram_id]
    if 'profile' in cols:
        select_cols.append(User.profile)

    # Use explicit SELECT to avoid any ORM automatic column expansion
    from sqlalchemy import select

    stmt = select(*select_cols).where(User.telegram_id == telegram_id).limit(1)
    result = db.execute(stmt).first()
    if result:
        from types import SimpleNamespace

        # result can be Row, map to expected attributes
        values = dict(result._mapping)
        return SimpleNamespace(
            id=values.get('id') or values.get('users_id') or values.get('users_id'),
            telegram_id=values.get('telegram_id') or values.get('users_telegram_id') or values.get('telegram_id'),
            profile=values.get('profile'),
        )

    # create user — only include profile if column exists
    if 'profile' in cols:
        user = User(telegram_id=telegram_id, profile={})
    else:
        user = User(telegram_id=telegram_id)

    db.add(user)
    db.commit()
    # If 'profile' column is absent, avoid refresh() because it will attempt to SELECT it.
    if 'profile' in cols:
        db.refresh(user)
    return user


# ==========
# ПРИЛОЖЕНИЕ
# ==========

app = FastAPI(title="Mamino Backend")

# CORS — миниапп грузится с твоего домена, так что справа можно будет зажать конкретный origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде лучше заменить на конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================
# РОУТЫ ЧАТА С АССИСТЕНТОМ
# =====================

@app.post("/api/chat/session", response_model=ChatSessionResponse)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """
    Создаёт новую сессию чата для заданного ассистента и telegram_id.

    Поддерживает два варианта передачи идентификатора пользователя:
    - напрямую `telegram_id` (для простоты локальной разработки),
    - `init_data` от Telegram WebApp — предпочтительно и безопасно (сервер верифицирует подпись).
    """
    # 1) ассистент должен существовать
    assistant = db.query(Assistant).filter(
        or_(Assistant.code == payload.assistant_slug, Assistant.slug == payload.assistant_slug)
    ).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # 2) определить telegram_id
    telegram_id: Optional[str] = None

    if payload.init_data:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not set")

        from backend.core.telegram_auth import validate_init_data

        # validate_init_data возвращает dict с данными
        data = validate_init_data(payload.init_data, bot_token)

        user_obj = data.get("user")
        if isinstance(user_obj, str):
            # иногда user приходит JSON-строкой
            user_obj = json.loads(user_obj)

        if not isinstance(user_obj, dict) or "id" not in user_obj:
            raise HTTPException(status_code=400, detail="Invalid init_data: missing user.id")

        telegram_id = str(user_obj["id"])

    elif payload.telegram_id:
        telegram_id = str(payload.telegram_id)

    else:
        raise HTTPException(status_code=400, detail="telegram_id or init_data is required")

    # 3) найти/создать пользователя
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4) создать сессию
    sess = ChatSession(user_id=user.id, assistant_id=assistant.id)
    db.add(sess)
    db.commit()
    db.refresh(sess)

    return {"session_id": sess.id}


@app.post("/api/chat/send", response_model=None, dependencies=[Depends(rate_limit_dep)])
def send_chat_message(
    payload: ChatSendRequest,
    db=Depends(get_db),  # без Session
    current_user: Any = Depends(get_current_user_optional),
):
    # ассистент
    assistant = db.query(Assistant).filter(
        or_(Assistant.code == payload.assistant_slug, Assistant.slug == payload.assistant_slug)
    ).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # сессия
    sess = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # пользователь сессии
    session_user = db.query(User).filter(User.id == sess.user_id).first()
    if not session_user:
        raise HTTPException(status_code=500, detail="Session user not found")

    # optional auth check (ровно как ожидает тест)
    if current_user is not None:
        cur_tid = str(getattr(current_user, "telegram_id", ""))
        if cur_tid != str(session_user.telegram_id):
            raise HTTPException(status_code=403, detail="Forbidden: telegram_id mismatch")

    # Получаем историю сообщений (без system_prompt)
    history_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sess.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
        if msg.role in ("user", "assistant")
    ]
    
    # Добавляем текущее сообщение пользователя
    history.append({"role": "user", "content": payload.message})
    
    # Сохраняем сообщение пользователя в БД
    user_msg = ChatMessage(
        session_id=sess.id,
        role="user",
        content=payload.message
    )
    db.add(user_msg)
    db.commit()

    # Переключатель fake / real (одна точка входа)
    if ENABLE_FAKE_OPENAI:
        FAKE_REPLY = os.getenv("FAKE_REPLY", "Hello from fake model")
        reply = FAKE_REPLY
    else:
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI client is not configured")
        reply = openai_client.chat(
            system_prompt=assistant.system_prompt,
            messages=history,
        )
    
    # Сохраняем ответ ассистента в БД
    assistant_msg = ChatMessage(
        session_id=sess.id,
        role="assistant",
        content=reply
    )
    db.add(assistant_msg)
    db.commit()
    
    # Формируем ответ с историей (включая новый ответ)
    messages = history + [{"role": "assistant", "content": reply}]
    
    return {"reply": reply, "messages": messages}


# Простейший ping, на всякий случай
@app.get("/health", dependencies=[Depends(rate_limit_dep)])
def healthcheck():
  return {"status": "ok"}
