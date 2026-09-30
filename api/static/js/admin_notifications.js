(function () {
  const root = document.getElementById('adminNotifications');
  if (!root) return;

  const POLL_MS = 30000;
  const countEl = root.querySelector('[data-notif-count]');
  const listEl = root.querySelector('[data-notif-list]');
  let latestId = 0;
  let timer = null;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function render(data) {
    const unread = Number(data.unread || 0);
    countEl.textContent = unread > 99 ? '99+' : String(unread);
    countEl.classList.toggle('d-none', unread === 0);
    const items = data.items || [];
    latestId = items.reduce((max, item) => Math.max(max, Number(item.id) || 0), latestId);
    if (!items.length) {
      listEl.innerHTML = '<div class="px-3 py-3 small text-muted">No notifications yet.</div>';
      return;
    }
    listEl.innerHTML = items.map((item) => {
      const tag = item.link ? 'a' : 'div';
      const href = item.link ? ` href="${escapeHtml(item.link)}"` : '';
      return `<${tag} class="dropdown-item small py-2 border-bottom text-wrap${item.unread ? ' fw-semibold' : ''}"${href}>`
        + `<div>${escapeHtml(item.title)}</div>`
        + (item.body ? `<div class="text-muted fw-normal">${escapeHtml(item.body)}</div>` : '')
        + `<div class="text-muted fw-normal" style="font-size: .75rem;">${escapeHtml(item.created_at)}</div>`
        + `</${tag}>`;
    }).join('');
  }

  function poll() {
    fetch(root.dataset.feedUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data && data.success) render(data); })
      .catch(() => {});
  }

  function start() {
    if (timer) return;
    poll();
    timer = setInterval(poll, POLL_MS);
  }

  function stop() {
    clearInterval(timer);
    timer = null;
  }

  root.addEventListener('shown.bs.dropdown', () => {
    if (!latestId || countEl.classList.contains('d-none')) return;
    fetch(root.dataset.seenUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': root.dataset.csrf },
      body: JSON.stringify({ up_to_id: latestId }),
    }).then((res) => {
      if (!res.ok) return;
      countEl.textContent = '0';
      countEl.classList.add('d-none');
    }).catch(() => {});
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop(); else start();
  });

  if (!document.hidden) start();
})();
