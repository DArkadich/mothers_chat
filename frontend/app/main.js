/* global Telegram */
(function () {
  "use strict";

  // Telegram WebApp
  const tg = (typeof Telegram !== "undefined" && Telegram.WebApp) ? Telegram.WebApp : null;

  function setupTelegramUi() {
    try {
      if (!tg) return;
      tg.ready();
      tg.expand();
      tg.setHeaderColor && tg.setHeaderColor("#f7f5ef");
      tg.setBackgroundColor && tg.setBackgroundColor("#f7f5ef");
    } catch (e) {
      console.warn("[mamino] Telegram init warning:", e);
    }
  }

  // DOM
  const bgHero = document.getElementById("bgHero");
  const bgMain = document.getElementById("bgMain");

  const screenHome = document.getElementById("screen-home");
  const screenAssistants = document.getElementById("screen-assistants");
  const screenDetails = document.getElementById("screen-details");
  const screenPackage = document.getElementById("screen-package");
  const screenChat = document.getElementById("screen-chat");

  const tabAssistants = document.getElementById("tabAssistants");
  const tabFav = document.getElementById("tabFav");
  const tabDream = document.getElementById("tabDream");
  const tabProfile = document.getElementById("tabProfile");

  const btnBabySleep = document.getElementById("btnBabySleep");

  const assistantsListEl = document.getElementById("assistantsList");

  const detailsTitleEl = document.getElementById("detailsTitle");
  const detailsBackEl = document.getElementById("detailsBack");
  const detailsPrevEl = document.getElementById("detailsPrev");
  const detailsStageEl = document.getElementById("detailsStage");
  const detailsProgressEl = document.getElementById("detailsProgress");

  const packageTitleEl = document.getElementById("packageTitle");
  const packageBackEl = document.getElementById("packageBack");
  const packageListEl = document.getElementById("packageList");
  const packageHintEl = document.getElementById("packageHint");

  const chatTitleEl = document.getElementById("chatTitle");
  const chatBackEl = document.getElementById("chatBack");
  const chatMessagesEl = document.getElementById("chatMessages");
  const chatFormEl = document.getElementById("chatForm");
  const chatInputEl = document.getElementById("chatInput");
  const chatStatusEl = document.getElementById("chatStatus");

  // =========================
  // Background switching
  // =========================
  function setBg(mode) {
    if (!bgHero || !bgMain) return;
    if (mode === "home") {
      bgHero.style.display = "block";
      bgMain.style.display = "none";
    } else {
      bgHero.style.display = "none";
      bgMain.style.display = "block";
    }
  }

  function setActiveTab(tabIdOrNull) {
    document.querySelectorAll(".tabbar__btn").forEach((b) => b.classList.remove("tabbar__btn--active"));
    if (!tabIdOrNull) return;
    const btn = document.getElementById(tabIdOrNull);
    if (btn) btn.classList.add("tabbar__btn--active");
  }

  function setActiveScreen(name) {
    const appRoot = document.getElementById("appRoot");
    if (appRoot) appRoot.classList.toggle("app--fullscreen", name === "chat");
    screenHome?.classList.remove("screen--active");
    screenAssistants?.classList.remove("screen--active");
    screenDetails?.classList.remove("screen--active");
    screenPackage?.classList.remove("screen--active");
    screenChat?.classList.remove("screen--active");

    if (name === "home") {
      screenHome?.classList.add("screen--active");
      setBg("home");
      setActiveTab(null);
      return;
    }

    if (name === "assistants") {
      screenAssistants?.classList.add("screen--active");
      setBg("inner");
      setActiveTab("tabAssistants");
      return;
    }

    if (name === "details") {
      screenDetails?.classList.add("screen--active");
      setBg("inner");
      setActiveTab("tabAssistants");
      return;
    }

    if (name === "package") {
      screenPackage?.classList.add("screen--active");
      setBg("inner");
      setActiveTab("tabAssistants");
      return;
    }

    if (name === "chat") {
      screenChat?.classList.add("screen--active");
      setBg("inner");
      setActiveTab("tabAssistants");
    }
  }

  // =========================
  // ASSISTANTS ACCORDION (MVP)
  // =========================

  // Путь к карточкам (symlink /app/cards -> /var/www/motherschat/Cards)
  // Фактически файлы лежат: /var/www/motherschat/Cards/pregnancy/01.svg ... 07.svg
  // Поэтому в браузере это: /app/cards/pregnancy/01.svg ... 07.svg
  const CARDS_BASE = "/app/cards/pregnancy";

  const PREGNANCY_ASSISTANTS = [
    { code: "pregnancy_first_days", title: "Наши первые дни вместе", subtitle: "Быт и опора в первые недели", src: `${CARDS_BASE}/01.svg` },
    { code: "pregnancy_sleep", title: "Малыш спит сладко", subtitle: "Сон и засыпания мягко, по возрасту", src: `${CARDS_BASE}/02.svg` },
    { code: "pregnancy_milk_mom", title: "Молочная мама", subtitle: "ГВ/смесь/смешанное — бытовые ориентиры", src: `${CARDS_BASE}/03.svg` },
    { code: "pregnancy_crying", title: "Почему малыш плачет", subtitle: "Плач как язык малыша — без страшилок", src: `${CARDS_BASE}/04.svg` },
    { code: "pregnancy_day_ok", title: "День в порядке", subtitle: "Режим и ритуалы, которые поддерживают", src: `${CARDS_BASE}/05.svg` },
    { code: "pregnancy_routine_for_you", title: "Режим, который работает на тебя", subtitle: "Стабильность без насилия", src: `${CARDS_BASE}/06.svg` },
    { code: "pregnancy_mom_rest", title: "Мама отдыхает", subtitle: "Отдых и восстановление без чувства вины", src: `${CARDS_BASE}/07.svg` }
  ];


  // =========================
  // PURCHASE STATE (MVP)
  // =========================

  const PLAN_RANK = { Basic: 1, Smart: 2, Pro: 3 };

  function purchaseKey(sectionKey) {
    return `mamino_purchase_${sectionKey}`;
  }

  function getPurchasedPlan(sectionKey) {
    const v = localStorage.getItem(purchaseKey(sectionKey));
    return (v === "Basic" || v === "Smart" || v === "Pro") ? v : null;
  }

  function setPurchasedPlan(sectionKey, planName) {
    if (!PLAN_RANK[planName]) return;
    localStorage.setItem(purchaseKey(sectionKey), planName);
  }

  function purchasedRank(sectionKey) {
    const p = getPurchasedPlan(sectionKey);
    return p ? PLAN_RANK[p] : 0;
  }

  const SECTIONS = [
    {
      key: "pregnancy",
      title: "Беременным",
      subtitle: "Поддержка от теста до родов",
      mvp: true,
      plans: [
        {
          name: "Basic",
          gift: "+1 подарок",
          items: [
            PREGNANCY_ASSISTANTS[0].title,
            PREGNANCY_ASSISTANTS[1].title,
            PREGNANCY_ASSISTANTS[2].title,
          ],
          detailsCount: 3,
        },
        {
          name: "Smart",
          gift: "+2 подарка",
          items: [
            "BASIC +",
            PREGNANCY_ASSISTANTS[3].title,
            PREGNANCY_ASSISTANTS[4].title,
          ],
          detailsCount: 5,
        },
        {
          name: "Pro",
          gift: "+3 подарка",
          items: [
            "BASIC + SMART",
            PREGNANCY_ASSISTANTS[5].title,
            PREGNANCY_ASSISTANTS[6].title,
          ],
          detailsCount: 7,
        }
      ]
    },
    { key: "newborn_0_1", title: "Малыши 0 - 1 год", subtitle: "Сон, грудь, животик и мама после родов" },
    { key: "kids_1_3", title: "Малыши 1 - 3 года", subtitle: "Прикорм, горшок, привычки и кризис трех лет" },
    { key: "kids_3_7", title: "Дети 3 - 7 лет (сад)", subtitle: "Речь, игры, концентрация и адаптация" },
    { key: "school_7_10", title: "Школьники 7 - 10 лет", subtitle: "Домашка, режим и отношения" },
    { key: "school_11_14", title: "Школьники 11 - 14 лет", subtitle: "Подростки, гаджеты, эмоции и будущее" },
    { key: "manykids", title: "Многодетным", subtitle: "Расписание, рутина, ресурсы и деньги" },
    { key: "solo", title: "Соло - мамам", subtitle: "Опора, отношения и финансовая грамотность" },
    { key: "wishlist", title: "Карта желаний мамы", subtitle: "Мечты, планы и свои желания" }
  ];

  // =========================
  // CHAT (персональный чат на ассистента)
  // =========================

  const API_BASE = "/api";

  function getTelegramUserId() {
    try {
      const id = tg?.initDataUnsafe?.user?.id;
      if (typeof id === "number" && Number.isFinite(id)) return String(id);
      if (typeof id === "string" && id.length > 0) return id;
      return null;
    } catch {
      return null;
    }
  }

  function sessionStorageKey(assistantSlug) {
    return `mamino_session_${assistantSlug}`;
  }

  async function apiPost(path, payload) {
    const r = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }
    if (!r.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : `HTTP ${r.status}`;
      throw new Error(msg);
    }
    return data;
  }

  function setChatStatus(msg) {
    if (!chatStatusEl) return;
    chatStatusEl.textContent = msg || "";
  }

  function clearChatUi() {
    if (chatMessagesEl) chatMessagesEl.innerHTML = "";
    if (chatInputEl) chatInputEl.value = "";
    setChatStatus("");
  }

  function renderChatHistory(messages) {
    clearChatUi();
    if (!Array.isArray(messages) || messages.length === 0) return;
    messages.forEach((m) => {
      if (!m || (m.role !== "user" && m.role !== "assistant")) return;
      appendChatBubble(m.role, String(m.content || ""));
    });
  }

  async function loadChatHistory(sessionId) {
    const data = await apiPost("/chat/history", { session_id: sessionId });
    const msgs = data?.messages;
    return Array.isArray(msgs) ? msgs : [];
  }

  function appendChatBubble(role, text) {
    if (!chatMessagesEl) return;
    const row = document.createElement("div");
    row.className = `chat__msg ${role === "user" ? "chat__msg--me" : "chat__msg--ai"}`;

    const bubble = document.createElement("div");
    bubble.className = "chat__bubble";
    bubble.textContent = text;

    row.appendChild(bubble);
    chatMessagesEl.appendChild(row);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  let activeAssistantSlug = null;
  let activeAssistantTitle = null;
  let activeSessionId = null;

  async function ensureChatSession(assistantSlug) {
    const cached = localStorage.getItem(sessionStorageKey(assistantSlug));
    if (cached && cached.length > 0) return cached;

    const telegramId = getTelegramUserId();
    if (!telegramId) throw new Error("Нет telegram_id (открой Mini App в Telegram).");

    const data = await apiPost("/chat/session", {
      assistant_slug: assistantSlug,
      telegram_id: telegramId
    });

    if (!data || !data.session_id) throw new Error("Backend не вернул session_id");
    localStorage.setItem(sessionStorageKey(assistantSlug), data.session_id);
    return data.session_id;
  }

  function openChatUi(assistantSlug, assistantTitle) {
    activeAssistantSlug = assistantSlug;
    activeAssistantTitle = assistantTitle;
    activeSessionId = null;

    clearChatUi();
    if (chatTitleEl) chatTitleEl.textContent = assistantTitle;

    setActiveScreen("chat");

    setChatStatus("Подключаю ассистента…");
    ensureChatSession(assistantSlug)
      .then(async (sid) => {
        activeSessionId = sid;
        const history = await loadChatHistory(sid);
        setChatStatus("");
        if (history.length > 0) {
          renderChatHistory(history);
        } else {
          appendChatBubble("assistant", "Привет! Я на связи. Чем помочь?");
        }
        chatInputEl?.focus();
      })
      .catch((e) => setChatStatus(`Ошибка: ${e.message}`));
  }

  async function sendChatMessage(text) {
    if (!activeAssistantSlug) throw new Error("assistant_slug не выбран");
    if (!activeSessionId) activeSessionId = await ensureChatSession(activeAssistantSlug);

    appendChatBubble("user", text);
    setChatStatus("Ассистент думает…");

    const data = await apiPost("/chat/send", {
      session_id: activeSessionId,
      assistant_slug: activeAssistantSlug,
      message: text
    });

    setChatStatus("");

    // Источник истины — история с backend
    if (Array.isArray(data?.messages)) {
      renderChatHistory(data.messages);
      return;
    }

    const reply = data?.reply;
    if (typeof reply === "string" && reply.length > 0) {
      appendChatBubble("assistant", reply);
    } else {
      setChatStatus("Ошибка: пустой ответ модели");
    }
  }

  // =========================
  // Package screen
  // =========================

  function renderPackageList(sectionKey, sectionTitle, plan) {
    if (!packageListEl) return;

    const count = plan.detailsCount || 3;
    const items = PREGNANCY_ASSISTANTS.slice(0, count);

    if (packageTitleEl) packageTitleEl.textContent = `${sectionTitle} • ${plan.name}`;
    if (packageHintEl) packageHintEl.textContent = "Выберите ассистента — откроется отдельный чат.";

    packageListEl.innerHTML = "";

    items.forEach((a) => {
      const row = document.createElement("div");
      row.className = "packageItem";

      const t = document.createElement("div");
      t.className = "packageItem__title";
      t.textContent = a.title;

      const sub = document.createElement("div");
      sub.className = "packageItem__sub";
      sub.textContent = a.subtitle || "";

      row.appendChild(t);
      row.appendChild(sub);

      row.addEventListener("click", () => {
        openChatUi(a.code, `${a.title} • ${sectionTitle} • ${plan.name}`);
      });

      packageListEl.appendChild(row);
    });

    // запоминаем, откуда пришли, чтобы крестик возвращал корректно
    if (packageBackEl) {
      packageBackEl.dataset.returnOpenKey = sectionKey;
    }

    setActiveScreen("package");
  }

  // =========================
  // Accordion helpers
  // =========================

  function closeAllAccordions(exceptKey) {
    if (!assistantsListEl) return;
    const all = assistantsListEl.querySelectorAll(".acc");
    all.forEach((node) => {
      const key = node.getAttribute("data-key");
      if (exceptKey && key === exceptKey) return;
      node.classList.remove("acc--open");
      const icon = node.querySelector(".acc__icon");
      if (icon) icon.textContent = "+";
      const body = node.querySelector(".acc__body");
      if (body) body.style.maxHeight = "0px";
    });
  }

  function openAccordion(key) {
    const node = assistantsListEl?.querySelector(`.acc[data-key="${CSS.escape(key)}"]`);
    if (!node) return;
    closeAllAccordions(key);
    node.classList.add("acc--open");
    const icon = node.querySelector(".acc__icon");
    if (icon) icon.textContent = "—";
    const body = node.querySelector(".acc__body");
    if (body) body.style.maxHeight = body.scrollHeight + "px";
  }

  function toggleAccordion(key) {
    const node = assistantsListEl?.querySelector(`.acc[data-key="${CSS.escape(key)}"]`);
    if (!node) return;

    const isOpen = node.classList.contains("acc--open");
    if (isOpen) {
      node.classList.remove("acc--open");
      const icon = node.querySelector(".acc__icon");
      if (icon) icon.textContent = "+";
      const body = node.querySelector(".acc__body");
      if (body) body.style.maxHeight = "0px";
      return;
    }

    openAccordion(key);
  }

  // =========================
  // DETAILS PAGER (оставлен как есть; сейчас не используется в сценарии покупки)
  // =========================

  let detailsItems = [];
  let detailsIndex = 0;
  let detailsReturn = { screen: "assistants", openKey: "pregnancy" };
  let detailsTitle = "Беременным";
  let detailsPlan = "Basic";

  function renderDetailsCard() {
    if (!detailsStageEl) return;
    const item = detailsItems[detailsIndex];
    if (!item) return;

    detailsStageEl.innerHTML = "";

    const clip = document.createElement("div");
    clip.className = "detailsCardClip";

    const img = document.createElement("img");
    img.className = "detailsCardImg";
    img.src = item.src;
    img.alt = "";
    img.loading = "eager";
    img.decoding = "async";

    clip.appendChild(img);
    detailsStageEl.appendChild(clip);

    clip.addEventListener("click", () => detailsNext());

    let startX = 0;
    let startY = 0;
    let moving = false;

    clip.addEventListener(
      "touchstart",
      (e) => {
        const t = e.touches?.[0];
        if (!t) return;
        startX = t.clientX;
        startY = t.clientY;
        moving = true;
      },
      { passive: true }
    );

    clip.addEventListener(
      "touchmove",
      (e) => {
        if (!moving) return;
        const t = e.touches?.[0];
        if (!t) return;
        const dx = t.clientX - startX;
        const dy = t.clientY - startY;
        if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
          e.preventDefault();
        }
      },
      { passive: false }
    );

    clip.addEventListener("touchend", (e) => {
      if (!moving) return;
      moving = false;
      const t = e.changedTouches?.[0];
      if (!t) return;
      const dx = t.clientX - startX;
      if (dx < -50) detailsNext();
      else if (dx > 50) detailsPrev();
    });

    if (detailsTitleEl) detailsTitleEl.textContent = `${detailsTitle} • ${detailsPlan}`;
    if (detailsProgressEl) detailsProgressEl.textContent = `${detailsIndex + 1} / ${detailsItems.length}`;
  }

  function detailsOpen(opts) {
    detailsTitle = opts.title;
    detailsPlan = opts.plan;
    detailsItems = opts.items.slice();
    detailsIndex = 0;
    detailsReturn = opts.returnTo;

    setActiveScreen("details");
    renderDetailsCard();
  }

  function detailsClose() {
    setActiveScreen(detailsReturn.screen);
    if (detailsReturn.openKey) {
      openAccordion(detailsReturn.openKey);
      const node = assistantsListEl?.querySelector(`.acc[data-key="${CSS.escape(detailsReturn.openKey)}"]`);
      node?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function detailsNext() {
    if (detailsIndex >= detailsItems.length - 1) {
      detailsClose();
      return;
    }
    detailsIndex += 1;
    renderDetailsCard();
  }

  function detailsPrev() {
    if (detailsIndex <= 0) return;
    detailsIndex -= 1;
    renderDetailsCard();
  }

  function makePlanCard(sectionKey, sectionTitle, plan) {
    const offer = document.createElement("div");
    offer.className = "offer";

    const left = document.createElement("div");
    left.className = "offer__left";

    const tier = document.createElement("div");
    tier.className = "offer__tier";
    tier.textContent = plan.name;

    const ul = document.createElement("ul");
    ul.className = "offer__list";
    plan.items.forEach((it) => {
      const li = document.createElement("li");
      li.textContent = it;
      ul.appendChild(li);
    });

    left.appendChild(tier);
    left.appendChild(ul);

    const right = document.createElement("div");
    right.className = "offer__right";

    const gifts = document.createElement("div");
    gifts.className = "offer__gifts";
    gifts.textContent = plan.gift;

    const primary = document.createElement("button");
    primary.type = "button";
    primary.className = "btnPink btnPink--primary";

    const secondary = document.createElement("button");
    secondary.type = "button";
    secondary.className = "btnLink";
    secondary.textContent = "Подробнее";

    const pr = purchasedRank(sectionKey);
    const myPlan = getPurchasedPlan(sectionKey);
    const thisRank = PLAN_RANK[plan.name] || 0;

    // ЛОГИКА (MVP)
    // - если ничего не куплено: "Купить" -> считаем оплату успешной, сохраняем план, открываем список ассистентов пакета
    // - если куплен этот/выше: "Открыть"/"Включено" -> открываем список ассистентов
    // - если куплен ниже: "Повысить" -> повышаем план и открываем список ассистентов
    if (pr === 0) {
      primary.textContent = "Купить";
      primary.addEventListener("click", () => {
        setPurchasedPlan(sectionKey, plan.name);
        renderAssistants();
        openAccordion(sectionKey);
        renderPackageList(sectionKey, sectionTitle, plan);
      });
    } else if (pr >= thisRank) {
      primary.textContent = (myPlan === plan.name) ? "Открыть" : "Включено";
      primary.addEventListener("click", () => {
        renderPackageList(sectionKey, sectionTitle, plan);
      });
    } else {
      primary.textContent = "Повысить";
      primary.addEventListener("click", () => {
        setPurchasedPlan(sectionKey, plan.name);
        renderAssistants();
        openAccordion(sectionKey);
        renderPackageList(sectionKey, sectionTitle, plan);
      });
    }

    secondary.addEventListener("click", () => {
      const count = plan.detailsCount || 3;
      const items = PREGNANCY_ASSISTANTS.slice(0, count).map(a => ({ title: a.title, subtitle: a.subtitle, src: a.src }));
      detailsOpen({
        title: sectionTitle,
        plan: plan.name,
        items,
        returnTo: { screen: "assistants", openKey: sectionKey }
      });
    });

    right.appendChild(gifts);
    right.appendChild(primary);
    right.appendChild(secondary);

    offer.appendChild(left);
    offer.appendChild(right);

    return offer;
  }

  function renderAssistants() {
    if (!assistantsListEl) return;
    assistantsListEl.innerHTML = "";

    SECTIONS.forEach((s) => {
      const item = document.createElement("div");
      item.className = "acc";
      item.setAttribute("data-key", s.key);

      const head = document.createElement("button");
      head.type = "button";
      head.className = "acc__head";

      const left = document.createElement("div");
      left.className = "acc__left";

      const t = document.createElement("div");
      t.className = "acc__title";
      t.textContent = s.title;

      const sub = document.createElement("div");
      sub.className = "acc__sub";
      sub.textContent = s.subtitle;

      left.appendChild(t);
      left.appendChild(sub);

      const icon = document.createElement("div");
      icon.className = "acc__icon";
      icon.textContent = "+";

      head.appendChild(left);
      head.appendChild(icon);

      const body = document.createElement("div");
      body.className = "acc__body";
      body.style.maxHeight = "0px";

      const bodyInner = document.createElement("div");
      bodyInner.className = "acc__bodyInner";

      if (s.mvp) {
        const plansWrap = document.createElement("div");
        plansWrap.className = "plans";
        s.plans.forEach((p) => plansWrap.appendChild(makePlanCard(s.key, s.title, p)));
        bodyInner.appendChild(plansWrap);
      } else {
        const soon = document.createElement("div");
        soon.className = "acc__soon";
        soon.textContent = "Скоро";
        bodyInner.appendChild(soon);
      }

      body.appendChild(bodyInner);

      item.appendChild(head);
      item.appendChild(body);

      head.addEventListener("click", () => toggleAccordion(s.key));

      assistantsListEl.appendChild(item);
    });
  }

  // =========================
  // Events
  // =========================

  function wireEvents() {
    tabAssistants?.addEventListener("click", () => setActiveScreen("assistants"));

    // пока остальные вкладки выключены
    tabFav?.addEventListener("click", () => {});
    tabDream?.addEventListener("click", () => {});
    tabProfile?.addEventListener("click", () => {});

    // HOME: «СОН МЛАДЕНЦА» ведёт в ассистенты (MVP: раскрываем 0–1 год)
    btnBabySleep?.addEventListener("click", () => {
      setActiveScreen("assistants");
      openAccordion("newborn_0_1");
    });

    detailsBackEl?.addEventListener("click", detailsClose);

    // “назад” на карточках (для листания)
    detailsPrevEl?.addEventListener("click", (e) => {
      e.preventDefault();
      detailsPrev();
    });

    packageBackEl?.addEventListener("click", () => {
      // Возврат на ассистенты: если пакет куплен — показываем тот же аккордеон, но карточки уже в режиме "Открыть/Повысить"
      setActiveScreen("assistants");
      const openKey = packageBackEl?.dataset?.returnOpenKey || "pregnancy";
      openAccordion(openKey);
      const node = assistantsListEl?.querySelector(`.acc[data-key="${CSS.escape(openKey)}"]`);
      node?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    chatBackEl?.addEventListener("click", () => {
      setActiveScreen("package");
    });

    chatFormEl?.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = (chatInputEl?.value || "").trim();
      if (!v) return;
      chatInputEl.value = "";
      sendChatMessage(v).catch((err) => setChatStatus(`Ошибка: ${err.message}`));
    });
  }

  // Boot
  function boot() {
    setupTelegramUi();
    renderAssistants();
    wireEvents();
    setActiveScreen("home");
  }

  boot();
})();