// Простая логика для первого экрана:
// - подсветка активной "быстрой" кнопки
// - подсветка активной вкладки таббара (пока без смены экранов)

document.addEventListener("DOMContentLoaded", () => {
  // Быстрые кнопки "что беспокоит прямо сейчас"
  const quickButtons = document.querySelectorAll(".m-quick-btn");
  quickButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      quickButtons.forEach((b) => b.classList.remove("m-quick-btn--active"));
      btn.classList.add("m-quick-btn--active");

      // сюда потом можно повесить переход к нужному ассистенту
      // например, вызвать API бэкенда
      console.log("Выбран запрос:", btn.dataset.topic);
    });
  });

  // Вкладки таббара
  const tabs = document.querySelectorAll(".m-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("m-tab--active"));
      tab.classList.add("m-tab--active");

      // позже здесь будет переключение экранов (assistants/favorites/dream/profile)
      console.log("Активная вкладка:", tab.dataset.tab);
    });
  });
});
