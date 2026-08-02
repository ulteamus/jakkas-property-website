(() => {
  const root = document.querySelector(".home-motion");
  if (!root) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STAGGER_MS = 165;
  const HERO_GAP_S = 0.15;

  root.querySelectorAll(".reveal-on-scroll").forEach((el) => {
    el.classList.remove("reveal-on-scroll", "is-visible");
    el.style.removeProperty("--reveal-delay");
  });

  const heroItems = Array.from(root.querySelectorAll(".home-hero-item"));

  const showItem = (el) => {
    el.classList.add("is-visible");
  };

  const delayFromStyle = (el, prop, fallback = 0) => {
    const value = parseFloat(getComputedStyle(el).getPropertyValue(prop));
    return Number.isFinite(value) ? value : fallback;
  };

  const whenDoorIntroReady = (callback) => {
    if (
      document.body.classList.contains("door-intro-done") ||
      !document.getElementById("doorIntro")
    ) {
      callback();
      return;
    }
    document.addEventListener("jk:door-intro-complete", callback, { once: true });
  };

  const revealSequential = (items, gapMs = STAGGER_MS) => {
    const pending = items.filter((item) => !item.classList.contains("is-visible"));
    if (!pending.length) return;

    if (reduceMotion) {
      pending.forEach(showItem);
      return;
    }

    pending.forEach((item, index) => {
      window.setTimeout(() => showItem(item), index * gapMs);
    });
  };

  const initHero = () => {
    if (!heroItems.length) return;

    if (reduceMotion) {
      heroItems.forEach(showItem);
      return;
    }

    requestAnimationFrame(() => {
      heroItems.forEach((el, index) => {
        const delay = delayFromStyle(el, "--hero-delay", index * HERO_GAP_S);
        window.setTimeout(() => showItem(el), delay * 1000 + 40);
      });
    });
  };

  whenDoorIntroReady(initHero);

  const sections = Array.from(root.querySelectorAll(".home-motion-section"));
  if (!sections.length) return;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    sections.forEach((section) => {
      revealSequential(Array.from(section.querySelectorAll(".home-motion-reveal")));
    });
    return;
  }

  const sectionObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const items = Array.from(entry.target.querySelectorAll(".home-motion-reveal"));
        revealSequential(items);
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
  );

  sections.forEach((section) => sectionObserver.observe(section));
})();
