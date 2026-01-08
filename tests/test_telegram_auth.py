import os
from types import SimpleNamespace
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# --- Конфигурация импорта приложения/моделей ---
# Гипотеза (поменяй при необходимости): app и зависимости живут в backend.main_newold,
# модели и Base в backend.models.
APP_MODULE = os.getenv("APP_MODULE", "backend.main_newold")
MODELS_MODULE = os.getenv("MODELS_MODULE", "backend.models")

app_mod = importlib.import_module(APP_MODULE)
models_mod = importlib.import_module(MODELS_MODULE)

# Достаём то, что нам нужно. Если имена отличаются — поправь один раз тут.
app = getattr(app_mod, "app")
get_db = getattr(app_mod, "get_db")
get_current_user_optional = getattr(app_mod, "get_current_user_optional")

Base = getattr(models_mod, "Base")
User = getattr(models_mod, "User")
Assistant = getattr(models_mod, "Assistant")


@pytest.fixture()
def db_session():
    # sqlite файл (чтобы работали несколько соединений в рамках теста)
    engine = create_engine(
        "sqlite:///./test_auth.sqlite",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    # Override get_db
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    # По умолчанию current_user отсутствует (как в реальном "optional")
    app.dependency_overrides[get_current_user_optional] = lambda: None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _seed_assistant(db_session, code="demo"):
    # Минимальная запись ассистента. Если у модели обязательные поля — добавь их тут.
    a = Assistant(code=code)
    db_session.add(a)
    db_session.commit()
    return a


def test_send_chat_message_forbidden_when_current_user_mismatch(client, db_session):
    """
    Ожидаемое поведение по текущему коду:
    - сессия привязана к telegram_id "111"
    - если current_user существует и его telegram_id != "111" -> 403
    """
    _seed_assistant(db_session, code="demo")

    # Создаём сессию как пользователь A (telegram_id=111)
    r = client.post("/api/chat/session", json={"assistant_slug": "demo", "telegram_id": "111"})
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    # Подкладываем current_user как другой telegram_id (222)
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(telegram_id="222")

    r2 = client.post("/api/chat/send", json={"session_id": session_id, "assistant_slug": "demo", "message": "hi"})
    assert r2.status_code == 403, r2.text
    assert r2.json()["detail"] == "Forbidden: telegram_id mismatch"


def test_send_chat_message_ok_when_current_user_matches(client, db_session):
    """
    Happy path:
    - current_user.telegram_id совпадает с session.user.telegram_id -> 200
    """
    _seed_assistant(db_session, code="demo")

    r = client.post("/api/chat/session", json={"assistant_slug": "demo", "telegram_id": "111"})
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(telegram_id="111")

    r2 = client.post("/api/chat/send", json={"session_id": session_id, "assistant_slug": "demo", "message": "hi"})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert "reply" in body


@pytest.mark.xfail(reason="Сейчас current_user optional: при None нет проверки владельца сессии, любой может отправлять в чужую сессию.")
def test_send_chat_message_should_fail_without_auth_but_currently_passes(client, db_session):
    """
    Это тест на желаемое поведение (без current_user нельзя отправлять в сессию).
    Сейчас в коде он, скорее всего, ПРОВАЛИТСЯ (потому что запрос пройдёт).
    """
    _seed_assistant(db_session, code="demo")

    r = client.post("/api/chat/session", json={"assistant_slug": "demo", "telegram_id": "111"})
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    # current_user=None (по умолчанию)
    r2 = client.post("/api/chat/send", json={"session_id": session_id, "assistant_slug": "demo", "message": "hacked"})
    assert r2.status_code in (401, 403), r2.text


def test_create_session_with_valid_initdata(client, db_session, monkeypatch):
    """Создание сессии с валидным Telegram initData — сервер должен верифицировать подпись и использовать user.id."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")

    # craft a valid initData string compatible with backend/core/telegram_auth.py
    import json
    from hashlib import sha256
    import hmac

    user_obj = {"id": 999}
    data = {
        "auth_date": "1600000000",
        "user": json.dumps(user_obj),
    }
    # build data_check_string
    items = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(items)
    secret_key = sha256("test_bot_token".encode()).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()
    init_data = f"user={json.dumps(user_obj)}&auth_date=1600000000&hash={hash_val}"

    _seed_assistant(db_session, code="demo")

    r = client.post("/api/chat/session", json={"assistant_slug": "demo", "init_data": init_data})
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    # Проверим, что в DB сессия принадлежит пользователю с telegram_id = '999'
    from backend.models import ChatSession, User
    sess = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
    assert sess is not None
    user = db_session.query(User).filter(User.id == sess.user_id).first()
    assert user is not None
    assert user.telegram_id == '999'

