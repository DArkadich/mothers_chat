import os
import hmac
import hashlib
import time
import logging
from datetime import datetime, date
from urllib.parse import parse_qsl
import uuid

from fastapi import FastAPI, Depends, Header, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, constr
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

from dotenv import load_dotenv

from openai import OpenAI
import tiktoken

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

# =========================
# ЗАГРУЗКА КОНФИГА
# =========================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

DEFAULT_DAILY_REQUESTS = int(os.getenv("DEFAULT_DAILY_REQUESTS", "30"))
DEFAULT_MONTHLY_REQUESTS = int(os.getenv("DEFAULT_MONTHLY_REQUESTS", "200"))

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1-mini")
REASONING_MODEL = "o3-mini"  # используем через base_model ассистента

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

if TELEGRAM_BOT_TOKEN.startswith("YOUR_"):
    print("⚠️ WARNING: TELEGRAM_BOT_TOKEN not set. Set TELEGRAM_BOT_TOKEN env var.")
if OPENAI_API_KEY.startswith("YOUR_"):
    print("⚠️ WARNING: OPENAI_API_KEY not set. Set OPENAI_API_KEY env var.")

# =========================
# ЛОГИРОВАНИЕ
# =========================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("motherschat")

# =========================
# МЕТРИКИ
# =========================

REQUEST_COUNT = Counter(
    "motherschat_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "motherschat_request_latency_seconds", "HTTP request latency", ["endpoint"]
)

# =========================
# RATE LIMITING (простое, по IP)
# =========================

from collections import defaultdict
from time import time as now_ts

_ip_requests: Dict[str, List[float]] = defaultdict(list)


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path

        if endpoint.startswith("/metrics"):
            return await call_next(request)

        ts = now_ts()
        window_start = ts - 60

        timestamps = _ip_requests[client_ip]
        # очищаем старые записи
        timestamps = [t for t in timestamps if t > window_start]
        timestamps.append(ts)
        _ip_requests[client_ip] = timestamps

        if len(timestamps) > RATE_LIMIT_PER_MINUTE:
            logger.warning(
                f"Rate limit exceeded: ip={client_ip}, count={len(timestamps)}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте чуть позже.",
            )

        response = await call_next(request)
        return response


# =========================
# БАЗА ДАННЫХ
# =========================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    limits = relationship("UserLimits", back_populates="user")
    assistants = relationship("UserAssistant", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    data = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    base_model = Column(String, nullable=False, default=DEFAULT_MODEL)
    system_prompt = Column(Text, nullable=False)
    extra_config = Column(JSON, nullable=False, default={})

    users = relationship("UserAssistant", back_populates="assistant")
    conversations = relationship("Conversation", back_populates="assistant")


class UserAssistant(Base):
    __tablename__ = "user_assistants"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="assistants")
    assistant = relationship("Assistant", back_populates="users")


class UserLimits(Base):
    __tablename__ = "user_limits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    daily_requests_base = Column(Integer, default=DEFAULT_DAILY_REQUESTS)
    monthly_requests_base = Column(Integer, default=DEFAULT_MONTHLY_REQUESTS)
    daily_requests_bonus = Column(Integer, default=0)
    monthly_requests_bonus = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="limits")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String, nullable=False)  # 'user' / 'assistant'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    age_group = Column(String, nullable=True)  # 'pregnant', '0_1', '1_3', ...
    tags = Column(JSON, nullable=False, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class KBExample(Base):
    __tablename__ = "kb_examples"

    id = Column(Integer, primary_key=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=True)
    question_example = Column(Text, nullable=False)
    answer_example = Column(Text, nullable=False)
    age_group = Column(String, nullable=True)
    tags = Column(JSON, nullable=False, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


# =========================
# OpenAI клиент + tiktoken
# =========================

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai_client = OpenAI()

# берём универсальный энкодер, если модель не найдена — fallback
try:
    tokenizer = tiktoken.encoding_for_model(DEFAULT_MODEL)
except Exception:
    tokenizer = tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        return len(tokenizer.encode(text))
    except Exception:
        # fallback — грубая оценка
        return max(1, len(text) // 4)


# =========================
# УТИЛИТЫ
# =========================

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _calc_telegram_check_hash(data: Dict[str, str], bot_token: str) -> str:
    auth_date = data.get("auth_date")
    if auth_date is None:
        raise ValueError("auth_date is missing")

    check_data_pairs = []
    for key in sorted(k for k in data.keys() if k != "hash"):
        value = data[key]
        check_data_pairs.append(f"{key}={value}")
    check_data_string = "\n".join(check_data_pairs)

    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    h = hmac.new(secret_key, msg=check_data_string.encode("utf-8"), digestmod=hashlib.sha256)
    return h.hexdigest()


def validate_telegram_init_data(init_data: str, bot_token: str) -> Dict[str, str]:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.get("hash")
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing hash")

    try:
        expected_hash = _calc_telegram_check_hash(parsed, bot_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    if not hmac.compare_digest(received_hash, expected_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad hash")

    auth_date_str = parsed.get("auth_date")
    if auth_date_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth_date")

    try:
        auth_ts = int(auth_date_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth_date")

    if time.time() - auth_ts > 7 * 24 * 3600:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="initData is too old")

    return parsed


def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
) -> User:
    data = validate_telegram_init_data(x_telegram_init_data, TELEGRAM_BOT_TOKEN)

    user_id = None
    username = None
    first_name = None

    user_raw = data.get("user")
    if user_raw:
        import json
        try:
            user_obj = json.loads(user_raw)
            user_id = user_obj.get("id")
            username = user_obj.get("username")
            first_name = user_obj.get("first_name")
        except Exception:
            pass

    if not user_id:
        user_id = data.get("id") or data.get("user_id")
        username = data.get("username")
        first_name = data.get("first_name")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user id in initData")

    user = db.query(User).filter(User.telegram_id == str(user_id)).first()
    if not user:
        try:
            user = User(
                telegram_id=str(user_id),
                username=username,
                first_name=first_name,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            profile = UserProfile(user_id=user.id, data={})
            limits = UserLimits(user_id=user.id)
            db.add(profile)
            db.add(limits)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.exception("DB error creating user")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка базы данных при создании пользователя",
            )
    else:
        user.last_seen_at = datetime.utcnow()
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("DB error updating last_seen_at")

    return user


def get_effective_limits(user: User, db: Session) -> Dict[str, int]:
    limits = db.query(UserLimits).filter(UserLimits.user_id == user.id).first()
    if not limits:
        limits = UserLimits(user_id=user.id)
        db.add(limits)
        db.commit()
        db.refresh(limits)

    daily = (limits.daily_requests_base or 0) + (limits.daily_requests_bonus or 0)
    monthly = (limits.monthly_requests_base or 0) + (limits.monthly_requests_bonus or 0)
    return {"daily": daily, "monthly": monthly}


def check_limits_or_raise(user: User, db: Session) -> None:
    limits = get_effective_limits(user, db)
    today = date.today()
    month_start = date(today.year, today.month, 1)

    daily_count = (
        db.query(func.count(Message.id))
        .join(Conversation)
        .filter(
            Conversation.user_id == user.id,
            Message.role == "user",
            Message.created_at >= datetime.combine(today, datetime.min.time()),
        )
        .scalar()
    )

    monthly_count = (
        db.query(func.count(Message.id))
        .join(Conversation)
        .filter(
            Conversation.user_id == user.id,
            Message.role == "user",
            Message.created_at >= datetime.combine(month_start, datetime.min.time()),
        )
        .scalar()
    )

    if daily_count >= limits["daily"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен дневной лимит сообщений. Попробуйте завтра или расширьте лимит.",
        )

    if monthly_count >= limits["monthly"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен месячный лимит сообщений. Можно расширить лимит за доплату.",
        )


def build_context_messages(
    db: Session,
    user: User,
    assistant: Assistant,
    max_messages: int = 10,
    max_examples: int = 3,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    messages.append({"role": "system", "content": assistant.system_prompt})

    # Подмешиваем примеры из базы знаний (простейшая версия: первые N по ассистенту)
    examples = (
        db.query(KBExample)
        .filter(
            (KBExample.assistant_id == assistant.id) | (KBExample.assistant_id.is_(None))
        )
        .order_by(KBExample.created_at.asc())
        .limit(max_examples)
        .all()
    )

    if examples:
        examples_block = "Вот примеры того, как нужно отвечать в типичных ситуациях:\n\n"
        for ex in examples:
            examples_block += f"Вопрос: {ex.question_example}\nОтвет: {ex.answer_example}\n\n"
        messages.append({"role": "system", "content": examples_block})

    conv = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id, Conversation.assistant_id == assistant.id)
        .order_by(Conversation.created_at.desc())
        .first()
    )

    if conv:
        last_msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(max_messages)
            .all()
        )
        for m in reversed(last_msgs):
            messages.append({"role": m.role, "content": m.content})

    return messages


# =========================
# Pydantic-схемы
# =========================

MessageText = constr(strip_whitespace=True, min_length=1, max_length=4000)


class AssistantOut(BaseModel):
    id: int
    code: str
    title: str
    description: str
    base_model: str
    has_access: bool

    class Config:
        orm_mode = True


class MeOut(BaseModel):
    id: int
    telegram_id: str
    username: Optional[str]
    first_name: Optional[str]

    class Config:
        orm_mode = True


class LimitsOut(BaseModel):
    daily_limit: int
    monthly_limit: int
    daily_used: int
    monthly_used: int


class ChatSendIn(BaseModel):
    assistant_id: int = Field(..., ge=1)
    message: MessageText


class ChatSendOut(BaseModel):
    conversation_id: int
    reply: str
    used_model: str
    user_message_tokens: int
    assistant_message_tokens: int


# =========================
# FASTAPI ПРИЛОЖЕНИЕ
# =========================

app = FastAPI(title="Moms AI Assistants API", version="0.2.0")

# middlewares
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SimpleRateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        latency = time.time() - start
        endpoint = request.url.path
        status_code = response.status_code if response else 500
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=status_code,
        ).inc()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Assistant).count() == 0:
            assistants_seed = [
                Assistant(
                    code="baby_sleep_0_1",
                    title="Сон малыша 0–12 месяцев",
                    description="Помогает наладить режим сна, засыпания и ночные пробуждения для детей до года.",
                    base_model=DEFAULT_MODEL,
                    system_prompt=(
                        "Ты ИИ-помощник для мам ребёнка до 1 года. "
                        "Отвечай мягко, поддерживающе, без запугивания. "
                        "Давай рекомендации по сну ребёнка с учётом возраста, но не ставь диагнозы и не отменяй врачей."
                    ),
                    extra_config={"temperature": 0.7},
                ),
                Assistant(
                    code="food_1_3",
                    title="Питание 1–3 года",
                    description="Советы по питанию, режиму и пищевому поведению детей от 1 до 3 лет.",
                    base_model=DEFAULT_MODEL,
                    system_prompt=(
                        "Ты ИИ-помощник по питанию для детей 1–3 лет. "
                        "Учитывай возраст, нормальную избирательность, поддерживай маму и ребёнка. "
                        "Не давай радикальных советов и не заменяй консультацию педиатра."
                    ),
                    extra_config={"temperature": 0.6},
                ),
            ]
            db.add_all(assistants_seed)
            db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error during startup seeding")
    finally:
        db.close()


# =========================
# ЭНДПОИНТЫ
# =========================

@app.get("/me", response_model=MeOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/assistants", response_model=List[AssistantOut])
def list_assistants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assistants = db.query(Assistant).all()
        user_assistant_ids = {
            ua.assistant_id
            for ua in db.query(UserAssistant)
            .filter(UserAssistant.user_id == current_user.id)
            .all()
        }
    except SQLAlchemyError:
        logger.exception("DB error in /assistants")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при получении ассистентов",
        )

    result: List[AssistantOut] = []
    for a in assistants:
        result.append(
            AssistantOut(
                id=a.id,
                code=a.code,
                title=a.title,
                description=a.description,
                base_model=a.base_model,
                has_access=a.id in user_assistant_ids,
            )
        )
    return result


@app.get("/limits", response_model=LimitsOut)
def get_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limits = get_effective_limits(current_user, db)
    today = date.today()
    month_start = date(today.year, today.month, 1)

    try:
        daily_used = (
            db.query(func.count(Message.id))
            .join(Conversation)
            .filter(
                Conversation.user_id == current_user.id,
                Message.role == "user",
                Message.created_at >= datetime.combine(today, datetime.min.time()),
            )
            .scalar()
        )

        monthly_used = (
            db.query(func.count(Message.id))
            .join(Conversation)
            .filter(
                Conversation.user_id == current_user.id,
                Message.role == "user",
                Message.created_at >= datetime.combine(month_start, datetime.min.time()),
            )
            .scalar()
        )
    except SQLAlchemyError:
        logger.exception("DB error in /limits")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при получении лимитов",
        )

    return LimitsOut(
        daily_limit=limits["daily"],
        monthly_limit=limits["monthly"],
        daily_used=daily_used or 0,
        monthly_used=monthly_used or 0,
    )


@app.post("/chat/send", response_model=ChatSendOut)
def chat_send(
    payload: ChatSendIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Проверяем доступ к ассистенту
    assistant = db.query(Assistant).filter(Assistant.id == payload.assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ассистент не найден")

    has_access = (
        db.query(UserAssistant)
        .filter(
            UserAssistant.user_id == current_user.id,
            UserAssistant.assistant_id == assistant.id,
        )
        .first()
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к ассистенту. Приобретите соответствующий пакет.",
        )

    check_limits_or_raise(current_user, db)

    try:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.user_id == current_user.id,
                Conversation.assistant_id == assistant.id,
            )
            .order_by(Conversation.created_at.desc())
            .first()
        )
        if not conv:
            conv = Conversation(user_id=current_user.id, assistant_id=assistant.id)
            db.add(conv)
            db.commit()
            db.refresh(conv)

        user_tokens = estimate_tokens(payload.message)
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=payload.message,
            tokens_used=user_tokens,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        conv.last_message_at = datetime.utcnow()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error in chat_send (creating message)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при сохранении сообщения",
        )

    context_messages = build_context_messages(db, current_user, assistant, max_messages=10)
    context_messages.append({"role": "user", "content": payload.message})

    model_name = assistant.base_model or DEFAULT_MODEL

    try:
        completion = openai_client.chat.completions.create(
            model=model_name,
            messages=context_messages,
            temperature=assistant.extra_config.get("temperature", 0.7)
            if assistant.extra_config
            else 0.7,
        )
    except Exception as e:
        logger.exception("OpenAI error in /chat/send")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка при обращении к модели. Попробуйте позже.",
        )

    reply_text = completion.choices[0].message.content or ""
    assistant_tokens = estimate_tokens(reply_text)

    try:
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=reply_text,
            tokens_used=assistant_tokens,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error in chat_send (saving assistant reply)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при сохранении ответа ассистента",
        )

    return ChatSendOut(
        conversation_id=conv.id,
        reply=reply_text,
        used_model=model_name,
        user_message_tokens=user_tokens,
        assistant_message_tokens=assistant_tokens,
    )


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
