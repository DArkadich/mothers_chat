import os
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from backend.core.limiter import rate_limit_dep
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

# =========================
# Настройки и инициализация
# =========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # В отсутствии переменной окружения используем sqlite в памяти для локального импорта/тестов.
    # В продакшне через docker-compose передаётся Postgres DATABASE_URL.
    "sqlite:///:memory:",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1-mini")  # можно поменять на то, что вы выбрали

# Инициализация клиента OpenAI: не падаем при импорте — если ключ не задан или
# инициализация не удалась, оставляем `openai_client = None` и проверяем при вызове.
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        # Если инициализация не удалась (несовместимость библиотек в окружении),
        # оставляем клиента пустым и обработаем это в рантайме.
        openai_client = None

# Режим разработки: при необходимости можно включить fake OpenAI для smoke-тестов
# (полезно на dev/CI, когда реальный ключ недоступен).
if os.getenv("ENABLE_FAKE_OPENAI", "0") == "1":
    class FakeOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(model, messages):
                    class MessageObj:
                        content = "Hello from fake model"

                    class ChoiceObj:
                        message = MessageObj()

                    class CompletionObj:
                        choices = [ChoiceObj()]

                    return CompletionObj()

    openai_client = FakeOpenAI()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    # Inspect database schema to avoid referencing non-existing columns (e.g., old migrations may not have 'slug')
    from sqlalchemy import inspect
    from backend.core.telegram_auth import validate_init_data_and_get_user_id

    inspector = inspect(engine)
    cols = [c['name'] for c in inspector.get_columns('assistants')]

    filters = []
    if 'slug' in cols:
        filters.append(Assistant.slug == payload.assistant_slug)
    if 'code' in cols:
        filters.append(Assistant.code == payload.assistant_slug)

    if not filters:
        # unexpected schema: fallback to searching by code only in ORM (may still fail)
        filters.append(Assistant.code == payload.assistant_slug)

    # Select explicit columns to avoid selecting 'slug' when it doesn't exist in DB
    row = (
        db.query(Assistant.id, Assistant.code, Assistant.title, Assistant.system_prompt, Assistant.description)
        .filter(or_(*filters))
        .first()
    )
    if not row:
        assistant = None
    else:
        # lightweight object emulating needed fields of Assistant
        from types import SimpleNamespace

        assistant = SimpleNamespace(
            id=row.id,
            code=row.code,
            title=row.title,
            system_prompt=row.system_prompt,
            description=row.description,
        )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ассистент не найден",
        )

    # Prefer init_data if provided (Telegram WebApp), otherwise fall back to plain telegram_id
    telegram_id = None
    if payload.init_data:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_id = validate_init_data_and_get_user_id(payload.init_data, bot_token)
    elif payload.telegram_id:
        telegram_id = payload.telegram_id

    if not telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="telegram_id or init_data is required")

    user = get_or_create_user_by_telegram(db, telegram_id)

    session = ChatSession(
        user_id=user.id,
        assistant_id=assistant.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Сохраним промт ассистента как системное сообщение,
    # чтобы в истории было видно, с какой инструкцией он работает.
    system_msg = ChatMessage(
        session_id=session.id,
        role="system",
        content=assistant.system_prompt,
    )
    db.add(system_msg)
    db.commit()

    return ChatSessionResponse(session_id=session.id)


@app.post("/api/chat/send", response_model=ChatSendResponse, dependencies=[Depends(rate_limit_dep)])
def send_chat_message(
    payload: ChatSendRequest,
    db: Session = Depends(get_db),
):
    """
    Принимает сообщение пользователя, обращается к OpenAI с системным промтом ассистента
    и всей историей диалога, сохраняет ответ и возвращает его.
    """
    session: Optional[ChatSession] = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    # Fetch assistant by id but select explicit columns present in DB to avoid missing 'slug' errors
    from sqlalchemy import inspect
    inspector = inspect(engine)
    assistant_cols = [c['name'] for c in inspector.get_columns('assistants')]

    select_cols = [Assistant.id, Assistant.code, Assistant.title, Assistant.system_prompt, Assistant.description]
    # Avoid selecting slug if it's not present
    if 'slug' in assistant_cols:
        select_cols.insert(1, Assistant.slug)

    row = db.query(*select_cols).filter(Assistant.id == session.assistant_id).first()
    if not row:
        assistant = None
    else:
        from types import SimpleNamespace
        assistant = SimpleNamespace(
            id=row.id,
            code=getattr(row, 'code', None),
            slug=getattr(row, 'slug', None),
            title=row.title,
            system_prompt=row.system_prompt,
            description=row.description,
        )

    if not assistant or (getattr(assistant, 'slug', None) != payload.assistant_slug and getattr(assistant, 'code', None) != payload.assistant_slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ассистент не соответствует сессии",
        )

    # Сохраняем сообщение пользователя
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # История сообщений в этой сессии
    messages_orm: List[ChatMessage] = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    openai_messages = []

    # системный промт ассистента — отправляем как system
    openai_messages.append(
        {"role": "system", "content": assistant.system_prompt}
    )

    # все сообщения user/assistant
    for msg in messages_orm:
        if msg.role == "system":
            continue
        openai_messages.append(
            {
                "role": msg.role,
                "content": msg.content,
            }
        )

    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI client is not configured",
        )

    try:
        completion = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка обращения к OpenAI: {e}",
        )

    reply_text = completion.choices[0].message.content

    # Сохраняем ответ ассистента
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Формируем ответ клиенту
    updated_messages: List[ChatMessage] = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    dto_messages: List[ChatMessageDTO] = [
        ChatMessageDTO(
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in updated_messages
    ]

    return ChatSendResponse(
        reply=reply_text,
        messages=dto_messages,
    )


# Простейший ping, на всякий случай
@app.get("/health", dependencies=[Depends(rate_limit_dep)])
def healthcheck():
  return {"status": "ok"}
