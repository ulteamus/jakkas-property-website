(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!document.body.classList.contains("jk-luxury")) return;

  const nav = document.querySelector(".jk-navbar");
  const sculpture = document.getElementById("jkSculpture");
  const sculptureStack = sculpture?.querySelector(".jk-sculpture-stack");

  function initNavReveal() {
    if (!nav) return;
    const onScroll = () => {
      nav.classList.toggle("nav-scrolled", window.scrollY > 48);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    const collapse = document.getElementById("publicNavbar");
    if (collapse) {
      collapse.addEventListener("shown.bs.collapse", () => nav.classList.add("nav-revealed"));
      collapse.addEventListener("hidden.bs.collapse", () => {
        if (window.scrollY <= 48) nav.classList.remove("nav-revealed");
      });
    }
  }

  function initMagneticButtons() {
    if (reduceMotion) return;
    document.querySelectorAll(".btn-jk-accent, .btn-jk-outline, .btn-jk-primary").forEach((btn) => {
      btn.classList.add("btn-jk-magnetic");
      btn.addEventListener("mousemove", (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.setProperty("--mag-x", `${x * 0.12}px`);
        btn.style.setProperty("--mag-y", `${y * 0.12}px`);
        btn.classList.add("is-near");
      });
      btn.addEventListener("mouseleave", () => {
        btn.style.setProperty("--mag-x", "0px");
        btn.style.setProperty("--mag-y", "0px");
        btn.classList.remove("is-near");
      });
    });
  }

  function initSculptureParallax() {
    if (!sculptureStack || reduceMotion) return;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    window.addEventListener("mousemove", (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      targetX = (e.clientX - cx) / cx * 6;
      targetY = (e.clientY - cy) / cy * 4;
    }, { passive: true });

    const tick = () => {
      currentX += (targetX - currentX) * 0.06;
      currentY += (targetY - currentY) * 0.06;
      sculptureStack.style.transform = `rotateY(${currentX}deg) rotateX(${4 + currentY * 0.25}deg)`;
      requestAnimationFrame(tick);
    };
    tick();
  }

  function initHeroParallax() {
    if (reduceMotion) return;
    const photo = document.querySelector(".cinema-bg-photo");
    if (!photo) return;
    window.addEventListener("scroll", () => {
      const y = Math.min(window.scrollY * 0.18, 120);
      photo.style.transform = `scale(1.1) translate3d(0, ${y}px, 0)`;
    }, { passive: true });
  }

  function initCardTilt() {
    if (reduceMotion) return;
    document.querySelectorAll(".property-card, .category-tile, .why-card").forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width - 0.5;
        const py = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `translateY(-6px) rotateX(${py * -4}deg) rotateY(${px * 4}deg)`;
      });
      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  }

  initNavReveal();
  initMagneticButtons();
  initSculptureParallax();
  initHeroParallax();
  initCardTilt();
})();
