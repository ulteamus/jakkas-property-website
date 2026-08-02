(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STAGGER_GAP_MS = 165;

  const isExcluded = (el) =>
    !el ||
    el.classList.contains("filter-drawer") ||
    el.id === "filterDrawer" ||
    el.closest(".filter-drawer, #filterDrawer, .ai-chat-widget, .quick-inquiry-panel");

  const show = (el) => {
    if (!el || isExcluded(el)) return;
    el.classList.add("is-visible");
  };

  const delayFromEl = (el, prop, fallback = 0) => {
    const inline = el.dataset.revealDelay ?? el.dataset.delay;
    if (inline !== undefined && inline !== "") return parseFloat(inline) || fallback;
    const styled = parseFloat(getComputedStyle(el).getPropertyValue(prop));
    return Number.isFinite(styled) ? styled : fallback;
  };

  const autoRevealSelectors = [
    ".property-card",
    ".why-card",
    ".testimonial-card",
    ".category-tile",
    ".content-card",
    ".submission-form",
    ".service-card",
    ".team-card",
    ".featured-card",
    ".section-title",
    ".chatbot-page-header",
    ".chatbot-shell",
    ".listings-page > header",
    ".listings-toolbar",
    ".contact-strip .container",
    ".gallery-main",
    ".detail-page .col-lg-5",
    ".detail-page .col-lg-7",
    ".detail-page section",
    ".footer-block",
    ".about-hero-card",
    ".founder-card",
    ".about-info-card",
    ".about-stat-card",
    ".about-contact-card",
    ".page-hero",
    ".contact-info-card",
    ".contact-map-wrap",
    ".reveal-on-scroll",
  ].join(",");

  const staggerState = new WeakMap();
  let staggerObserver = null;

  function prepareStaggerChildren(container) {
    Array.from(container.children).forEach((child, index) => {
      if (isExcluded(child)) return;
      child.classList.add("scroll-reveal", "scroll-reveal-seq");
      if (!child.style.getPropertyValue("--stagger-index")) {
        child.style.setProperty("--stagger-index", String(index));
      }
    });
  }

  function revealSequential(items, gapMs = STAGGER_GAP_MS) {
    const pending = items.filter((item) => !item.classList.contains("is-visible"));
    if (!pending.length) return;

    if (reduceMotion) {
      pending.forEach(show);
      return;
    }

    pending.forEach((item, index) => {
      window.setTimeout(() => show(item), index * gapMs);
    });
  }

  function getStaggerObserver() {
    if (staggerObserver) return staggerObserver;
    if (reduceMotion || !("IntersectionObserver" in window)) return null;

    staggerObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const container = entry.target;
          const state = staggerState.get(container) || { triggered: false };
          state.triggered = true;
          staggerState.set(container, state);
          revealSequential(Array.from(container.children).filter((child) => !isExcluded(child)));
          observer.unobserve(container);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -32px 0px" }
    );
    return staggerObserver;
  }

  function setupStaggerContainers(root = document) {
    const containers = root.matches?.(".scroll-reveal-stagger")
      ? [root, ...root.querySelectorAll(".scroll-reveal-stagger")]
      : root.querySelectorAll(".scroll-reveal-stagger");

    containers.forEach((container) => {
      if (!(container instanceof Element) || isExcluded(container)) return;
      prepareStaggerChildren(container);

      const state = staggerState.get(container) || { triggered: false };
      const pending = Array.from(container.children).filter(
        (child) => !isExcluded(child) && !child.classList.contains("is-visible")
      );
      if (!pending.length) return;

      if (state.triggered || reduceMotion || !("IntersectionObserver" in window)) {
        revealSequential(pending);
        return;
      }

      staggerState.set(container, state);
      getStaggerObserver()?.observe(container);
    });
  }

  function autoApplyScrollReveal(root = document) {
    root.querySelectorAll(autoRevealSelectors).forEach((el) => {
      if (el.classList.contains("scroll-reveal") || isExcluded(el)) return;
      const staggerRoot = el.closest(".scroll-reveal-stagger");
      if (staggerRoot && Array.from(staggerRoot.children).includes(el)) return;
      el.classList.add("scroll-reveal");
    });
  }

  let revealObserver = null;

  function getRevealObserver() {
    if (revealObserver) return revealObserver;
    if (reduceMotion || !("IntersectionObserver" in window)) return null;

    revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting || isExcluded(entry.target)) return;
          show(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -32px 0px" }
    );
    return revealObserver;
  }

  function observe(root = document) {
    setupStaggerContainers(root);
    autoApplyScrollReveal(root);

    const items = Array.from(root.querySelectorAll(".scroll-reveal:not(.is-visible)")).filter(
      (item) => !isExcluded(item) && !item.closest(".scroll-reveal-stagger")
    );

    if (!items.length) return;

    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach(show);
      return;
    }

    const observer = getRevealObserver();
    items.forEach((item) => observer.observe(item));
  }

  function whenDoorIntroReady(callback) {
    if (
      document.body.classList.contains("door-intro-done") ||
      !document.getElementById("doorIntro")
    ) {
      callback();
      return;
    }
    document.addEventListener("jk:door-intro-complete", callback, { once: true });
  }

  function initHeroReveal() {
    const hero = document.querySelector(".scroll-reveal-hero");
    if (!hero) return;

    const items = hero.querySelectorAll(".scroll-reveal-hero-item");
    if (!items.length) return;

    const run = () => {
      if (reduceMotion) {
        items.forEach(show);
        return;
      }

      requestAnimationFrame(() => {
        items.forEach((el, index) => {
          const delay = delayFromEl(el, "--hero-delay", index * 0.15);
          window.setTimeout(() => show(el), delay * 1000 + 60);
        });
      });
    };

    whenDoorIntroReady(run);
  }

  function initHeroParallax() {
    if (reduceMotion) return;
    const hero = document.querySelector(".jk-hero.hero-home, .hero-home");
    const layer = hero?.querySelector(".hero-parallax-layer");
    if (!hero || !layer) return;

    const onScroll = () => {
      const rect = hero.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      const progress = Math.min(Math.max(-rect.top / rect.height, 0), 1);
      layer.style.transform = `translate3d(0, ${progress * 28}px, 0)`;
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function initCounters(root = document) {
    const counters = Array.from(root.querySelectorAll("[data-counter], [data-count]"));
    if (!counters.length) return;

    const formatter = new Intl.NumberFormat("en-IN");

    const runCounter = (el) => {
      if (el.dataset.animated === "true") return;
      el.dataset.animated = "true";

      const target = Number(el.dataset.counter ?? el.dataset.count ?? 0);
      const suffix = el.dataset.suffix || "";

      if (reduceMotion || target <= 0) {
        el.textContent = target > 0 ? `${formatter.format(target)}${suffix}` : el.textContent;
        return;
      }

      const duration = 1400;
      const startAt = performance.now();

      const tick = (now) => {
        const progress = Math.min((now - startAt) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = `${formatter.format(Math.round(target * eased))}${suffix}`;
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    if (reduceMotion || !("IntersectionObserver" in window)) {
      counters.forEach(runCounter);
      return;
    }

    const counterObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          runCounter(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.35 }
    );
    counters.forEach((counter) => counterObserver.observe(counter));
  }

  function initNavbarScroll() {
    const nav = document.querySelector(".jk-navbar, .jv-navbar");
    if (!nav) return;
    const onScroll = () => nav.classList.toggle("nav-scrolled", window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function initPageEnter() {
    const main = document.querySelector("main.page-enter");
    if (!main) return;
    requestAnimationFrame(() => main.classList.add("is-visible"));
  }

  initPageEnter();
  initNavbarScroll();
  initHeroReveal();
  initHeroParallax();
  observe();
  initCounters();

  window.JkScrollReveal = { observe, show };
})();
