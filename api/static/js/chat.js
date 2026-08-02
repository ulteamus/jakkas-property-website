const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `<div class="bubble">${text.replace(/</g, '&lt;').replace(/\n/g, '<br>')}</div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage('user', message);
  chatInput.value = '';
  chatInput.disabled = true;

  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    appendMessage('assistant', data.reply || data.error || 'Sorry, something went wrong.');
  } catch {
    appendMessage('assistant', 'Connection error. Please try again.');
  }

  chatInput.disabled = false;
  chatInput.focus();
});
