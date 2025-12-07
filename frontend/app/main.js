// Простейший SPA-роутер + данные ассистентов 0–1 и "Вкусная беременность".

const mcScreens = {};
let currentScreen = "home";

// Описание ассистентов (по тексту с макетов)
const ASSISTANTS = {
  newborn_first_days: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "",
    title: "АССИСТЕНТ «НАШИ ПЕРВЫЕ ДНИ ВМЕСТЕ»",
    lead:
      "Когда вы приезжаете домой из роддома и нужно понимание: почему малыш плачет, сколько он должен спать, как его купать и что считать нормой. Ассистент помогает спокойно пройти первые недели.",
    does: [
      "Даёт понятный распорядок дня новорождённого",
      "Объясняет, что обычно норма, а что повод уточнить у специалиста",
      "Рассказывает про уход: пупок, купание, подмывание, одевание",
      "Помогает понять малыша и действовать уверенно"
    ],
    gets: [
      "Чёткий план, что делать каждый день / каждый час",
      "Понимание, что происходит и почему",
      "Уверенность: «Мы справляемся»"
    ]
  },
  sleep_0_1: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "",
    title: "АССИСТЕНТ «МАЛЫШ СПИТ СЛАДКО»",
    lead:
      "Когда малыш спит по 20 минут, путает день и ночь, а засыпание возможно только на руках или груди — этот ассистент помогает наладить мягкий, понятный режим сна по возрасту.",
    does: [
      "Объясняет сон по этапам: 0–3, 3–6, 6–12 месяцев",
      "Даёт ориентиры бодрствования",
      "Помогает выстроить спокойное укладывание",
      "Показывает, как постепенно убрать грудь/руки из засыпания"
    ],
    gets: [
      "Более длинные и спокойные сны",
      "Часы отдыха для мамы",
      "Укладывания без истерик"
    ]
  },
  breastfeeding: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "",
    title: "АССИСТЕНТ «МОЛОЧНАЯ МАМА»",
    lead:
      "Когда кормление больно, появляются трещины, малыш кажется голодным или грудь становится плотной — этот ассистент помогает настроить грудное вскармливание мягко и без стресса.",
    does: [
      "Объясняет прикладывание и показывает удобные позы",
      "Подсказывает, как уменьшить боль и напряжение в груди",
      "Помогает понять, ест ли малыш достаточно",
      "Рассказывает о сцеживании и докорме без чувства вины"
    ],
    gets: [
      "Кормление без боли",
      "Молоко есть",
      "Понимание, что происходит и как помочь себе",
      "Уверенность в своих силах и спокойный настрой"
    ]
  },
  cry: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "Тариф Smart",
    title: "АССИСТЕНТ «ПОЧЕМУ МАЛЫШ ПЛАЧЕТ?»",
    lead:
      "Когда малыш плачет, а ты не можешь понять — он голодный, устал, хочет на руки или ему что-то мешает — этот ассистент помогает разобраться, что стоит за разными видами плача.",
    does: [
      "Объясняет типы плача и их признаки",
      "Помогает отличить голод, усталость и дискомфорт",
      "Подсказывает, как мягко реагировать",
      "Показывает, когда плач норма, а когда лучше уточнить у специалиста"
    ],
    gets: [
      "Понимание малыша, а не угадывание",
      "Уверенность в своих действиях",
      "Спокойнее реагируете на плач"
    ]
  },
  day_routine: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "Тариф Smart",
    title: "АССИСТЕНТ «ДЕНЬ В ПОРЯДКЕ. РЕЖИМ, КОТОРЫЙ РАБОТАЕТ НА ТЕБЯ»",
    lead:
      "Когда малыш спит и ест хаотично, а мама не успевает даже поесть или прийти в себя, этот ассистент помогает выстроить понятный и удобный ритм дня — без строгих правил и давления.",
    does: [
      "Создаёт реалистичный режим под возраст ребёнка",
      "Учитывает ваш семейный темп",
      "Подсказывает окна бодрствования",
      "Помогает синхронизировать день мамы и малыша",
      "Объясняет мягкие переходы между возрастами"
    ],
    gets: [
      "Предсказуемый день",
      "Больше времени на себя",
      "Меньше хаоса и перегруза"
    ]
  },
  mom_rest: {
    segmentTitle: "Малыши 0–1 год",
    segmentSubtitle: "Сон, грудь, животик и мама после родов",
    tariff: "Тариф Pro",
    title: "АССИСТЕНТ «МАМА ОТДЫХАЕТ»",
    lead:
      "Когда дни проходят в кормлениях и пелёнках, а на себя нет ни минуты, этот ассистент помогает вернуть ощущение жизни, а не бесконечного сервиса 24/7.",
    does: [
      "Помогает встроить сон, еду и душ в реальный день с малышом",
      "Даёт простые способы восстановления тела и головы",
      "Подсказывает, как просить и принимать помощь",
      "Объясняет, почему усталость — это не слабость"
    ],
    gets: [
      "Ощущение «я тоже человек»",
      "Больше сил и спокойствия",
      "День, где мама тоже важна"
    ]
  },
  tasty_pregnancy: {
    segmentTitle: "Беременным",
    segmentSubtitle: "Поддержка от теста до родов",
    tariff: "",
    title: "АССИСТЕНТ «ВКУСНАЯ БЕРЕМЕННОСТЬ»",
    lead:
      "Когда мучают тошнота, изжога, отвращение к еде и страх «ем ли я правильно», этот ассистент помогает есть спокойно.",
    does: [
      "Учитывает твой срок и самочувствие",
      "Подбирает еду, которая легче переносится",
      "Даёт идеи перекусов и блюд",
      "Помогает понять, на какую систему спокойно можно опираться в питании"
    ],
    gets: [
      "Легче переносишь токсикоз",
      "Не боишься еды",
      "Питаешь спокойно себя с малышом вкусной и полезной пищей"
    ]
  }
};

// хелпер переключения экранов
function setScreen(name) {
  if (currentScreen === name) return;
  currentScreen = name;
  Object.entries(mcScreens).forEach(([key, el]) => {
    if (key === name) el.classList.add("mc-screen--active");
    else el.classList.remove("mc-screen--active");
  });

  const topTitle = document.getElementById("mc-topbar-title");
  const topSubtitle = document.getElementById("mc-topbar-subtitle");

  if (name === "home") {
    topTitle.textContent = "MAMIN";
    topSubtitle.textContent = "помощь маме, которая всегда под рукой";
  } else if (name === "segments") {
    topTitle.textContent = "ассистенты";
    topSubtitle.textContent = "от беременности до подростков";
  } else if (name === "segment-0-1") {
    topTitle.textContent = "малыши 0–1 год";
    topSubtitle.textContent = "сон, грудь, животик и мама после родов";
  } else if (name === "favorites") {
    topTitle.textContent = "избранное";
    topSubtitle.textContent = "планы и подборки ассистентов";
  } else if (name === "dream") {
    topTitle.textContent = "dream room";
    topSubtitle.textContent = "мечты и маленькие радости мамы";
  } else if (name === "profile") {
    topTitle.textContent = "профиль";
    topSubtitle.textContent = "твои этапы и доступы";
  } else if (name === "assistant") {
    // заголовок воротится из данных ассистента, см. showAssistant
  }
}

// отрисовка ассистента в карточку
function showAssistant(key) {
  const data = ASSISTANTS[key];
  if (!data) return;

  const segTitle = document.getElementById("mc-assistant-segment-title");
  const segSub = document.getElementById("mc-assistant-segment-subtitle");
  const title = document.getElementById("mc-assistant-title");
  const lead = document.getElementById("mc-assistant-lead");
  const tariff = document.getElementById("mc-assistant-tariff");
  const doesList = document.getElementById("mc-assistant-does");
  const getsList = document.getElementById("mc-assistant-gets");

  segTitle.textContent = data.segmentTitle;
  segSub.textContent = data.segmentSubtitle;
  title.textContent = data.title;
  lead.textContent = data.lead;

  if (data.tariff) {
    tariff.textContent = data.tariff;
    tariff.style.display = "inline-flex";
  } else {
    tariff.textContent = "";
    tariff.style.display = "none";
  }

  const fillList = (ul, items) => {
    ul.innerHTML = "";
    items.forEach((txt) => {
      const li = document.createElement("li");
      li.textContent = txt;
      ul.appendChild(li);
    });
  };

  fillList(doesList, data.does);
  fillList(getsList, data.gets);

  const topTitle = document.getElementById("mc-topbar-title");
  const topSubtitle = document.getElementById("mc-topbar-subtitle");
  topTitle.textContent = data.segmentTitle.toLowerCase();
  topSubtitle.textContent = data.segmentSubtitle;

  setScreen("assistant");
}

function setActiveTab(tabName) {
  document.querySelectorAll(".mc-tab").forEach((btn) => {
    if (btn.dataset.tab === tabName) {
      btn.classList.add("mc-tab--active");
    } else {
      btn.classList.remove("mc-tab--active");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // собрать экраны
  document.querySelectorAll(".mc-screen").forEach((el) => {
    const name = el.dataset.screen;
    if (name) mcScreens[name] = el;
  });

  // по умолчанию: показываем home
  setScreen("home");
  setActiveTab("assistants");

  // таббар
  document.querySelectorAll(".mc-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.targetScreen;
      const tabName = btn.dataset.tab;
      if (target) {
        setScreen(target);
      }
      if (tabName) {
        setActiveTab(tabName);
      }
    });
  });

  // клики по быстрой сетке на главной
  document.querySelectorAll(".mc-quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (action === "open-assistant") {
        const code = btn.dataset.assistant;
        showAssistant(code || "sleep_0_1");
      } else if (action === "open-segment") {
        const seg = btn.dataset.segment;
        if (seg === "1-3") {
          setScreen("segments");
        } else {
          setScreen("segment-0-1");
        }
        setActiveTab("assistants");
      } else if (action === "go-assistants") {
        setScreen("segments");
        setActiveTab("assistants");
      }
    });
  });

  // список сегментов
  document.querySelectorAll(".mc-list-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const seg = btn.dataset.segment;
      if (seg === "0-1") {
        setScreen("segment-0-1");
        setActiveTab("assistants");
      } else if (seg === "pregnant") {
        showAssistant("tasty_pregnancy");
      } else {
        // остальные сегменты пока просто ведут в заглушки в «Избранное»
        setScreen("segments");
      }
    });
  });

  // кнопки пакетов
  document.querySelectorAll("[data-action='open-pack-details']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pack = btn.dataset.pack;
      // для MVP просто открываем одного из ассистентов
      if (pack === "basic-0-1") showAssistant("newborn_first_days");
      else if (pack === "smart-0-1") showAssistant("day_routine");
      else if (pack === "pro-0-1") showAssistant("mom_rest");
    });
  });

  // обратные кнопки
  const backToPacksBtn = document.querySelector("[data-action='back-to-packs']");
  if (backToPacksBtn) {
    backToPacksBtn.addEventListener("click", () => {
      setScreen("segment-0-1");
      setActiveTab("assistants");
    });
  }

  // покупка (пока просто alert, потом заменишь вызовом API)
  document.querySelectorAll("[data-action='buy-pack']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pack = btn.dataset.pack;
      console.log("BUY PACK", pack);
      alert("Здесь будет покупка набора: " + pack);
    });
  });

  const buyAssistantBtn = document.querySelector("[data-action='buy-current-assistant']");
  if (buyAssistantBtn) {
    buyAssistantBtn.addEventListener("click", () => {
      alert("Здесь будет покупка текущего ассистента.");
    });
  }
});
