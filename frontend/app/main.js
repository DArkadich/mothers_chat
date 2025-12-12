/* global Telegram */

(function () {
  "use strict";

  // =========================
  // Конфиг
  // =========================
  const API_BASE = "/api";

  // Для MVP: список ассистентов на фронте.
  // Сейчас backend игнорирует assistant_slug и берёт первого ассистента из БД,
  // но интерфейсу нужно чем-то наполняться.
  const ASSISTANTS = [
    {
      slug: "newborn_sleep",
      title: "Наши первые дни вместе",
      description: "Поддержка и бытовые ориентиры в первые недели с новорождённым.",
    },
    {
      slug: "pregnancy_calm",
      title: "Спокойная беременность",
      description: "Мягкие подсказки и структурирование тревожных мыслей.",
    },
    {
      slug: "routine_0_1",
      title: "Режим 0–1",
      description: "Сон, кормление, спокойные ритуалы и бытовые лайфхаки.",
    },
    {
      slug: "care_basics",
      title: "Уход без паники",
      description: "Купание, подмывание, одежда по температуре — без страшилок.",
    },
  ];

  // =========================
  // Telegram WebApp init
  // =========================
  const tg = (typeof Telegram !== "undefined" && Telegram.WebApp) ? Telegram.WebApp : null;

  function getTelegramId() {
    try {
      if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.id) {
        return String(tg.initDataUnsafe.user.id);
      }
    } catch (_) {}
    return "debug-123";
  }

  function setupTelegramUi() {
    try {
      if (!tg) return;
      tg.ready();
      tg.expand();
      // Нежный фон под дизайн, Telegram иногда перекрашивает
      tg.setHeaderColor && tg.setHeaderColor("#f7f5ef");
      tg.setBackgroundColor && tg.setBackgroundColor("#f7f5ef");
    } catch (e) {
      console.warn("[mamino] Telegram init warning:", e);
    }
  }

  // =========================
  // DOM
  // =========================
  const screenHome = document.getElementById("screen-home");
  const screenAssistants = document.getElementById("screen-assistants");
  const screenChat = document.getElementById("screen-chat");

  const goAssistantsBtn = document.getElementById("goAssistants");
  const assistantsGrid = document.getElementById("assistantsGrid");

  const tabHome = document.getElementById("tabHome");
  const tabAssistants = document.getElementById("tabAssistants");
  const tabChat = document.getElementById("tabChat");

  const chatTitle = document.getElementById("chatTitle");
  const chatMessagesEl = document.getElementById("chatMessages");
  const chatInputEl = document.getElementById("chatInput");
  const chatSendButtonEl = document.getElementById("chatSendButton");

  // =========================
  // State
  // =========================
  let currentSessionId = null;
  let currentAssistantSlug = null;

  // =========================
  // Screen switching
  // =========================
  function setActiveScreen(name) {
    console.log("[mamino] showScreen:", name);

    screenHome.classList.remove("screen--active");
    screenAssistants.classList.remove("screen--active");
    screenChat.classList.remove("screen--active");

    if (name === "home") screenHome.classList.add("screen--active");
    if (name === "assistants") screenAssistants.classList.add("screen--active");
    if (name === "chat") screenChat.classList.add("screen--active");

    // таб "Чат" доступен только после создания сессии
    tabChat.disabled = !currentSessionId;

    // При показе чата — прокручиваем вниз
    if (name === "chat") {
      requestAnimationFrame(() => {
        if (chatMessagesEl) chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
      });
    }
  }

  // =========================
  // Chat render
  // =========================
  function clearChat() {
    if (!chatMessagesEl) return;
    chatMessagesEl.innerHTML = "";
  }

  function addChatMessage(role, text) {
    if (!chatMessagesEl) {
      console.warn("[mamino] chatMessagesEl not found");
      return;
    }

    const row = document.createElement("div");
    row.className = "msgRow " + (role === "user" ? "msgRow--user" : "msgRow--assistant");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    row.appendChild(bubble);
    chatMessagesEl.appendChild(row);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  // =========================
  // API
  // =========================
  async function apiCreateSession(assistantSlug, telegramId) {
    console.log("[mamino] apiCreateSession", assistantSlug);

    const res = await fetch(`${API_BASE}/chat/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assistant_slug: assistantSlug,
        telegram_id: telegramId,
      }),
    });

    if (!res.ok) {
      const txt = await safeText(res);
      console.error("[mamino] createSession error", res.status, txt);
      throw new Error("Не удалось создать сессию");
    }

    const data = await res.json();
    console.log("[mamino] session created", data);
    return data.session_id;
  }

  async function apiSendMessage(sessionId, assistantSlug, text) {
    console.log("[mamino] apiSendMessage", {
      currentSessionId: sessionId,
      currentAssistantSlug: assistantSlug,
      text,
    });

    const res = await fetch(`${API_BASE}/chat/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        assistant_slug: assistantSlug,
        message: text,
      }),
    });

    if (!res.ok) {
      const txt = await safeText(res);
      console.error("[mamino] send error", res.status, txt);
      throw new Error("Не удалось отправить сообщение");
    }

    const data = await res.json();
    console.log("[mamino] reply received", data, "session", res.status);
    return data;
  }

  async function safeText(res) {
    try { return await res.text(); } catch (_) { return ""; }
  }

  // =========================
  // Assistants UI
  // =========================
  function renderAssistants() {
    assistantsGrid.innerHTML = "";
    ASSISTANTS.forEach((a) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "assistantCard";
      btn.dataset.assistantSlug = a.slug;

      const t = document.createElement("div");
      t.className = "assistantCard__title";
      t.textContent = a.title;

      const d = document.createElement("div");
      d.className = "assistantCard__desc";
      d.textContent = a.description;

      btn.appendChild(t);
      btn.appendChild(d);

      btn.addEventListener("click", () => startChatWithAssistant(a.slug, a.title));

      assistantsGrid.appendChild(btn);
    });
  }

  // =========================
  // Chat flow
  // =========================
  async function startChatWithAssistant(slug, title) {
    const telegramId = getTelegramId();
    console.log("[mamino] telegramId =", telegramId);

    try {
      clearChat();
      currentAssistantSlug = slug;
      if (chatTitle) chatTitle.textContent = title;

      setActiveScreen("chat");
      addChatMessage("assistant", "Сейчас открою диалог…");

      const sessionId = await apiCreateSession(slug, telegramId);
      currentSessionId = sessionId;

      // Обновляем доступность вкладки
      tabChat.disabled = false;

      // Приветствие (не обязательное, но приятно)
      clearChat();
      addChatMessage("assistant", "Привет. Я рядом. Расскажите, что сейчас беспокоит больше всего?");

    } catch (e) {
      console.error("[mamino] error starting session", e);
      alert("Не удалось начать диалог. Проверьте соединение и попробуйте ещё раз.");
      setActiveScreen("assistants");
    }
  }

  async function handleSend() {
    const text = (chatInputEl?.value || "").trim();
    if (!text) return;

    if (!currentSessionId || !currentAssistantSlug) {
      alert("Сначала выберите ассистента.");
      return;
    }

    chatInputEl.value = "";
    addChatMessage("user", text);

    // временный индикатор
    const typingId = "typing-" + Date.now();
    addChatMessage("assistant", "…");
    const lastBubble = chatMessagesEl.lastElementChild?.querySelector(".bubble");
    if (lastBubble) lastBubble.dataset.typingId = typingId;

    try {
      const data = await apiSendMessage(currentSessionId, currentAssistantSlug, text);

      // удаляем "…"
      const bubbles = chatMessagesEl.querySelectorAll(".bubble");
      for (const b of bubbles) {
        if (b.dataset.typingId === typingId) {
          b.parentElement.remove();
          break;
        }
      }

      addChatMessage("assistant", data.reply);

    } catch (e) {
      console.error("[mamino] send failed", e);

      // удаляем "…"
      const bubbles = chatMessagesEl.querySelectorAll(".bubble");
      for (const b of bubbles) {
        if (b.dataset.typingId === typingId) {
          b.parentElement.remove();
          break;
        }
      }

      addChatMessage("assistant", "Не удалось получить ответ. Попробуйте ещё раз.");
    }
  }

  // =========================
  // Nav / Events
  // =========================
  function wireEvents() {
    goAssistantsBtn.addEventListener("click", () => setActiveScreen("assistants"));

    tabHome.addEventListener("click", () => setActiveScreen("home"));
    tabAssistants.addEventListener("click", () => setActiveScreen("assistants"));
    tabChat.addEventListener("click", () => {
      if (!currentSessionId) return;
      setActiveScreen("chat");
    });

    chatSendButtonEl.addEventListener("click", handleSend);
    chatInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSend();
      }
    });
  }

  // =========================
  // Boot
  // =========================
  function boot() {
    console.log("[mamino] main.js loaded");

    setupTelegramUi();
    renderAssistants();
    wireEvents();
    setActiveScreen("home");
  }

  boot();
})();
