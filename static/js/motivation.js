(() => {
  const slogans = [
    "Твой главный соперник — вчерашний ты.",
    "Лучше сделать как можешь, чем не сделать совсем.",
    "Сложно только до того момента, пока не начал.",
    "Не жди подходящего момента, создавай его сам.",
    "Прогресс важнее идеала.",
    "Не бойся медленного движения, бойся стоять на месте.",
    "Ты способен на большее, чем думаешь.",
    "Не сдавайся за шаг до результата.",
    "Все великие начинали с малого.",
    "Сила — в постоянстве.",
    "Страх уходит в действии.",
    "Твоя жизнь — в твоих руках.",
    "Результат любит регулярность.",
    "Маленькие шаги каждый день дают большие перемены.",
    "Не позволяй вчерашним ошибкам испортить сегодняшний день.",
    "Дисциплина — это свобода.",
    "Привычка формирует характер.",
    "Твои старания обязательно окупятся.",
    "Двигайся в своем темпе, но не останавливайся.",
    "Успех складывается из ежедневных усилий.",
    "Побеждает тот, кто действует.",
    "Не позволяй сомнениям управлять тобой.",
    "Выбирай движение, а не сожаления.",
    "Твои действия сегодня — твое будущее завтра.",
    "Сделай это, даже если страшно.",
    "Твой единственный ограничитель — ты сам.",
    "Ты творишь свою реальность.",
    "Выходи из зоны комфорта.",
    "Каждое усилие имеет значение.",
    "Не позволяй лени взять верх.",
    "Верь в свой путь, даже если он непростой.",
    "Дисциплина бьёт класс.",
  ];

  const element = document.getElementById("motivation-slogan");
  if (!element || slogans.length === 0) {
    return;
  }

  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  let order = [];
  let position = 0;
  let lastShown = null;

  function shuffle(items) {
    const copy = items.slice();
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function nextSlogan() {
    if (position >= order.length) {
      order = shuffle(slogans);
      position = 0;

      // Не показываем один и тот же слоган два раза подряд.
      if (order.length > 1 && order[0] === lastShown) {
        [order[0], order[1]] = [order[1], order[0]];
      }
    }

    lastShown = order[position];
    position += 1;
    return lastShown;
  }

  function show(slogan) {
    element.textContent = slogan;
  }

  show(nextSlogan());

  if (reducedMotion) {
    return;
  }

  window.setInterval(() => {
    element.classList.add("is-fading");
    window.setTimeout(() => {
      show(nextSlogan());
      element.classList.remove("is-fading");
    }, 320);
  }, 7000);
})();
