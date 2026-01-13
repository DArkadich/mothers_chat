# conftest.py
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Устанавливаем fake режим для всех тестов
os.environ.setdefault("ENABLE_FAKE_OPENAI", "1")
