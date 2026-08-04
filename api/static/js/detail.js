document.querySelectorAll('.gallery-thumb').forEach(th => {
  th.addEventListener('click', () => {
    document.getElementById('mainImg').src = th.dataset.full;
    document.querySelectorAll('.gallery-thumb').forEach(x => x.classList.remove('active'));
    th.classList.add('active');
  });
});

document.querySelector('.btn-call')?.addEventListener('click', () => {
  const pid = document.querySelector('[data-property-id]')?.dataset.propertyId;
  apiFetch('/api/event/call', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ property_id: pid }) });
});

document.querySelector('.btn-whatsapp')?.addEventListener('click', async (e) => {
  e.preventDefault();
  const pid = document.querySelector('[data-property-id]')?.dataset.propertyId;
  const r = await apiFetch('/api/whatsapp/interest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ property_id: pid }),
  });
  const d = await r.json();
  if (d.whatsapp_url) window.open(d.whatsapp_url, '_blank');
});

document.querySelector('.btn-share')?.addEventListener('click', () => {
  if (navigator.share) navigator.share({ title: document.title, url: location.href });
  else { navigator.clipboard.writeText(location.href); alert('Link copied!'); }
});

function openSiteVisitPanel(focus = true) {
  const panel = document.getElementById('visitPanel');
  const intent = document.getElementById('inquiryIntent');
  if (intent) intent.value = 'site_visit';
  if (panel && window.bootstrap?.Collapse) {
    bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false }).show();
  } else if (panel) {
    panel.classList.add('show');
  }
  panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (focus) {
    setTimeout(() => document.getElementById('visitNameInput')?.focus(), 280);
  }
}

document.querySelectorAll('.btn-request-visit').forEach((btn) => {
  btn.addEventListener('click', () => openSiteVisitPanel(true));
});

if (location.hash === '#visitPanel' || /[?&]intent=site_visit\b/i.test(location.search)) {
  openSiteVisitPanel(true);
}

document.getElementById('inquiryForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  const r = await apiFetch('/api/inquiry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const d = await r.json();
  alert(d.message || d.error);
  if (d.success) e.target.reset();
});

document.getElementById('visitForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  const r = await apiFetch('/api/visit-request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const d = await r.json();
  alert(d.message || d.error);
  if (d.success) e.target.reset();
});
