// Здесь пока НЕТ запросов к backend — это дизайн/логика UI.
// Когда будем подключать API, можно будет заменить квиз-логику и добавить реальные ассистенты из БД.

// ==== DOM элементы ====

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

// ==== Статус ====

function setStatus(text) {
  if (!statusBar) return;
  statusBar.textContent = text || "";
}

// ==== Переключение экранов ====

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

// ==== Данные ассистентов по сегментам (из структуры заказчика) ====

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
      { name: "Мягкая подготовка к родам" },
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
    title: "Дети 3–7 лет (детский сад)",
    subtitle: "Речь, игры, концентрация и адаптация",
    assistants: [
      { name: "Ассистент речи и чтения" },
      { name: "Ассистент творческих игр" },
      { name: "Ассистент концентрации" },
      { name: "Ассистент “учим стихи без стресса”" },
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
    title: "Школьники (начальная школа 7–10 лет)",
    subtitle: "Домашка, режим и отношения",
    assistants: [
      { name: "Ассистент по домашке" },
      { name: "Ассистент дисциплины и мотивации" },
      { name: "Ассистент родителя в школе" },
      { name: "Ассистент “режим без криков”" },
      { name: "Ассистент общения с ребёнком на доверии" },
      { name: "Ассистент “игра в самостоятельность” (баллы, поощрения)" }
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
    title: "Школьники (средняя школа 11–14 лет)",
    subtitle: "Подростки, гаджеты, эмоции и будущее",
    assistants: [
      { name: "Ассистент общения без конфликтов" },
      { name: "Ассистент “дети и гаджеты”" },
      { name: "Ассистент эмоциональной устойчивости" },
      { name: "Ассистент выстраивания доверия" },
      { name: "Ассистент “профориентация”" },
      { name: "Ассистент уверенности (психоэмоциональные практики)" }
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
      { name: "Ассистент “где не выгореть”" },
      { name: "Ассистент бюджета семьи" },
      { name: "Ассистент “мама и личное время”" },
      { name: "Ассистент делегирования (чек-листы для детей, домашних и нянь)" }
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
    subtitle: "Опора, отношения с детьми и финансовая устойчивость",
    assistants: [
      { name: "Ассистент “Внутренняя опора”" },
      { name: "Ассистент “Разговор с ребёнком”" },
      { name: "Ассистент “Мой день без помощи”" },
      { name: "Ассистент “Мальчик без папы”" },
      { name: "Ассистент “Девочка без папы”" },
      { name: "Ассистент “Женщина, а не только мама”" },
      { name: "Ассистент “Финансовая самостоятельность”" }
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
    title: "Карта желаний",
    subtitle: "Мечты мамы и планы на жизнь",
    assistants: [
      { name: "Ассистент “Карта желаний для мамы”" }
    ],
    bonuses: []
  }
];

// ==== Рендер сегментов и ассистентов ====

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
        "В рабочей версии это будет отдельный ассистент с чек-листами, ответами и подсказками под этот запрос.";

      item.appendChild(titleRow);
      item.appendChild(desc);

      assistantList.appendChild(item);
    });

    if (segment.bonuses && segment.bonuses.length > 0) {
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
          "Дополнительный материал, чек-лист или мини-курс, который усиливает основной ассистент.";

        bItem.appendChild(bTitleRow);
        bItem.appendChild(bDesc);
        bonusList.appendChild(bItem);
      });

      const bonusLabel = document.createElement("div");
      bonusLabel.className = "assistant-desc";
      bonusLabel.textContent = "Бонусы, входящие в пакет:";

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

// ==== Быстрые запросы → переход в квиз с подсказкой ====

quickChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    const id = chip.getAttribute("data-quick");
    // Для простоты — просто открываем квиз и показываем статус
    showScreen("quiz");
    setStatus("Вы выбрали тему: " + chip.textContent.trim());
  });
});

// ==== Кнопка "Найти решение" ====

findSolutionBtn.addEventListener("click", () => {
  showScreen("quiz");
  setStatus("Ответьте на 3 вопроса, чтобы получить подбор ассистента.");
});

// ==== Навигация ====

navItems.forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.getAttribute("data-target");
    if (!target) return;
    showScreen(target);
    if (target === "assistants") {
      setStatus("Выберите актуальную тему или пройдите квиз подбора.");
    } else if (target === "favorites") {
      setStatus("Здесь будут храниться ваши избранные ответы и планы.");
    } else if (target === "profile") {
      setStatus("Профиль мамы: ассистенты, квизы, документы и оплата.");
    }
  });
});

// ==== Кнопки "Назад" ====

quizBackBtn.addEventListener("click", () => {
  showScreen("assistants");
  setStatus("Вы вернулись к списку ассистентов.");
});

resultBackBtn.addEventListener("click", () => {
  showScreen("assistants");
  setStatus("Можно выбрать другой ассистент или пройти квиз ещё раз.");
});

// ==== Квиз: логика подбора ассистента по ответам ====

function pickAssistantFromQuiz(stage, mainIssue) {
  // Очень упрощённая логика маппинга для демонстрации
  if (stage === "pregnant") {
    if (mainIssue === "mom_recovery" || mainIssue === "relations") {
      return {
        segmentTitle: "Беременным",
        assistantName: "Ассистент по состоянию (сон, тревожность, дыхание)",
        explanation:
          "Вы на этапе беременности и больше всего сейчас болит ваше состояние — тревоги, усталость, мысли. " +
          "Этот ассистент помогает выстроить мягкий режим, ритуалы, дыхательные практики и разговор с собой без самокритики."
      };
    }
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Беременным",
        assistantName: "Вкусная беременность",
        explanation:
          "Сейчас важно, чтобы питание поддерживало и вас, и малыша, но не превращалось в стресс. " +
          "Этот ассистент поможет выстроить простую и реальную систему, без жестких запретов и чувства вины."
      };
    }
    return {
      segmentTitle: "Беременным",
      assistantName: "Неделя за неделей. Ты и малыш",
      explanation:
        "На этапе беременности базовая опора — понимать, что происходит с вами и малышом. " +
        "Этот ассистент даёт неделевой формат: что норма, чего ожидать, какие вопросы задать врачу и как поддержать себя."
    };
  }

  if (stage === "baby_0_1") {
    if (mainIssue === "sleep") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Ассистент сна младенца",
        explanation:
          "Сон — самая частая и самая болезненная тема первых месяцев. " +
          "Ассистент поможет мягко выстроить ритуалы, понять, что в норме для возраста, и как уменьшить количество ночных пробуждений."
      };
    }
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Ассистент грудного вскармливания",
        explanation:
          "Грудное вскармливание — это и про тело, и про эмоции. " +
          "Ассистент поможет с позами, захватом, режимом и успокоит, если всё идёт не по идеальной схеме."
      };
    }
    if (mainIssue === "colic") {
      return {
        segmentTitle: "Малыши 0–1 год",
        assistantName: "Система высаживания от коликов",
        explanation:
          "Когда животик и колики мучают малыша, важно иметь понятный набор действий. " +
          "Ассистент даст конкретные шаги по высаживанию, рутине и способам мягко помочь ребёнку и себе."
      };
    }
    return {
      segmentTitle: "Малыши 0–1 год",
      assistantName: "Почему мой ребёнок плачет и как его успокоить",
      explanation:
        "Если кажется, что ребёнок плачет «просто так» и вы не понимаете, что делать, " +
        "этот ассистент поможет разложить варианты причин и подобрать подходящие способы успокоения."
    };
  }

  if (stage === "baby_1_3") {
    if (mainIssue === "feeding") {
      return {
        segmentTitle: "Малыши 1–3 года",
        assistantName: "Ассистент прикорма и меню",
        explanation:
          "Ассистент поможет выстроить прикорм и питание без войны за каждую ложку, " +
          "учитывая возраст, интерес ребёнка и ваш ресурс."
      };
    }
    if (mainIssue === "behavior") {
      return {
        segmentTitle: "Малыши 1–3 года",
        assistantName: "Ассистент по кризису трёх лет (поведение, истерики, границы)",
        explanation:
          "Когда начинается «я сам» и истерики, нужен понятный и спокойный взрослый рядом. " +
          "Ассистент подскажет, как реагировать, где ставить границы и как сохранять отношения тёплыми."
      };
    }
    return {
      segmentTitle: "Малыши 1–3 года",
      assistantName: "Ассистент горшка",
      explanation:
        "Вопрос горшка часто превращается в поле боя. " +
        "Ассистент поможет сделать этот процесс мягче, с уважением к ребёнку и вашим границам."
    };
  }

  if (stage === "child_3_7") {
    if (mainIssue === "behavior") {
      return {
        segmentTitle: "Дети 3–7 лет",
        assistantName: "Ассистент расписания дня и дисциплины",
        explanation:
          "Чтобы утро и вечер не превращались в марафон с криками, " +
          "ассистент поможет выстроить понятный ребёнку распорядок дня и систему договорённостей."
      };
    }
    if (mainIssue === "school") {
      return {
        segmentTitle: "Дети 3–7 лет",
        assistantName: "Ассистент адаптации к детсаду / школе",
        explanation:
          "Новое место, новые люди, много эмоций. " +
          "Ассистент подскажет, как подготовить ребёнка, как объяснять, что происходит, и когда стоит подключать специалистов."
      };
    }
    return {
      segmentTitle: "Дети 3–7 лет",
      assistantName: "Ассистент творческих игр",
      explanation:
        "Игры — лучший способ развития в этом возрасте. " +
        "Ассистент предложит идеи игр, которые подходят именно вашему возрасту и вашему типу ребёнка."
    };
  }

  if (stage === "school_7_10") {
    return {
      segmentTitle: "Школьники 7–10 лет",
      assistantName: "Ассистент по домашке",
      explanation:
        "Когда уроки забирают всё время и нервы, ассистент поможет выстроить систему: сколько времени, в каком порядке, " +
        "как мотивировать и когда можно отпускать контроль."
    };
  }

  if (stage === "school_11_14") {
    if (mainIssue === "relations") {
      return {
        segmentTitle: "Школьники 11–14 лет",
        assistantName: "Ассистент общения без конфликтов",
        explanation:
          "Подростковый возраст — испытание для всех. " +
          "Ассистент поможет говорить так, чтобы сохранять уважение и доверие, даже когда у всех бушуют эмоции."
      };
    }
    if (mainIssue === "school") {
      return {
        segmentTitle: "Школьники 11–14 лет",
        assistantName: "Ассистент “профориентация”",
        explanation:
          "Если уже сейчас хочется разобраться, к чему у ребёнка интерес и способности, " +
          "ассистент поможет задать правильные вопросы и наметить мягкие шаги."
      };
    }
    return {
      segmentTitle: "Школьники 11–14 лет",
      assistantName: "Ассистент эмоциональной устойчивости",
      explanation:
        "Ассистент поможет ребёнку (и вам) лучше понимать эмоции, проживать сложные состояния и не проваливаться в чувства «я ничего не могу»."
    };
  }

  if (stage === "multikids") {
    return {
      segmentTitle: "Многодетным",
      assistantName: "Ассистент расписания семьи",
      explanation:
        "С несколькими детьми важно не только выжить, но и не потерять себя. " +
        "Ассистент поможет разложить рутину, дела по дому, кружки и время мамы так, чтобы нагрузка стала понятнее и легче."
    };
  }

  if (stage === "solo_mom") {
    if (mainIssue === "money_time") {
      return {
        segmentTitle: "Соло-мамам",
        assistantName: "Ассистент “Финансовая самостоятельность”",
        explanation:
          "Ассистент поможет выстроить базовый финансовый план, понять, за счёт чего можно опереться и где добавлять доход без выгорания."
      };
    }
    return {
      segmentTitle: "Соло-мамам",
      assistantName: "Ассистент “Внутренняя опора”",
      explanation:
        "Когда вы одна с ребёнком, особенно важно иметь внутренний стержень. " +
        "Ассистент поможет поддержать себя, выстроить границы и перестать обвинять себя за всё на свете."
    };
  }

  // Fallback
  return {
    segmentTitle: "Мамины ассистенты",
    assistantName: "Базовый ассистент по ситуации мамы",
    explanation:
      "В полной версии ассистент задаст вам несколько уточняющих вопросов и сформирует план действий под вашу историю."
  };
}

// ==== Обработка отправки квиза ====

quizForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(quizForm);
  const stage = formData.get("stage") || "pregnant";
  const mainIssue = formData.get("main_issue") || "sleep";
  const severity = formData.get("severity") || "calm";

  const picked = pickAssistantFromQuiz(stage, mainIssue);

  // Составляем текст шагов с учётом "напряженности"
  let stepsText = "";
  if (severity === "calm") {
    stepsText =
      "1. Начать с мягких изменений — маленькие шаги без давления.\n" +
      "2. Отслеживать, что работает лучше всего именно в вашей семье.\n" +
      "3. Возвращаться к ассистенту, когда захочется идти глубже.";
  } else if (severity === "medium") {
    stepsText =
      "1. Определить 1–2 самые сложные точки в дне или неделе.\n" +
      "2. Взять готовый план из ассистента и адаптировать его под ваш ритм.\n" +
      "3. Добавить практики восстановления для вас, чтобы был ресурс эти изменения выдержать.";
  } else {
    stepsText =
      "1. Сначала стабилизировать ваше состояние: сон, минимум поддержки, убрать лишние требования к себе.\n" +
      "2. Выбрать самый острый симптом (сон, истерики или самочувствие) и работать только с ним.\n" +
      "3. Если тревога очень высокая — ассистент подскажет, какие формулировки использовать, обращаясь к специалистам.";
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
  setStatus("Это демонстрация результата. В боевой версии здесь будет конкретный ассистент и кнопка оплаты.");
});

// ==== "Подключить ассистента" и "Сохранить в избранное" (демо) ====

resultConnectBtn.addEventListener("click", () => {
  setStatus("В рабочей версии здесь будет оплата и подключение ассистента.");
});

resultFavoriteBtn.addEventListener("click", () => {
  const cardHtml = resultCard.innerHTML;
  favoritesEmpty.classList.add("hidden");

  const item = document.createElement("div");
  item.className = "result-card";
  item.innerHTML = cardHtml;

  favoritesList.appendChild(item);
  favoritesList.classList.remove("hidden");

  setStatus("Результат сохранён в избранное (демо).");
});

// ==== Telegram WebApp интеграция (пока мягко) ====

function initTelegram() {
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    // В дальнейшем можно будет взять tg.initDataUnsafe.user и подставить имя мамы
  }
}

// ==== Инициализация приложения ====

function initApp() {
  initTelegram();
  renderSegments();
  showScreen("assistants");
  setStatus("Это демонстрационный дизайн мини-приложения mamino.online. Можно показывать заказчице и обсуждать структуру.");
}

document.addEventListener("DOMContentLoaded", initApp);
