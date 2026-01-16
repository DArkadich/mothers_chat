from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = JSON

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String(64), unique=True, nullable=False, index=True)
    profile = Column(JSON, nullable=True)

    chat_sessions = relationship("ChatSession", back_populates="user")


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(64), unique=True, nullable=True, index=True)
    code = Column(String(64), unique=True, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="assistant")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Автозаполнение title, если не задано
        if not getattr(self, "title", None):
            self.title = getattr(self, "code", None) or "Assistant"
        
        # Автозаполнение slug, если не задано
        if hasattr(self, "slug") and not getattr(self, "slug", None):
            base = (getattr(self, "code", None) or getattr(self, "title", None) or "assistant")
            self.slug = str(base).strip().lower().replace(" ", "-")
        
        # Автозаполнение system_prompt, если не задано (для NOT NULL constraint)
        if hasattr(self, "system_prompt") and not getattr(self, "system_prompt", None):
            self.system_prompt = "You are a helpful assistant."


class ChatSession(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    assistant = relationship("Assistant", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column('conversation_id', Integer, ForeignKey("conversations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)

    session = relationship("ChatSession", back_populates="messages")


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_key = Column(String(64), nullable=False, index=True)
    plan_name = Column(String(64), nullable=False, index=True)
    details_cards = Column(JSONB if JSONB != JSON else JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Уникальность гарантируется миграцией через constraint, не через Index
