// URL backend-а.
// В докере на локалке: http://localhost:8000
// В проде поставишь сюда свой домен, например https://api.motherschat.example
const BACKEND_BASE_URL = "http://localhost:8000";

let tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
let initData = "";
let currentAssistant = null;
let isSending = false;

// Элементы DOM
const userInfoEl = document.getElementById("user-info");
const assistantsListEl = document.getElementById("assistants-list");
const limitsEl = document.getElementById("limits");
const chatTitleEl = document.getElementById("chat-title");
const chatWindowEl = document.getElementById("chat-window");
const chatFormEl = document.getElementById("chat-form");
const chatInputEl = document.getElementById("chat-input");
const statusBarEl = document.getElementById("status-bar");

// Инициализация Telegram Web App
function initTelegram() {
  if (!tg) {
    console.warn("Telegram WebApp not found, running in browser debug mode.");
    statusBarEl.textContent = "Режим отладки: Telegram WebApp не найден.";
    return;
  }

  tg.ready();
  tg.expand();
  tg.MainButton.hide();

  initData = tg.initData || "";

  if (!initData) {
    statusBarEl.textContent = "Не удалось получить initData от Telegram.";
  } else {
    statusBarEl.textContent = "Подключено к Telegram.";
  }
}

// Обёртка над fetch с заголовком X-Telegram-Init-Data
async function apiFetch(path, options = {}) {
  const url = BACKEND_BASE_URL + path;
  const headers = options.headers || {};
  if (initData) {
    headers["X-Telegram-Init-Data"] = initData;
  }
  headers["Content-Type"] = "application/json";

  const finalOptions = {
    method: options.method || "GET",
    headers,
    body: options.body || undefined,
  };

  const resp = await fetch(url, finalOptions);

  if (!resp.ok) {
    let detail = `Ошибка API: ${resp.status}`;
    try {
      const data = await resp.json();
      if (data && data.detail) {
        detail = Array.isArray(data.detail)
          ? data.detail.map(d => d.msg || d).join("; ")
          : data.detail;
      }
    } catch (e) {
      // игнорируем — оставляем detail как есть
    }
    throw new Error(detail);
  }

  if (resp.status === 204) {
    return null;
  }

  return resp.json();
}

function setStatus(text) {
  statusBarEl.textContent = text || "";
}

function appendMessage(role, text) {
  const msgEl = document.createElement("div");
  msgEl.classList.add("chat-message");
  msgEl.classList.add(role === "user" ? "user" : "assistant");
  msgEl.textContent = text;
  chatWindowEl.appendChild(msgEl);
  chatWindowEl.scrollTop = chatWindowEl.scrollHeight;
}

// Загрузка информации о пользователе
async function loadMe() {
  try {
    const me = await apiFetch("/me");
    const name = me.first_name || me.username || me.telegram_id;
    userInfoEl.textContent = `Вы вошли как: ${name}`;
  } catch (e) {
    console.error(e);
    userInfoEl.textContent = "Не удалось загрузить данные пользователя.";
    setStatus(e.message);
  }
}

// Загрузка лимитов
async function loadLimits() {
  try {
    const limits = await apiFetch("/limits");
    limitsEl.textContent = `Лимиты: день ${limits.daily_used}/${limits.daily_limit}, месяц ${limits.monthly_used}/${limits.monthly_limit}`;
  } catch (e) {
    console.error(e);
    limitsEl.textContent = "Не удалось загрузить лимиты.";
  }
}

// Рендер списка ассистентов
function renderAssistants(list) {
  assistantsListEl.innerHTML = "";

  if (!Array.isArray(list) || list.length === 0) {
    assistantsListEl.textContent = "Ассистенты недоступны.";
    return;
  }

  list.forEach(a => {
    const item = document.createElement("div");
    item.classList.add("assistant-item");
    if (!a.has_access) {
      item.classList.add("disabled");
    }
    if (currentAssistant && currentAssistant.id === a.id) {
      item.classList.add("active");
    }

    const title = document.createElement("div");
    title.classList.add("assistant-title");
    title.textContent = a.title;

    const desc = document.createElement("div");
    desc.classList.add("assistant-description");
    desc.textContent = a.description;

    const badge = document.createElement("div");
    badge.classList.add("assistant-badge");
    if (a.has_access) {
      badge.classList.add("access");
      badge.textContent = "Доступ есть";
    } else {
      badge.classList.add("no-access");
      badge.textContent = "Нет доступа";
    }

    item.appendChild(title);
    item.appendChild(desc);
    item.appendChild(badge);

    if (a.has_access) {
      item.addEventListener("click", () => {
        currentAssistant = a;
        updateActiveAssistant();
      });
    }

    assistantsListEl.appendChild(item);
  });
}

function updateActiveAssistant() {
  const items = assistantsListEl.querySelectorAll(".assistant-item");
  items.forEach(item => item.classList.remove("active"));

  if (!currentAssistant) {
    chatTitleEl.textContent = "Чат";
    chatWindowEl.innerHTML = "";
    return;
  }

  chatTitleEl.textContent = `Чат: ${currentAssistant.title}`;

  // подсветка активного
  const children = Array.from(assistantsListEl.children);
  children.forEach(el => {
    const titleEl = el.querySelector(".assistant-title");
    if (titleEl && titleEl.textContent === currentAssistant.title) {
      el.classList.add("active");
    }
  });

  // при выборе нового ассистента пока не грузим историю, просто очищаем окно
  chatWindowEl.innerHTML = "";
  appendMessage(
    "assistant",
    "Выберите вопрос и напишите его внизу. Я постараюсь помочь 🙂"
  );
}

// Загрузка ассистентов
async function loadAssistants() {
  try {
    const list = await apiFetch("/assistants");
    renderAssistants(list);
    // автоматически выбираем первого доступного
    const firstAvailable = list.find(a => a.has_access);
    if (firstAvailable && !currentAssistant) {
      currentAssistant = firstAvailable;
      updateActiveAssistant();
    }
  } catch (e) {
    console.error(e);
    assistantsListEl.textContent = "Ошибка загрузки ассистентов.";
    setStatus(e.message);
  }
}

// Отправка сообщения
async function handleSendMessage(event) {
  event.preventDefault();

  if (!currentAssistant) {
    setStatus("Выберите ассистента.");
    return;
  }

  const text = chatInputEl.value.trim();
  if (!text) {
    return;
  }

  if (isSending) {
    return;
  }

  isSending = true;
  chatFormEl.querySelector("button").disabled = true;
  setStatus("Отправка запроса...");

  appendMessage("user", text);
  chatInputEl.value = "";

  try {
    const payload = {
      assistant_id: currentAssistant.id,
      message: text,
    };

    const resp = await apiFetch("/chat/send", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    appendMessage("assistant", resp.reply);
    setStatus(`Ответ от модели ${resp.used_model}.`);
    await loadLimits();
  } catch (e) {
    console.error(e);
    appendMessage("assistant", "Произошла ошибка при обработке запроса. Попробуйте позже.");
    setStatus(e.message);
  } finally {
    isSending = false;
    chatFormEl.querySelector("button").disabled = false;
  }
}

// Инициализация
function initApp() {
  initTelegram();

  chatFormEl.addEventListener("submit", handleSendMessage);

  loadMe();
  loadAssistants();
  loadLimits();
}

document.addEventListener("DOMContentLoaded", initApp);
