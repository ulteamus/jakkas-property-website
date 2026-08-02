(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const counters = Array.from(document.querySelectorAll("[data-counter]"));
  if (!counters.length) return;

  const formatter = new Intl.NumberFormat("en-IN");

  const runCounter = (el) => {
    if (el.dataset.animated === "true") return;
    el.dataset.animated = "true";

    const target = Number(el.dataset.counter || 0);
    const suffix = el.dataset.suffix || "";
    if (reduceMotion || target <= 0) {
      el.textContent = `${formatter.format(Math.max(0, target))}${suffix}`;
      return;
    }

    const duration = 1400;
    const startAt = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - startAt) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      el.textContent = `${formatter.format(value)}${suffix}`;
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
})();
