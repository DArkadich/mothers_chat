from fastapi.testclient import TestClient
import pytest

import backend.main_newold as appmod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use a file-backed sqlite DB for tests to persist tables across connections
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_mamino.db")
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Replace module engine/session with test ones
appmod.engine = engine
appmod.SessionLocal = SessionLocalTest

client = TestClient(appmod.app)

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables in the test DB and ensure a fresh DB for each test
    appmod.Base.metadata.create_all(bind=appmod.engine)
    # clean up after test
    yield
    appmod.Base.metadata.drop_all(bind=appmod.engine)
    try:
        os.remove("test_mamino.db")
    except OSError:
        pass


def test_create_session_and_send_message(monkeypatch):
    # create assistant in DB
    db = appmod.SessionLocal()
    assistant = appmod.Assistant(code="testassistant", title="Test", system_prompt="You are helpful")
    db.add(assistant)
    db.commit()
    db.refresh(assistant)

    # create session
    resp = client.post("/api/chat/session", json={"assistant_slug": "testassistant", "telegram_id": "123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    session_id = data["session_id"]

    # prepare fake OpenAI response
    class FakeChoice:
        class Message:
            def __init__(self, content):
                self.content = content
        def __init__(self, content):
            self.message = FakeChoice.Message(content)

    class FakeCompletion:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    class FakeOpenAI:
        def __init__(self):
            self.chat = self
        def completions(self):
            pass
        class completions:
            @staticmethod
            def create(model, messages):
                return FakeCompletion("Hello from fake model")

    # monkeypatch OpenAI client
    appmod.openai_client = FakeOpenAI()

    # send message
    resp2 = client.post("/api/chat/send", json={"session_id": session_id, "assistant_slug": "testassistant", "message": "Hi"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "reply" in data2 and data2["reply"] == "Hello from fake model"
    assert isinstance(data2.get("messages"), list)

    db.close()
