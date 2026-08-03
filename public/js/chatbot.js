/**
 * JAKKASH Property Assistant — menu-driven static guide (no LLM / NLP).
 */
(function () {
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");
  const chatPropertyResults = document.getElementById("chatPropertyResults");
  const chatSendBtn = document.getElementById("chatSendBtn");
  const chatMenu = document.getElementById("chatMenu");
  const shell = document.querySelector(".chatbot-shell");

  const phone = (shell?.dataset.phone || "918511751119").replace(/\D/g, "");
  const whatsapp = (shell?.dataset.whatsapp || phone).replace(/\D/g, "");
  const address =
    shell?.dataset.address ||
    "40, Ganesh Krupa Soc, Opp Gail Tower, Anand Mahal Road, Surat 395009";

  const waUrl = `https://wa.me/${whatsapp}?text=${encodeURIComponent(
    "Hello JAKKASH Property Consultancy. I need help with a property."
  )}`;
  const telUrl = `tel:${phone}`;

  function formatMessage(text) {
    const safe = (text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return safe
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br>");
  }

  function scrollChatToBottom(smooth = true) {
    if (!chatMessages) return;
    chatMessages.scrollTo({
      top: chatMessages.scrollHeight,
      behavior:
        smooth && !window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "smooth"
          : "auto",
    });
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    const avatar =
      role === "assistant"
        ? `<span class="chat-avatar chat-avatar--bot" aria-hidden="true"><i class="bi bi-building"></i></span>`
        : `<span class="chat-avatar chat-avatar--user" aria-hidden="true"><i class="bi bi-person-fill"></i></span>`;
    div.innerHTML = `${avatar}<div class="bubble">${formatMessage(text)}</div>`;
    chatMessages.appendChild(div);
    requestAnimationFrame(() => {
      div.classList.add("chat-msg--visible");
      scrollChatToBottom();
    });
  }

  function setMenuButtons(buttons) {
    if (!chatMenu) return;
    chatMenu.innerHTML = "";
    (buttons || []).forEach((btn) => {
      if (btn.href) {
        const a = document.createElement("a");
        a.className = "chat-chip chat-chip--link";
        a.href = btn.href;
        if (btn.external) {
          a.target = "_blank";
          a.rel = "noopener noreferrer";
        }
        a.textContent = btn.label;
        chatMenu.appendChild(a);
        return;
      }
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chat-chip";
      b.dataset.action = btn.action || "";
      b.textContent = btn.label;
      b.addEventListener("click", () => handleAction(btn.action, btn.label));
      chatMenu.appendChild(b);
    });
  }

  const MAIN_MENU = [
    { label: "Browse Properties", action: "browse" },
    { label: "Sell My Property", action: "sell" },
    { label: "Speak to a Broker", action: "broker" },
    { label: "Frequently Asked Questions", action: "faq" },
  ];

  const MENUS = {
    main: {
      reply:
        "How can we help you today? Choose an option below — no typing required.",
      buttons: MAIN_MENU,
    },
    browse: {
      reply:
        "Browse our Surat listings by category. Tap a type to open matching properties:",
      buttons: [
        { label: "3BHK Flats", href: "/properties?type=flat&bhk=3" },
        { label: "Bungalows", href: "/properties?type=bungalow" },
        { label: "Commercial", href: "/properties?type=commercial" },
        { label: "Plots", href: "/properties?type=plot" },
        { label: "← Back to menu", action: "main" },
      ],
    },
    sell: {
      reply:
        "Want to list with JAKKASH?\n\n1) Share owner and property details\n2) Our team verifies documents and pricing\n3) We market to active buyers in Surat\n\nUse the button below to start your listing.",
      buttons: [
        { label: "Go to Sell Property", href: "/sell-property" },
        { label: "← Back to menu", action: "main" },
      ],
    },
    broker: {
      reply:
        "Speak directly with a JAKKASH broker. We are available for calls and WhatsApp during working hours.",
      buttons: [
        { label: "WhatsApp", href: waUrl, external: true },
        { label: "Call Now", href: telUrl },
        { label: "← Back to menu", action: "main" },
      ],
    },
    faq: {
      reply: "Pick a common question:",
      buttons: [
        { label: "Brokerage terms", action: "faq_brokerage" },
        { label: "Office location", action: "faq_location" },
        { label: "Working hours", action: "faq_hours" },
        { label: "← Back to menu", action: "main" },
      ],
    },
    faq_brokerage: {
      reply:
        "**Brokerage:** Terms are shared transparently before any site visit or deal. Standard consultancy fees apply based on transaction type (buy / sell / rent). Ask your assigned broker for the exact schedule for your case.",
      buttons: [
        { label: "More FAQs", action: "faq" },
        { label: "Speak to a Broker", action: "broker" },
        { label: "← Main menu", action: "main" },
      ],
    },
    faq_location: {
      reply: `**Office (Surat):**\n${address}\n\nYou can also find us via Contact Us on the website.`,
      buttons: [
        { label: "More FAQs", action: "faq" },
        { label: "Contact page", href: "/contact" },
        { label: "← Main menu", action: "main" },
      ],
    },
    faq_hours: {
      reply:
        "**Working hours:** Monday–Saturday, 10:00 AM – 7:00 PM (IST).\nSunday by appointment. WhatsApp messages are monitored throughout the day.",
      buttons: [
        { label: "More FAQs", action: "faq" },
        { label: "Speak to a Broker", action: "broker" },
        { label: "← Main menu", action: "main" },
      ],
    },
  };

  function handleAction(action, userLabel) {
    const key = (action || "main").trim().toLowerCase();
    const node = MENUS[key] || MENUS.main;
    if (userLabel && key !== "main") {
      appendMessage("user", userLabel);
    }
    appendMessage("assistant", node.reply);
    setMenuButtons(node.buttons);
    if (chatPropertyResults) chatPropertyResults.innerHTML = "";
  }

  function matchKeyword(raw) {
    const q = (raw || "").toLowerCase().trim();
    if (!q) return null;
    if (/^(hi|hello|hey|namaste|good\s+(morning|afternoon|evening))\b/.test(q)) {
      return "main";
    }
    if (/\b(contact|phone|call|whatsapp|broker|agent)\b/.test(q)) {
      return "broker";
    }
    if (/\b(address|location|office|where)\b/.test(q)) {
      return "faq_location";
    }
    if (/\b(hour|timing|open|closed)\b/.test(q)) {
      return "faq_hours";
    }
    if (/\b(brokerage|commission|fees?)\b/.test(q)) {
      return "faq_brokerage";
    }
    if (/\b(sell|list\s+my|owner)\b/.test(q)) {
      return "sell";
    }
    if (/\b(buy|rent|flat|bhk|bungalow|plot|commercial|browse|propert)\b/.test(q)) {
      return "browse";
    }
    if (/\b(faq|question|help)\b/.test(q)) {
      return "faq";
    }
    return null;
  }

  function handleFreeText(message) {
    appendMessage("user", message);
    const action = matchKeyword(message);
    if (action) {
      const node = MENUS[action] || MENUS.main;
      appendMessage("assistant", node.reply);
      setMenuButtons(node.buttons);
      return;
    }
    appendMessage(
      "assistant",
      "Please use the quick options below — or type hello, contact, address, sell, or browse."
    );
    setMenuButtons(MAIN_MENU);
  }

  chatForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const message = (chatInput.value || "").trim();
    if (!message) return;
    chatInput.value = "";
    handleFreeText(message);
    chatInput.focus();
  });

  // Initial menu (welcome bubble is in HTML)
  setMenuButtons(MAIN_MENU);
})();
