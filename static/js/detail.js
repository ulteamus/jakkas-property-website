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

function showShareFallback(title, url, image) {
  const modalEl = document.getElementById('shareFallbackModal');
  const nameEl = document.getElementById('shareFallbackName');
  const urlEl = document.getElementById('shareFallbackUrl');
  const imgEl = document.getElementById('shareFallbackImage');
  if (!modalEl || !urlEl) {
    prompt('Copy this property link:', url);
    return;
  }
  if (nameEl) nameEl.textContent = title;
  urlEl.value = url;
  if (imgEl) {
    if (image) {
      imgEl.src = image;
      imgEl.classList.remove('d-none');
    } else {
      imgEl.classList.add('d-none');
    }
  }
  if (window.bootstrap?.Modal) {
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  } else {
    modalEl.classList.add('show');
    modalEl.style.display = 'block';
  }
}

document.getElementById('shareFallbackCopy')?.addEventListener('click', async () => {
  const url = document.getElementById('shareFallbackUrl')?.value || location.href;
  try {
    await navigator.clipboard.writeText(url);
    alert('Link copied to clipboard.');
  } catch (_) {
    prompt('Copy this property link:', url);
  }
});

async function shareProperty() {
  const title = document.querySelector('h1')?.textContent?.trim() || document.title;
  const url = location.href;
  const image =
    document.getElementById('mainImg')?.src ||
    document.querySelector('meta[property="og:image"]')?.content ||
    '';
  const payload = { title, text: title, url };
  if (navigator.share) {
    try {
      await navigator.share(payload);
      return;
    } catch (err) {
      if (err && err.name === 'AbortError') return;
    }
  }
  showShareFallback(title, url, image);
}

document.querySelectorAll('.btn-share, [data-action="share-property"]').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    shareProperty();
  });
});

function focusInquiryName() {
  const nameInput =
    document.getElementById('inquiryNameInput') ||
    document.querySelector('#inquiryForm input[name="name"]') ||
    document.getElementById('visitNameInput') ||
    document.querySelector('#visitForm input[name="name"]');
  nameInput?.focus();
}

function openInquiryPanel(focus = true) {
  const panel =
    document.getElementById('inquiryPanel') ||
    document.getElementById('inquiryForm') ||
    document.getElementById('visitPanel');
  const intent = document.getElementById('inquiryIntent');
  if (intent && !intent.value) intent.value = 'property';
  if (panel && window.bootstrap?.Collapse && panel.classList.contains('collapse')) {
    bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false }).show();
  } else if (panel?.classList) {
    panel.classList.add('show');
  }
  panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (focus) setTimeout(focusInquiryName, 280);
}

if (location.hash === '#inquiryForm' || location.hash === '#inquiryPanel') {
  openInquiryPanel(true);
}

document.getElementById('inquiryForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd);
  body.source = body.source || 'property_detail';
  const r = await apiFetch('/api/inquiry', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const d = await r.json();
  alert(d.message || d.error);
  if (d.success) e.target.reset();
});

document.getElementById('visitForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd);
  body.source = 'site_visit';
  const r = await apiFetch('/api/visit-request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const d = await r.json();
  alert(d.message || d.error);
  if (d.success) e.target.reset();
});
