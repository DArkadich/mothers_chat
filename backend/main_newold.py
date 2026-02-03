import os
import uuid
import json
from datetime import datetime
from typing import List, Literal, Optional, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
from backend.deps.auth import InitDataPayload, resolve_user_from_init_data

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

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI (чат)
openai_client = None
if OPENAI_API_KEY and not ENABLE_FAKE_OPENAI:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    except Exception:
        openai_client = None

# Клиент OpenAI для Images API (карта желаний)
openai_images_client = None
if OPENAI_API_KEY:
    try:
        openai_images_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        openai_images_client = None

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    payload: InitDataPayload = Depends(),
    db: Session = Depends(get_db),
):
    return resolve_user_from_init_data(payload.init_data, db)


# ==========
# RATE LIMITING
# ==========

async def rate_limit_dep(
    request: Request,
) -> None:
    # твоя логика лимитов
    key = request.client.host if request.client else "anon"
    if not limiter.allowed(key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    return None


# ==========
# МОДЕЛИ БД
# ==========

from .models import Base, User, Assistant, ChatSession, ChatMessage, Package



# В реальности структуры мигрируются через Alembic.
# Здесь create_all можно оставить закомментированным,
# если Alembic уже настроен под эти модели.
# Base.metadata.create_all(bind=engine)


# ==========
# СХЕМЫ API
# ==========

class ChatSessionCreate(BaseModel):
    assistant_slug: str = Field(..., examples=["newborn_sleep"])
    init_data: str = Field(..., description="Telegram WebApp initData string. Server will validate signature and extract user.id as telegram_id.")


class ChatSessionResponse(BaseModel):
    session_id: int


class ChatSendRequest(BaseModel):
    session_id: int
    assistant_slug: str
    message: str
    init_data: str


class ChatMessageDTO(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str


class ChatSendResponse(BaseModel):
    reply: str
    messages: List[ChatMessageDTO]


class DetailCardItem(BaseModel):
    title: str
    items: Optional[List[str]] = None
    bodyHtml: Optional[str] = None
    body: Optional[str] = None


class PackageDetailsResponse(BaseModel):
    details_cards: List[DetailCardItem]


class OnboardedRequest(BaseModel):
    init_data: str = Field(..., description="Telegram WebApp initData for auth.")
    complete: bool = Field(default=False, description="If true, mark onboarding as completed.")


class OnboardedResponse(BaseModel):
    onboarded: bool


class WishlistGenerateResponse(BaseModel):
    image_b64: str


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


# Логирование 422 (помогает понять, какие поля не совпали)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        raw = await request.body()
        body = raw.decode("utf-8", errors="replace")
        if len(body) > 2000:
            body = body[:2000] + "...[truncated]"
    except Exception:
        body = "<unavailable>"

    logger.info(
        "[ValidationError] path=%s method=%s errors=%s body=%s",
        request.url.path,
        request.method,
        exc.errors(),
        body,
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Глобальный exception handler для логирования ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error(
        "[Exception] path=%s method=%s error=%s traceback=%s",
        request.url.path,
        request.method,
        str(exc),
        traceback.format_exc(),
    )
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# =====================
# ОНБОРДИНГ (флаг «уже видел онбординг» по пользователю)
# =====================

@app.post("/api/onboarded", response_model=OnboardedResponse)
def onboarded_status_or_complete(
    payload: OnboardedRequest,
    db: Session = Depends(get_db),
):
    """
    GET-режим: body { init_data } → { onboarded: bool }.
    SET-режим: body { init_data, complete: true } → помечает онбординг пройденным, возвращает { onboarded: true }.
    """
    from sqlalchemy import inspect

    current_user = resolve_user_from_init_data(payload.init_data, db)
    cols = [c["name"] for c in inspect(engine).get_columns("users")]
    if "profile" not in cols:
        return OnboardedResponse(onboarded=False)

    profile = dict(getattr(current_user, "profile", None) or {})
    if payload.complete:
        profile["onboarded"] = True
        current_user.profile = profile
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(current_user, "profile")
        db.commit()
        db.refresh(current_user)
        return OnboardedResponse(onboarded=True)
    return OnboardedResponse(onboarded=bool(profile.get("onboarded")))


# =====================
# КАРТА ЖЕЛАНИЙ (генерация изображения по фото + промпт)
# =====================

@app.post("/api/wishlist/generate", response_model=WishlistGenerateResponse)
@app.post("/wishlist/generate", response_model=WishlistGenerateResponse)  # альтернативный путь (если прокси обрезает /api)
async def wishlist_generate(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    init_data: Optional[str] = Form(None),
):
    """
    Генерация изображения для карты желаний: фото пользователя + текстовый запрос.
    Возвращает PNG в base64.
    """
    import io

    if not OPENAI_API_KEY or not openai_images_client:
        raise HTTPException(status_code=500, detail="Сервис генерации изображений недоступен")

    try:
        raw_bytes = await image.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Пустой файл изображения")

        content_type = (image.content_type or "").strip().lower()
        if content_type not in ("image/jpeg", "image/png", "image/webp"):
            content_type = "image/jpeg"
        filename = image.filename or "image.jpg"
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            filename = "image.jpg"

        # Префикс помогает модели сгенерировать полную сцену с лицом из фото, а не только фон
        enhanced_prompt = (
            f"Create a full photorealistic scene with this person in it. "
            f"Preserve the person's face exactly as in the photo. "
            f"Scene description: {prompt}"
        )

        result = openai_images_client.images.edit(
            model="gpt-image-1",
            image=(filename, io.BytesIO(raw_bytes), content_type),
            prompt=enhanced_prompt,
            size="1024x1024",
        )

        if not result.data or not getattr(result.data[0], "b64_json", None):
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать изображение")

        return WishlistGenerateResponse(image_b64=result.data[0].b64_json)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("wishlist generate error: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")


# =====================
# РОУТЫ ЧАТА С АССИСТЕНТОМ
# =====================

@app.post("/api/chat/session", response_model=ChatSessionResponse)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """
    Создаёт новую сессию чата для заданного ассистента.

    Использует только `init_data` от Telegram WebApp — сервер верифицирует подпись.
    """
    # ВАЖНО: не используем Depends(get_current_user) здесь, чтобы не было конфликта
    # двух "body" моделей (payload + InitDataPayload). Резолвим пользователя вручную,
    # как в /api/chat/send и /api/chat/history.
    current_user = resolve_user_from_init_data(payload.init_data, db)

    # 1) ассистент должен существовать
    assistant = db.query(Assistant).filter(
        or_(Assistant.code == payload.assistant_slug, Assistant.slug == payload.assistant_slug)
    ).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # 2) если сессия уже есть для этой пары user+assistant — возвращаем последнюю
    existing = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id, ChatSession.assistant_id == assistant.id)
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .first()
    )
    if existing:
        return {"session_id": existing.id}

    # 3) создать новую сессию
    sess = ChatSession(user_id=current_user.id, assistant_id=assistant.id)
    db.add(sess)
    db.commit()
    db.refresh(sess)

    return {"session_id": sess.id}


class ChatHistoryRequest(BaseModel):
    session_id: int
    init_data: str = Field(..., description="Telegram WebApp initData string. Server will validate signature and extract user.id as telegram_id.")


@app.post("/api/chat/history", response_model=None)
def get_chat_history(
    payload: ChatHistoryRequest,
    db: Session = Depends(get_db),
):
    """
    Получение истории сообщений по session_id (без system).
    Требует авторизации: сессия должна принадлежать текущему пользователю.
    """
    # 1) Разрешить пользователя из init_data
    # Fallback для истории: если подпись невалидна, извлекаем user.id без проверки
    from backend.deps.auth import resolve_user_from_init_data
    current_user = resolve_user_from_init_data(payload.init_data, db, allow_unsafe=True)
    
    # 2) Найти сессию с проверкой владельца (КРИТИЧНО для безопасности)
    sess = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2) Получить историю сообщений (без system)
    history_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sess.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )

    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in history_messages
        if msg.role in ("user", "assistant")
    ]

    return {"messages": messages}


@app.get("/api/packages/{section_key}/{plan_name}/details", response_model=PackageDetailsResponse)
def get_package_details(section_key: str, plan_name: str, db: Session = Depends(get_db)):
    """
    Получение деталей пакета (карточки "Подробнее") по section_key и plan_name.
    """
    package = (
        db.query(Package)
        .filter(Package.section_key == section_key, Package.plan_name == plan_name)
        .first()
    )
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    raw_cards = package.details_cards
    if not isinstance(raw_cards, list):
        raise HTTPException(status_code=500, detail="Invalid package details_cards format")
    
    # Валидация и нормализация карточек
    validated_cards = []
    for card in raw_cards:
        if not isinstance(card, dict):
            continue
        if not card.get("title"):
            continue
        validated_cards.append(DetailCardItem(**card))
    
    return PackageDetailsResponse(details_cards=validated_cards)


@app.post("/api/chat/send", response_model=None, dependencies=[Depends(rate_limit_dep)])
def send_chat_message(
    payload: ChatSendRequest,
    db=Depends(get_db),  # без Session
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

    # auth check: разрешаем пользователя из init_data
    from backend.deps.auth import resolve_user_from_init_data
    current_user = resolve_user_from_init_data(payload.init_data, db)
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
    # Читаем переменную заново при каждом запросе (на случай изменения в runtime)
    current_fake_mode = env_bool("ENABLE_FAKE_OPENAI", "0")
    if current_fake_mode:
        FAKE_REPLY = os.getenv("FAKE_REPLY", "Hello from fake model")
        reply = FAKE_REPLY
    else:
        # Проверка: нужен API ключ (только если не fake режим)
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OpenAI API key is not set")
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
