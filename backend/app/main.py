from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime

# предполагаем, что у тебя уже есть engine, SessionLocal, Base и модели

# если нет get_db – добавь:
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatSessionCreate(BaseModel):
    assistant_slug: str
    telegram_id: str


class ChatSessionResponse(BaseModel):
    session_id: uuid.UUID


@app.post("/api/chat/session", response_model=ChatSessionResponse)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
):
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

    user = (
        db.query(User)
        .filter(User.telegram_id == payload.telegram_id)
        .first()
    )
    if not user:
        user = User(telegram_id=payload.telegram_id, profile={})
        db.add(user)
        db.commit()
        db.refresh(user)

    session = ChatSession(user_id=user.id, assistant_id=assistant.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    system_msg = ChatMessage(
        session_id=session.id,
        role="system",
        content=assistant.system_prompt,
    )
    db.add(system_msg)
    db.commit()

    return ChatSessionResponse(session_id=session.id)
class ChatSendRequest(BaseModel):
    session_id: uuid.UUID
    assistant_slug: str
    message: str


class ChatMessageDTO(BaseModel):
    role: str
    content: str
    created_at: str


class ChatSendResponse(BaseModel):
    reply: str
    messages: list[ChatMessageDTO]


@app.post("/api/chat/send", response_model=ChatSendResponse)
def send_chat_message(
    payload: ChatSendRequest,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    assistant = (
        db.query(Assistant)
        .filter(Assistant.id == session.assistant_id)
        .first()
    )
    if not assistant or assistant.slug != payload.assistant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ассистент не соответствует сессии",
        )

    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    openai_messages = [{"role": "system", "content": assistant.system_prompt}]
    for m in msgs:
        if m.role == "system":
            continue
        openai_messages.append({"role": m.role, "content": m.content})

    completion = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=openai_messages,
    )
    reply_text = completion.choices[0].message.content

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    updated = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return ChatSendResponse(
        reply=reply_text,
        messages=[
            ChatMessageDTO(
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in updated
        ],
    )
