from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON

# ----------------------------
# Database setup
# ----------------------------

DATABASE_URL = "postgresql+psycopg2://motherschat:motherschat_password@db:5432/motherschat"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ----------------------------
# Models
# ----------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    base_model = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    extra_config = Column(JSON, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)        # user | assistant | system
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# создаём недостающие таблицы (users, chat_sessions, chat_messages)
Base.metadata.create_all(bind=engine)

# ----------------------------
# Pydantic Schemas
# ----------------------------

class ChatSessionCreate(BaseModel):
    assistant_slug: str
    telegram_id: str


class ChatSessionResponse(BaseModel):
    session_id: str


class ChatSendRequest(BaseModel):
    session_id: str
    assistant_slug: str
    message: str


class ChatMessageDTO(BaseModel):
    role: str
    content: str
    created_at: str


class ChatSendResponse(BaseModel):
    reply: str
    messages: List[ChatMessageDTO]


class ChatHistoryRequest(BaseModel):
    session_id: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageDTO]

# ----------------------------
# DB dependency
# ----------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# OpenAI client
# ----------------------------

from openai import OpenAI

OPENAI_MODEL = "gpt-4o-mini"
openai_client = OpenAI()

# ----------------------------
# FastAPI init
# ----------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Routes
# ----------------------------

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/chat/session", response_model=ChatSessionResponse)
def create_chat_session(payload: ChatSessionCreate, db: Session = Depends(get_db)):
    """Создание (или получение существующей) чат-сессии по assistant_slug (= assistants.code)."""

    assistant = (
        db.query(Assistant)
        .filter(Assistant.code == payload.assistant_slug)
        .first()
    )
    if not assistant:
        raise HTTPException(status_code=404, detail="Ассистент не найден")

    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        user = User(telegram_id=payload.telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # ВАЖНО: если сессия уже существует — возвращаем её (чтобы история сохранялась)
    existing = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.assistant_id == assistant.id)
        .order_by(ChatSession.created_at.desc())
        .first()
    )
    if existing:
        return ChatSessionResponse(session_id=existing.id)

    session = ChatSession(
        user_id=user.id,
        assistant_id=assistant.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Добавляем системное сообщение с промтом только для новой сессии
    sys_msg = ChatMessage(
        session_id=session.id,
        role="system",
        content=assistant.system_prompt,
    )
    db.add(sys_msg)
    db.commit()

    return ChatSessionResponse(session_id=session.id)


@app.post("/chat/history", response_model=ChatHistoryResponse)
def chat_history(payload: ChatHistoryRequest, db: Session = Depends(get_db)):
    """Получение истории сообщений по session_id (без system)."""

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id)
        .first()
    )
    if not session:
        raise HTTPException(404, "Сессия не найдена")

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return ChatHistoryResponse(
        messages=[
            ChatMessageDTO(
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in history
            if m.role != "system"
        ]
    )


@app.post("/chat/send", response_model=ChatSendResponse)
def chat_send(payload: ChatSendRequest, db: Session = Depends(get_db)):
    """Отправка сообщения в чат и получение ответа от OpenAI."""

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id)
        .first()
    )
    if not session:
        raise HTTPException(404, "Сессия не найдена")

    assistant = db.query(Assistant).filter(Assistant.id == session.assistant_id).first()
    if not assistant:
        raise HTTPException(400, "Ассистент отсутствует")

    # Сохраняем сообщение пользователя
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    # История сообщений
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    messages_for_openai = [{"role": m.role, "content": m.content} for m in history]

    # Запрос к модели
    try:
        model_name = assistant.base_model or OPENAI_MODEL

        completion = openai_client.chat.completions.create(
            model=model_name,
            messages=messages_for_openai
        )

        reply = completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"OpenAI error: {str(e)}")

    # Сохраняем ответ ассистента
    as_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply,
    )
    db.add(as_msg)
    db.commit()

    # Возвращаем обновлённую историю
    updated = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return ChatSendResponse(
        reply=reply,
        messages=[
            ChatMessageDTO(
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in updated
            if m.role != "system"
        ]
    )