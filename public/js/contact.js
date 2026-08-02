(() => {
  const form = document.getElementById("contactForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const requirement = (fd.get("requirement") || "").trim();
    const budget = (fd.get("budget") || "").trim();
    const location = (fd.get("preferred_location") || "").trim();
    const messageParts = [];
    if (requirement) messageParts.push(`Requirement: ${requirement}`);
    if (budget) messageParts.push(`Budget: ${budget}`);
    if (location) messageParts.push(`Preferred Location: ${location}`);

    const body = {
      name: fd.get("name"),
      mobile: fd.get("mobile"),
      email: fd.get("email"),
      message: messageParts.join(" | ") || "General inquiry from contact page",
      budget: budget || null,
      preferred_location: location || null,
      source: "contact_form",
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
      const r = await apiFetch("/api/inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      alert(d.message || d.error);
      if (d.success) form.reset();
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
})();
