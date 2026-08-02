const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");
const chatPropertyResults = document.getElementById("chatPropertyResults");
const chatSendBtn = document.getElementById("chatSendBtn");

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
    behavior: smooth && !window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "smooth" : "auto",
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

function showTypingIndicator() {
  hideTypingIndicator();
  const div = document.createElement("div");
  div.className = "chat-msg assistant chat-typing";
  div.id = "chatTyping";
  div.innerHTML = `
    <span class="chat-avatar chat-avatar--bot" aria-hidden="true"><i class="bi bi-building"></i></span>
    <div class="bubble bubble--typing" aria-label="Assistant is typing">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  `;
  chatMessages.appendChild(div);
  scrollChatToBottom();
}

function hideTypingIndicator() {
  document.getElementById("chatTyping")?.remove();
}

function setChatLoading(loading) {
  chatInput.disabled = loading;
  chatSendBtn.disabled = loading;
  chatSendBtn.classList.toggle("is-loading", loading);
  chatSendBtn.querySelector(".chat-send-spinner")?.classList.toggle("d-none", !loading);
  chatSendBtn.querySelector(".chat-send-icon")?.classList.toggle("d-none", loading);
  chatSendBtn.querySelector(".chat-send-label")?.classList.toggle("d-none", loading);
}

function renderPropertyCard(p) {
  const image = p.primary_image
    ? `<img src="/uploads/${p.primary_image}" alt="" class="card-img-top">`
    : `<div class="card-img-top bg-secondary d-flex align-items-center justify-content-center" style="height:180px"><i class="bi bi-building text-white fs-2"></i></div>`;
  return `
    <div class="col-md-6 col-lg-4 reveal-on-scroll">
      <article class="card property-card h-100">
        ${image}
        <div class="card-body">
          <h6 class="mb-1">${p.property_name}</h6>
          <p class="small text-muted mb-1">${p.area_name || "Surat"}</p>
          <p class="price mb-2">${formatINR(p.price || 0)}${p.listing_type === "rent" ? "/mo" : ""}</p>
          <a href="/property/${p.slug}" class="btn btn-sm btn-jk-primary">View Details</a>
        </div>
      </article>
    </div>
  `;
}

async function sendMessage(message) {
  appendMessage("user", message);
  setChatLoading(true);
  showTypingIndicator();

  try {
    const response = await apiFetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    hideTypingIndicator();
    appendMessage(
      "assistant",
      data.reply || data.error || "I apologise — I couldn't process that request. Please try again."
    );
    if (data.properties?.length) {
      chatPropertyResults.innerHTML = data.properties.map(renderPropertyCard).join("");
      chatPropertyResults.querySelectorAll(".reveal-on-scroll").forEach((el, i) => {
        setTimeout(() => el.classList.add("is-visible"), 80 + i * 60);
      });
    }
  } catch (err) {
    hideTypingIndicator();
    appendMessage(
      "assistant",
      "We're experiencing a brief connection issue. Please try again in a moment, or reach us directly on WhatsApp."
    );
  }

  setChatLoading(false);
  chatInput.focus();
}

chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = (chatInput.value || "").trim();
  if (!message || chatSendBtn?.disabled) return;
  chatInput.value = "";
  await sendMessage(message);
});

document.querySelectorAll(".chat-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    if (chatSendBtn?.disabled) return;
    sendMessage(chip.dataset.msg || "");
  });
});
