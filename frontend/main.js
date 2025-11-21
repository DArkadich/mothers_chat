// DEMO-РЕЖИМ: здесь НЕТ запросов к backend или OpenAI.
// Всё работает локально, чтобы показать интерфейс заказчице.

// Мнимая "база" ассистентов для демо
const DEMO_ASSISTANTS = [
    {
      id: 1,
      code: "pregnancy_emotions",
      title: "Эмоциональная поддержка при беременности",
      tag: "беременность",
      description: "Помогает справляться с тревогами, страхами и перепадами настроения.",
      note: "Говорим с вами человеческим языком, без осуждения."
    },
    {
      id: 2,
      code: "pregnancy_body",
      title: "Изменения в теле и самочувствие",
      tag: "самочувствие",
      description: "Объясняет, что с вами происходит на разных сроках и когда стоит обратиться к врачу.",
      note: "Не заменяет врача, но помогает разобраться в ощущениям."
    },
    {
      id: 3,
      code: "pregnancy_family",
      title: "Отношения и границы",
      tag: "семья",
      description: "Помогает выстраивать диалог с партнёром, родителями и окружением.",
      note: "Учитывает, что вы сейчас более уязвимы и чувствительны."
    }
  ];
  
  // Эмуляция "пользователя"
  const DEMO_USER = {
    first_name: "Аня",
    username: "mama_demo",
    segment: "pregnant",
    week: 28
  };
  
  let currentAssistant = null;
  let isSending = false;
  
  // DOM элементы
  const userInfoEl = document.getElementById("user-info");
  const assistantsListEl = document.getElementById("assistants-list");
  const chatTitleEl = document.getElementById("chat-title");
  const chatWindowEl = document.getElementById("chat-window");
  const chatFormEl = document.getElementById("chat-form");
  const chatInputEl = document.getElementById("chat-input");
  const statusBarEl = document.getElementById("status-bar");
  
  // Устанавливаем статус
  function setStatus(text) {
    statusBarEl.textContent = text || "";
  }
  
  // Добавляем сообщение в чат
  function appendMessage(role, text) {
    const msgEl = document.createElement("div");
    msgEl.classList.add("chat-message");
    msgEl.classList.add(role === "user" ? "user" : "assistant");
    msgEl.textContent = text;
    chatWindowEl.appendChild(msgEl);
    chatWindowEl.scrollTop = chatWindowEl.scrollHeight;
  }
  
  // Рендер демо-пользователя
  function initDemoUser() {
    const name = DEMO_USER.first_name || DEMO_USER.username;
    const week = DEMO_USER.week;
    userInfoEl.textContent = `Вы: ${name}, примерно ${week} неделя беременности (демо).`;
  }
  
  // Рендер ассистентов
  function renderAssistants(list) {
    assistantsListEl.innerHTML = "";
  
    list.forEach((a) => {
      const item = document.createElement("div");
      item.classList.add("assistant-item");
  
      const titleRow = document.createElement("div");
      titleRow.classList.add("assistant-title-row");
  
      const title = document.createElement("div");
      title.classList.add("assistant-title");
      title.textContent = a.title;
  
      const tag = document.createElement("div");
      tag.classList.add("assistant-tag");
      tag.textContent = a.tag;
  
      titleRow.appendChild(title);
      titleRow.appendChild(tag);
  
      const desc = document.createElement("div");
      desc.classList.add("assistant-description");
      desc.textContent = a.description;
  
      const note = document.createElement("div");
      note.classList.add("assistant-note");
      note.textContent = a.note;
  
      item.appendChild(titleRow);
      item.appendChild(desc);
      item.appendChild(note);
  
      item.addEventListener("click", () => {
        currentAssistant = a;
        updateActiveAssistant();
      });
  
      assistantsListEl.appendChild(item);
    });
  }
  
  // Подсветка активного ассистента и приветствие
  function updateActiveAssistant() {
    const items = assistantsListEl.querySelectorAll(".assistant-item");
    items.forEach((item) => item.classList.remove("active"));
  
    if (!currentAssistant) {
      chatTitleEl.textContent = "Чат с ассистентом";
      return;
    }
  
    chatTitleEl.textContent = `Чат: ${currentAssistant.title}`;
  
    // Подсветить активного
    const children = Array.from(assistantsListEl.children);
    children.forEach((el) => {
      const titleEl = el.querySelector(".assistant-title");
      if (titleEl && titleEl.textContent === currentAssistant.title) {
        el.classList.add("active");
      }
    });
  
    // Очистить чат и показать приветственное сообщение ассистента
    chatWindowEl.innerHTML = "";
    appendMessage(
      "assistant",
      getWelcomeTextForAssistant(currentAssistant)
    );
  
    setStatus(`Вы выбрали ассистента: «${currentAssistant.title}»`);
  }
  
  // Генерация приветствия в зависимости от ассистента
  function getWelcomeTextForAssistant(assistant) {
    if (!assistant) {
      return "Выберите ассистента слева и напишите свой вопрос.";
    }
  
    switch (assistant.code) {
      case "pregnancy_emotions":
        return (
          "Я здесь, чтобы поддержать вас эмоционально.\n\n" +
          "Можете написать, что больше всего тревожит сейчас: страхи, мысли о родах, отношения с близкими или что-то ещё."
        );
      case "pregnancy_body":
        return (
          "Расскажите, на каком вы сейчас сроке и что беспокоит в теле: боли, усталость, изменения настроения.\n\n" +
          "Я помогу объяснить, что может быть нормой, а когда важно обратиться к врачу."
        );
      case "pregnancy_family":
        return (
          "Иногда беременность обостряет старые конфликты и поднимает новые темы.\n\n" +
          "Можете описать ситуацию с партнёром или близкими — попробуем вместе найти мягкий, но понятный способ поговорить."
        );
      default:
        return "Я готов помочь. Напишите, что сейчас больше всего хочется обсудить.";
    }
  }
  
  // Простая генерация “умного, но демо” ответа
  function generateDemoReply(assistant, userMessage) {
    const text = userMessage.trim();
    const base =
      "Сейчас я работаю в демо-режиме и показываю, как может выглядеть ответ. В живой версии здесь будет персональный ИИ, обученный под ваш запрос.\n\n";
  
    if (!assistant) {
      return (
        base +
        "Вы пока не выбрали ассистента. В живом приложении вы сможете общаться с разными помощниками: по эмоциям, самочувствию и отношениям."
      );
    }
  
    if (assistant.code === "pregnancy_emotions") {
      return (
        base +
        "Я слышу, что вам нелегко, и это нормально — беременность действительно может усиливать тревожность.\n\n" +
        "1) Для начала давайте признаем: то, что вы чувствуете, не делает вас «слабой» или «плохой мамой».\n" +
        "2) Полезно разделять факты и страшные мысли — в реальной версии ассистент поможет вам это аккуратно разложить.\n" +
        "3) Также можно подобрать мягкие ритуалы перед сном и техники заземления.\n\n" +
        "В боевой версии вы получите конкретные шаги и формулировки под вашу ситуацию."
      );
    }
  
    if (assistant.code === "pregnancy_body") {
      return (
        base +
        "Многие ощущения во время беременности могут пугать, особенно если это первый опыт.\n\n" +
        "В рабочей версии ассистент:\n" +
        "• уточнит срок, интенсивность симптомов,\n" +
        "• подскажет, какие признаки выглядят как вариант нормы,\n" +
        "• а какие — повод обязательно связаться с врачом.\n\n" +
        "Сейчас важно, что вы не остаётесь с этим одна — даже демо уже показывает формат поддержки."
      );
    }
  
    if (assistant.code === "pregnancy_family") {
      return (
        base +
        "Тема отношений во время беременности особенно чувствительная.\n\n" +
        "В полной версии ассистент поможет:\n" +
        "• сформулировать, что именно вы хотите донести до партнёра или родных;\n" +
        "• подобрать мягкие, но честные фразы без обвинений;\n" +
        "• продумать, как сохранить границы и не перегореть.\n\n" +
        "Демо показывает пример формата: вы описываете ситуацию, а ИИ помогает разложить её по полочкам."
      );
    }
  
    return (
      base +
      "Вы задали вопрос, и в полной версии ассистент ответит на него с учётом вашего срока, контекста и предыдущих диалогов."
    );
  }
  
  // Обработчик отправки сообщения
  function handleSendMessage(event) {
    event.preventDefault();
  
    const text = chatInputEl.value.trim();
    if (!text || isSending) {
      return;
    }
  
    if (!currentAssistant) {
      setStatus("Сначала выберите ассистента слева.");
      return;
    }
  
    isSending = true;
    chatFormEl.querySelector("button").disabled = true;
    setStatus("Формируем ответ (демо)…");
  
    appendMessage("user", text);
    chatInputEl.value = "";
  
    // Эмуляция задержки "обдумывания"
    setTimeout(() => {
      const reply = generateDemoReply(currentAssistant, text);
      appendMessage("assistant", reply);
      setStatus("Ответ сгенерирован в демо-режиме. В реальной версии здесь будет ИИ.");
      isSending = false;
      chatFormEl.querySelector("button").disabled = false;
    }, 700);
  }
  
  // Инициализация приложения
  function initApp() {
    // На этом шаге мы не используем Telegram.initData, но можем аккуратно проверить наличие
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
    }
  
    initDemoUser();
    renderAssistants(DEMO_ASSISTANTS);
  
    // Автоматически выбираем первого ассистента
    currentAssistant = DEMO_ASSISTANTS[0];
    updateActiveAssistant();
  
    chatFormEl.addEventListener("submit", handleSendMessage);
  
    setStatus("Это демо-версия без сервера. Можно пробовать писать вопросы и смотреть интерфейс.");
  }
  
  document.addEventListener("DOMContentLoaded", initApp);
  