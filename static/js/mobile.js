(() => {
  const MOBILE_MAX = 991.98;

  function isMobile() {
    return window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches;
  }

  function setActiveMobileNav() {
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    document.querySelectorAll(".jk-mobile-nav__item[data-nav]").forEach((link) => {
      const target = (link.getAttribute("data-nav") || "").replace(/\/$/, "") || "/";
      const active = target === "/" ? path === "/" : path === target || path.startsWith(`${target}/`);
      link.classList.toggle("is-active", active);
    });
  }

  function initMobileHero() {
    const hero = document.querySelector(".property-hero");
    if (!hero || hero.dataset.mobileHeroInit === "true") return;
    hero.dataset.mobileHeroInit = "true";

    const panels = hero.querySelectorAll(".property-hero__panel");
    let timer = null;
    let index = 0;

    function startCinema() {
      hero.classList.add("is-mobile-cinema");
      hero.classList.remove("is-cinema");
      clearInterval(timer);
      index = 0;
      panels.forEach((panel, i) => panel.classList.toggle("is-visible", i === 0));
      timer = setInterval(() => {
        panels[index].classList.remove("is-visible");
        index = (index + 1) % panels.length;
        panels[index].classList.add("is-visible");
      }, 7000);
    }

    function stopCinema() {
      hero.classList.remove("is-mobile-cinema");
      clearInterval(timer);
      panels.forEach((panel) => panel.classList.add("is-visible"));
    }

    function sync() {
      if (isMobile()) startCinema();
      else stopCinema();
    }

    sync();
    window.addEventListener("resize", sync, { passive: true });
  }

  function closeNavOnNavigate() {
    const collapse = document.getElementById("publicNavbar");
    if (!collapse || !window.bootstrap) return;
    document.querySelectorAll(".jk-mobile-nav__item[href]").forEach((link) => {
      link.addEventListener("click", () => {
        const instance = window.bootstrap.Collapse.getInstance(collapse);
        if (instance && collapse.classList.contains("show")) instance.hide();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setActiveMobileNav();
    initMobileHero();
    closeNavOnNavigate();
  });
})();
