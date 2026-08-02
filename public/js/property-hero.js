(function () {
  const MOBILE_MAX = 991.98;

  function isMobile() {
    return window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches;
  }

  function initPropertyHero(hero) {
    if (!hero || hero.dataset.propertyHeroInit === "true") return;
    hero.dataset.propertyHeroInit = "true";
    if (isMobile()) return;

    const panels = hero.querySelectorAll(".property-hero__panel");
    const modeBtns = hero.querySelectorAll(".property-hero__mode-btn");
    let cinemaIndex = 0;
    let cinemaTimer = null;

    hero.querySelectorAll("video").forEach((v) => {
      v.muted = true;
      v.playsInline = true;
      v.play().catch(() => {});
    });

    function setSplitMode() {
      hero.classList.remove("is-cinema");
      clearInterval(cinemaTimer);
      panels.forEach((p) => p.classList.add("is-visible"));
      modeBtns.forEach((b) => {
        b.classList.toggle("is-active", b.dataset.mode === "split");
        b.setAttribute("aria-selected", b.dataset.mode === "split");
      });
    }

    function setCinemaMode() {
      hero.classList.add("is-cinema");
      modeBtns.forEach((b) => {
        b.classList.toggle("is-active", b.dataset.mode === "cinema");
        b.setAttribute("aria-selected", b.dataset.mode === "cinema");
      });
      cinemaIndex = 0;
      panels.forEach((p, i) => p.classList.toggle("is-visible", i === 0));
      clearInterval(cinemaTimer);
      cinemaTimer = setInterval(() => {
        panels[cinemaIndex].classList.remove("is-visible");
        cinemaIndex = (cinemaIndex + 1) % panels.length;
        panels[cinemaIndex].classList.add("is-visible");
      }, 8000);
    }

    modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.mode === "cinema") setCinemaMode();
        else setSplitMode();
      });
    });
  }

  document.querySelectorAll(".property-hero").forEach(initPropertyHero);
})();
