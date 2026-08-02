(() => {
  const INTRO_SEEN_KEY = "jk-door-intro-seen";
  const OPEN_DELAY_MS = 480;
  const OPEN_DURATION_MS = 1200;
  const REMOVE_DELAY_MS = 450;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function finish(intro) {
    document.body.classList.remove("door-intro-active");
    document.body.classList.add("door-intro-done");
    if (intro) {
      intro.classList.add("is-complete");
      window.setTimeout(() => intro.remove(), REMOVE_DELAY_MS);
    }
    document.dispatchEvent(new CustomEvent("jk:door-intro-complete"));
  }

  function skip(intro) {
    intro?.remove();
    document.body.classList.remove("door-intro-active");
    document.body.classList.add("door-intro-done");
    document.dispatchEvent(new CustomEvent("jk:door-intro-complete"));
  }

  const intro = document.getElementById("doorIntro");
  if (!intro) {
    document.body.classList.add("door-intro-done");
    document.dispatchEvent(new CustomEvent("jk:door-intro-complete"));
    return;
  }

  if (reduceMotion || sessionStorage.getItem(INTRO_SEEN_KEY) === "1") {
    skip(intro);
    return;
  }

  document.body.classList.add("door-intro-active");

  const startOpen = () => {
    intro.classList.add("is-opening");
    window.setTimeout(() => {
      sessionStorage.setItem(INTRO_SEEN_KEY, "1");
      finish(intro);
    }, OPEN_DURATION_MS);
  };

  window.setTimeout(startOpen, OPEN_DELAY_MS);

  intro.addEventListener("click", () => skip(intro), { once: true });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") skip(intro);
  }, { once: true });
})();
