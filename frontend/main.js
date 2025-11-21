// Логика демо-версии MAMINO: сегменты, ассистенты, квиз, избранное.
// Пока без реального backend и OpenAI — это презентационный фронт для согласования визуала и UX.

const screens = document.querySelectorAll(".screen");
const navItems = document.querySelectorAll(".nav-item");
const statusBar = document.getElementById("status-bar");

const segmentsContainer = document.getElementById("segments-container");

const findSolutionBtn = document.getElementById("find-solution-btn");
const quizScreen = document.querySelector('[data-screen="quiz"]');
const quizForm = document.getElementById("quiz-form");
const quizBackBtn = document.getElementById("quiz-back-btn");

const resultScreen = document.querySelector('[data-screen="result"]');
const resultCard = document.getElementById("result-card");
const resultBackBtn = document.getElementById("result-back-btn");
const resultConnectBtn = document.getElementById("result-connect-btn");
const resultFavoriteBtn = document.getElementById("result-favorite-btn");

const favoritesList = document.getElementById("favorites-list");
const favoritesEmpty = document.getElementById("favorites-empty");

const quickChips = document.querySelectorAll(".quick-chip");

// Статус-строка
function setStatus(text) {
  if (!statusBar) return;
  statusBar.textContent = text || "";
}

// Переключение экранов
function showScreen(name) {
  screens.forEach((s) => {
    const screenName = s.getAttribute("data-screen");
    if (screenName === name) {
      s.classList.add("screen-active");
    } else {
      s.classList.remove("screen-active");
    }
  });

  navItems.forEach((btn) => {
    const target = btn.getAttribute("data-target");
    if (target === name) {
      btn.classList.add("nav-item-active");
    } else {
      btn.classList.remove("nav-item-active");
    }
  });
}

// Структура сегментов и ассистентов (по брифу заказчицы)
const SEGMENTS = [
  {
    id: "pregnant",
    title: "Беременным",
    subtitle: "Поддержка от теста до родов",
    assistants: [
      { name: "Неделя за неделей. Ты и малыш" },
      { name: "Вкусная беременность" },
      { name: "Красивая беременность" },
      { name: "Тело без боли: спорт, отёки, судороги" },
      { name: "Ассистент по состоянию (сон, тревожность, дыхание)" },
      { name: "Мягкая подготовка к родам" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "baby_0_1",
    title: "Малыши 0–1 год",
    subtitle: "Сон, грудь, животик и мама после родов",
    assistants: [
      { name: "Ассистент сна младенца" },
      { name: "Ассистент грудного вскармливания" },
      { name: "Ассистент стула и питания" },
      { name: "Ассистент ухода за мамой после родов" },
      { name: "Почему мой ребёнок плачет и как его успокоить" },
      { name: "Система высаживания от коликов" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 1",
      "Бонус 2",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "baby_1_3",
    title: "Малыши 1–3 года",
    subtitle: "Прикорм, горшок, привычки и кризис трёх лет",
    assistants: [
      { name: "Ассистент прикорма и меню" },
      { name: "Ассистент горшка" },
      { name: "Ассистент игр и развития по возрасту" },
      { name: "Ассистент формирования привычек (сон, еда, зубы)" },
      { name: "Ассистент мягкого отлучения от соски" },
      { name: "Ассистент по кризису трёх лет (поведение, истерики, границы)" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "child_3_7",
    title: "Дети 3–7 лет (сад)",
    subtitle: "Речь, игры, концентрация и адаптация",
    assistants: [
      { name: "Ассистент речи и чтения" },
      { name: "Ассистент творческих игр" },
      { name: "Ассистент концентрации" },
      { name: "Ассистент «учим стихи без стресса»" },
      { name: "Ассистент расписания дня и дисциплины" },
      { name: "Ассистент адаптации к детсаду / школе" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "school_7_10",
    title: "Школьники 7–10 лет",
    subtitle: "Домашка, режим и отношения",
    assistants: [
      { name: "Ассистент по домашке" },
      { name: "Ассистент дисциплины и мотивации" },
      { name: "Ассистент родителя в школе" },
      { name: "Ассистент «режим без криков»" },
      { name: "Ассистент общения на доверии" },
      { name: "Ассистент «игра в самостоятельность»" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "school_11_14",
    title: "Школьники 11–14 лет",
    subtitle: "Подростки, гаджеты, эмоции и будущее",
    assistants: [
      { name: "Ассистент общения без конфликтов" },
      { name: "Ассистент «дети и гаджеты»" },
      { name: "Ассистент эмоциональной устойчивости" },
      { name: "Ассистент выстраивания доверия" },
      { name: "Ассистент «профориентация»" },
      { name: "Ассистент уверенности" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "multikids",
    title: "Многодетным",
    subtitle: "Расписание, рутина, ресурсы и деньги",
    assistants: [
      { name: "Ассистент расписания семьи" },
      { name: "Ассистент рутины и дел" },
      { name: "Ассистент «где не выгореть»" },
      { name: "Ассистент бюджета семьи" },
      { name: "Ассистент «мама и личное время»" },
      { name: "Ассистент делегирования и чек-листов" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "solo_mom",
    title: "Соло-мамам",
    subtitle: "Опора, отношения и финансовая устойчивость",
    assistants: [
      { name: "Ассистент «Внутренняя опора»" },
      { name: "Ассистент «Разговор с ребёнком»" },
      { name: "Ассистент «Мой день без помощи»" },
      { name: "Ассистент «Мальчик без папы»" },
      { name: "Ассистент «Девочка без папы»" },
      { name: "Ассистент «Женщина, а не только мама»" },
      { name: "Ассистент «Финансовая самостоятельность»" }
    ],
    bonuses: [
      "Бонус 1",
      "Бонус 1",
      "Бонус 1",
      "Бонус 2",
      "Бонус 3"
    ]
  },
  {
    id: "dream_map",
    title: "Карта желаний мамы",
    subtitle: "Мечты, планы и свои желания",
    assistants: [
      { name: "Ассистент «Карта желаний для мамы»" }
    ],
    bonuses: []
  }
];

// Рендер сегментов
function renderSegments() {
  segmentsContainer.innerHTML = "";

  SEGMENTS.forEach((segment, index) => {
    const card = document.createElement("div");
    card.className = "segment-card";

    const header = document.createElement("div");
    header.className = "segment-header";

    const main = document.createElement("div");
    main.className = "segment-main";

    const title = document.createElement("div");
    title.className = "segment-title";
    title.textContent = segment.title;

    const subtitle = document.createElement("div");
    subtitle.className = "segment-subtitle";
    subtitle.textContent = segment.subtitle;

    main.appendChild(title);
    main.appendChild(subtitle);

    const toggle = document.createElement("div");
    toggle.className = "segment-toggle";
    toggle.textContent = index === 0 ? "−" : "+";

    header.appendChild(main);
    header.appendChild(toggle);

    const body = document.createElement("div");
    body.className = "segment-body";
    if (index === 0) {
      body.classList.add("segment-body-open");
    }

    const assistantList = document.createElement("div");
    assistantList.className = "assistant-list";

    segment.assistants.forEach((asst) => {
      const item = document.createElement("div");
      item.className = "assistant-item";

      const titleRow = document.createElement("div");
      titleRow.className = "assistant-title-row";

      const atitle = document.createElement("div");
      atitle.className = "assistant-title";
      atitle.textContent = asst.name;

      const pill = document.createElement("div");
      pill.className = "assistant-pill";
      pill.textContent = "ИИ-ассистент";

      titleRow.appendChild(atitle);
      titleRow.appendChild(pill);

      const desc = document.createElement("div");
      desc.className = "assistant-desc";
      desc.textContent =
        "В рабочей версии это будет отдельный ассистент с подсказками, сценариями и чек-листами под эту тему.";

      item.appendChild(titleRow);
      item.appendChild(desc);

      assistantList.appendChild(item);
    });

    if (segment.bonuses && segment.bonuses.length > 0) {
      const bonusLabel = document.createElement("div");
      bonusLabel.className = "assistant-desc";
      bonusLabel.textContent = "Бонусы, усиливающие этот этап:";

      const bonusList = document.createElement("div");
      bonusList.className = "assistant-list";

      segment.bonuses.forEach((b) => {
        const bItem = document.createElement("div");
        bItem.className = "assistant-item";

        const bTitleRow = document.createElement("div");
        bTitleRow.className = "assistant-title-row";

        const bTitle = document.createElement("div");
        bTitle.className = "assistant-title";
        bTitle.textContent = b;

        const pill = document.createElement("div");
        pill.className = "assistant-pill";
        pill.textContent = "бонус";

        bTitleRow.appendChild(bTitle);
        bTitleRow.appendChild(pill);

        const bDesc = document.createElement("div");
        bDesc.className = "assistant-desc";
        bDesc.textContent =
          "В демо это условный бонус. В продукте — чек-листы, мини-курсы или поддерживающие материалы.";

        bItem.appendChild(bTitleRow);
        bItem.appendChild(bDesc);
        bonusList.appendChild(bItem);
      });

      body.appendChild(bonusLabel);
      body.appendChild(bonusList);
    }

    body.appendChild(assistantList);

    header.addEventListener("click", () => {
      const isOpen = body.classList.contains("segment-body-open");
      if (isOpen) {
        body.classList.remove("segment-body-open");
        toggle.textContent = "+";
      } else {
        body.classList.add("segment-body-open");
        toggle.textContent = "−";
      }
    });

    card.appendChild(header);
    card.appendChild(body);
    segmentsContainer.appendChild(card);
  });
}

// Быстрые темы → квиз
quickChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    showScreen("quiz");
    setStatus("Тема: " + chip.textContent.trim() + ". Ответьте на вопросы, чтобы получить подбор.");
  });
});

// Кнопка "Подобрать решение"
findSolutionBtn.addEventListener("click", () => {
  showScreen("quiz");
  setStatus("Ответьте на 3 вопроса — и мы предложим ассистента под вашу ситуацию.");
});

// Навигация
navItems.forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.getAttribute("data-target");
    if (!target) return;
    showScreen(target);
    if (target === "assistants") {
      setStatus("Выберите тему или пройдите подбор.");
    } else if (target === "favorites") {
      setStatus("Здесь будут ваши сохранённые подборы и ответы ассистентов.");
    } else if (target === "profile") {
      setStatus("Профиль мамы и документы сервиса MAMINO.");
    }
  });
});

// Назад из квиза и результата
quizBackBtn.addEventListener("click", () => {
  showScreen("assistants");
  setStatus("Вы вернулись к ассистентам.");
});

resultBackBtn.addEventListener("click", () => {
  showScreen("assistants");
  setStatus("Можно выбрать другую тему или пройти подбор ещё раз.");
});

// Подбор ассистента по квизу (простая логика для демо)
function pickAssistantFromQuiz(stage, mainIssue) {
  if (stage === "pregnant") {
    if (mainIssue === "mom_recovery" || mainIssue === "relations") {
      return {
        segmentTitle: "Беременным",
        assistantName: "Ассистент по состоянию (сон, тревожность, дыхание)",
        explanation:
          "Беременность — время, когда эмоции и тело меняются одновременно. Этот ассистент помогает выстроить мягкий режим, " +
          "подобрать ритуалы сна и дыхательные практики, чтобы вы чувствовали больше опоры."
      };
    }
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Беременным",
        assistantName: "Вкусная беременность",
        explanation:
          "Никаких идеальных диет. Ассистент помогает собрать реальное, живое меню под ваши предпочтения, ограничения врача и уровень сил."
      };
    }
    return {
      segmentTitle: "Беременным",
      assistantName: "Неделя за неделей. Ты и малыш",
      explanation:
        "Если хочется понимать, что происходит с вами и малышом, — этот ассистент даёт неделевой формат: норма, риски, вопросы к врачу и мягкая поддержка."
    };
  }

  if (stage === "baby_0_1") {
    if (mainIssue === "sleep") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Ассистент сна младенца",
        explanation:
          "Сон ребёнка — один из главных источников тревоги. Ассистент помогает выстроить ритуалы, понять особенности сна по возрасту " +
          "и снизить количество ночных качелей."
      };
    }
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Ассистент грудного вскармливания",
        explanation:
          "Грудное вскармливание — это про тело, эмоции и отношения с ребёнком. Ассистент помогает с позами, захватом, режимом и снижает чувство вины, " +
          "если всё идёт не по книжке."
      };
    }
    if (mainIssue === "colic") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Система высаживания от коликов",
        explanation:
          "Когда животик и колики мучают малыша, важно иметь понятный набор действий. Ассистент даёт пошаговый план, чтобы помочь ребёнку и не потерять себя."
      };
    }
    return {
      segmentTitle: "Малыши 0–1 год",
      assistantName: "Почему мой ребёнок плачет и как его успокоить",
      explanation:
        "Ассистент помогает разложить возможные причины плача и подбирает подходящие способы успокоения, исходя из возраста и контекста."
    };
  }

  if (stage === "baby_1_3") {
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Малыши 1–3 года",
        assistantName: "Ассистент прикорма и меню",
        explanation:
          "Когда каждый приём пищи — поле боя, ассистент помогает выстроить систему питания без угроз и шантажа «ещё ложечку — и мультик»."
      };
    }
    if (mainIssue === "behavior") {
      return {
        segmentTitle: "Малыши 1–3 года",
        assistantName: "Ассистент по кризису трёх лет",
        explanation:
          "Кризис трёх лет — это «я сам», истерики и испытание границ. Ассистент помогает реагировать спокойно и при этом не растворяться в требованиях ребёнка."
      };
    }
    return {
      segmentTitle: "Малыши 1–3 года",
      assistantName: "Ассистент горшка",
      explanation:
        "Ассистент превращает историю с горшком из стресса в понятный процесс: когда начинать, как объяснять и что делать, если ребёнок сопротивляется."
    };
  }

  if (stage === "child_3_7") {
    if (mainIssue === "behavior") {
      return {
        segmentTitle: "Дети 3–7 лет",
        assistantName: "Ассистент расписания дня и дисциплины",
        explanation:
          "Ассистент помогает выстроить понятный ребёнку распорядок: утро, сад, вечерние ритуалы — так, чтобы взрослая жизнь тоже влезла."
      };
    }
    if (mainIssue === "school") {
      return {
        segmentTitle: "Дети 3–7 лет",
        assistantName: "Ассистент адаптации к детсаду / школе",
        explanation:
          "Первые коллективы — большой стресс. Ассистент помогает подготовить ребёнка, проживать слёзы и замечания и поддерживать себя."
      };
    }
    return {
      segmentTitle: "Дети 3–7 лет",
      assistantName: "Ассистент творческих игр",
      explanation:
        "Если не хватает идей, чем заняться, ассистент предлагает игры под возраст и характер ребёнка — без килограмма развивающих пособий."
    };
  }

  if (stage === "school_7_10") {
    return {
      segmentTitle: "Школьники 7–10 лет",
      assistantName: "Ассистент по домашке",
      explanation:
        "Домашка не должна съедать всю семью. Ассистент помогает договориться о времени, распределить нагрузку и снизить конфликты вокруг уроков."
    };
  }

  if (stage === "school_11_14") {
    if (mainIssue === "relations") {
      return {
        segmentTitle: "Школьники 11–14 лет",
        assistantName: "Ассистент общения без конфликтов",
        explanation:
          "Подростковый возраст — испытание для всех. Ассистент помогает говорить так, чтобы сохранять доверие, даже когда у всех внутри буря."
      };
    }
    if (mainIssue === "school") {
      return {
        segmentTitle: "Школьники 11–14 лет",
        assistantName: "Ассистент «профориентация»",
        explanation:
          "Если хочется понимать, к чему у ребёнка интерес и способности, ассистент подскажет вопросы, шаги и безопасные форматы проб."
      };
    }
    return {
      segmentTitle: "Школьники 11–14 лет",
      assistantName: "Ассистент эмоциональной устойчивости",
      explanation:
        "Ассистент помогает ребёнку (и вам) лучше понимать эмоции, проживать сложные состояния и не оставаться с этим в одиночестве."
    };
  }

  if (stage === "multikids") {
    return {
      segmentTitle: "Многодетным",
      assistantName: "Ассистент расписания семьи",
      explanation:
        "Ассистент помогает разложить по полочкам всех детей, кружки, дом и ваши дела, чтобы дать ощущение управляемости вместо хаоса."
    };
  }

  if (stage === "solo_mom") {
    if (mainIssue === "money_time") {
      return {
        segmentTitle: "Соло-мамам",
        assistantName: "Ассистент «Финансовая самостоятельность»",
        explanation:
          "Ассистент помогает сделать первые шаги к более устойчивому доходу, не загоняя вас в ещё одно выгорание."
      };
    }
    return {
      segmentTitle: "Соло-мамам",
      assistantName: "Ассистент «Внутренняя опора»",
      explanation:
        "Когда вы одна с ребёнком, особенно важно иметь внутренний стержень. Ассистент помогает поддержать себя, выстроить границы и убрать лишнее самобичевание."
    };
  }

  return {
    segmentTitle: "MAMINO",
    assistantName: "Базовый ассистент по ситуации мамы",
    explanation:
      "В полной версии ассистент задаст ещё несколько вопросов и соберёт маршрут под вашу историю: от первых шагов до расширенного плана."
  };
}

// Обработка отправки квиза
quizForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(quizForm);
  const stage = formData.get("stage") || "pregnant";
  const mainIssue = formData.get("main_issue") || "sleep";
  const severity = formData.get("severity") || "calm";

  const picked = pickAssistantFromQuiz(stage, mainIssue);

  let stepsText = "";
  if (severity === "calm") {
    stepsText =
      "1. Начать с маленьких изменений, которые не требуют от вас сверхусилий.\n" +
      "2. Отслеживать, что даёт облегчение именно вашей семье.\n" +
      "3. Возвращаться к ассистенту, когда появится ресурс идти глубже.";
  } else if (severity === "medium") {
    stepsText =
      "1. Выделить 1–2 самые болезненные точки в дне.\n" +
      "2. Взять готовый план из ассистента и адаптировать под ваш ритм.\n" +
      "3. Добавить простые практики восстановления для вас, чтобы хватило сил на изменения.";
  } else {
    stepsText =
      "1. Сначала стабилизировать ваше состояние: сон, минимум поддержки, убрать лишние требования к себе.\n" +
      "2. Выбрать один самый острый симптом (сон, истерики, здоровье) и работать только с ним.\n" +
      "3. Если тревога зашкаливает — ассистент подскажет, как мягко обратиться за поддержкой к специалистам.";
  }

  resultCard.innerHTML = `
    <div class="result-segment">${picked.segmentTitle}</div>
    <div class="result-assistant-name">${picked.assistantName}</div>
    <div class="result-explainer">${picked.explanation}</div>
    <ol class="result-steps">
      ${stepsText
        .split("\n")
        .map((line) => `<li>${line.replace(/^\d+\.\s*/, "")}</li>`)
        .join("")}
    </ol>
  `;

  showScreen("result");
  setStatus("Это демонстрация подбора. В продукте здесь появится живой ассистент и кнопка оплаты.");
});

// Подключение ассистента (демо)
resultConnectBtn.addEventListener("click", () => {
  setStatus("В рабочей версии здесь будет оплата и открытие доступа к ассистенту.");
});

// Сохранение в избранное
resultFavoriteBtn.addEventListener("click", () => {
  const cardHtml = resultCard.innerHTML;
  favoritesEmpty.classList.add("hidden");

  const item = document.createElement("div");
  item.className = "result-card";
  item.innerHTML = cardHtml;

  favoritesList.appendChild(item);
  favoritesList.classList.remove("hidden");

  setStatus("Подбор сохранён в избранное (демо-режим).");
});

// Telegram WebApp интеграция (мягкая, без логики)
function initTelegram() {
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
  }
}

// Android-фиксы: убираем 100vh+fixed-ад для WebView
function applyAndroidFixesIfNeeded() {
  if (/Android/i.test(navigator.userAgent)) {
    document.body.classList.add("is-android");
  }
}

// Инициализация
function initApp() {
  applyAndroidFixesIfNeeded();
  initTelegram();
  renderSegments();
  showScreen("assistants");
  setStatus("Это демо-версия интерфейса MAMINO для согласования визуала и структуры.");
}

document.addEventListener("DOMContentLoaded", initApp);
