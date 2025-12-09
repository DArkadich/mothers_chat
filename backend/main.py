import os
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from openai import OpenAI

# =========================
# Настройки и инициализация
# =========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@motherschat_db:5432/motherschat",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1-mini"  # можно поменять на то, что вы выбрали

if not OPENAI_API_KEY:
    raise RuntimeError("Не задан OPENAI_API_KEY в окружении")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

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

class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(String(64), unique=True, nullable=False, index=True)
    # сюда потом можно складывать имя, возраст детей и т.д.
    profile = Column(JSON, nullable=True)

    chat_sessions = relationship("ChatSession", back_populates="user")


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="assistant")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assistant_id = Column(PG_UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    assistant = relationship("Assistant", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = Column(String(16), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)

    session = relationship("ChatSession", back_populates="messages")


# В реальности структуры мигрируются через Alembic.
# Здесь create_all можно оставить закомментированным,
# если Alembic уже настроен под эти модели.
# Base.metadata.create_all(bind=engine)


# ==========
# СХЕМЫ API
# ==========

class ChatSessionCreate(BaseModel):
    assistant_slug: str = Field(..., examples=["newborn_sleep"])
    telegram_id: str = Field(..., examples=["123456789"])


class ChatSessionResponse(BaseModel):
    session_id: uuid.UUID


class ChatSendRequest(BaseModel):
    session_id: uuid.UUID
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
    user: Optional[User] = (
        db.query(User).filter(User.telegram_id == telegram_id).first()
    )
    if user:
        return user

    user = User(telegram_id=telegram_id, profile={})
    db.add(user)
    db.commit()
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
    """
    assistant: Optional[Assistant] = (
        db.query(Assistant)
        .filter(Assistant.slug == payload.assistant_slug)
        .first()
    )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ассистент не найден",
        )

    user = get_or_create_user_by_telegram(db, payload.telegram_id)

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


@app.post("/api/chat/send", response_model=ChatSendResponse)
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

    assistant: Optional[Assistant] = (
        db.query(Assistant)
        .filter(Assistant.id == session.assistant_id)
        .first()
    )
    if not assistant or assistant.slug != payload.assistant_slug:
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
@app.get("/health")
def healthcheck():
  return {"status": "ok"}
