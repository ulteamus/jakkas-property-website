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
    } else {
      imgEl.classList.add('d-none');
    }
    if (image) imgEl.classList.remove('d-none');
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

function propertyShareMeta() {
  const title =
    document.querySelector('h1')?.textContent?.trim() ||
    document.querySelector('meta[property="og:title"]')?.content?.trim() ||
    document.title;
  const locality =
    document.querySelector('[data-property-area]')?.dataset.propertyArea ||
    document.querySelector('.property-locality, .text-muted .bi-geo-alt')?.parentElement?.textContent?.replace(/\s+/g, ' ').trim() ||
    document.querySelector('meta[property="og:description"]')?.content?.trim() ||
    'Surat';
  const pathMatch = location.pathname.match(/\/property\/([^/?#]+)/);
  const slug = pathMatch ? pathMatch[1] : '';
  const url = slug
    ? `${location.origin}/property/${slug}`
    : (document.querySelector('meta[property="og:url"]')?.content || location.href.split('#')[0]);
  const image =
    document.getElementById('mainImg')?.src ||
    document.querySelector('meta[property="og:image"]')?.content ||
    '';
  const text = `${title} — ${locality}. View this property on JAKKASH Property Consultancy.`;
  return { title, text, url, image };
}

async function sharePropertyFiles(imageUrl) {
  if (!imageUrl || !navigator.canShare || !window.File || !window.Blob) return null;
  try {
    const res = await fetch(imageUrl, { mode: 'cors', credentials: 'same-origin' });
    if (!res.ok) return null;
    const blob = await res.blob();
    if (!blob || !blob.type.startsWith('image/')) return null;
    const ext = (blob.type.split('/')[1] || 'jpg').replace('jpeg', 'jpg');
    const file = new File([blob], `property.${ext}`, { type: blob.type });
    if (!navigator.canShare({ files: [file] })) return null;
    return [file];
  } catch (_) {
    return null;
  }
}

async function shareProperty() {
  const { title, text, url, image } = propertyShareMeta();
  const payload = { title, text, url };
  if (navigator.share) {
    try {
      const files = await sharePropertyFiles(image);
      if (files) {
        try {
          await navigator.share({ ...payload, files });
          return;
        } catch (err) {
          if (err && err.name === 'AbortError') return;
          // Fall through to share without files if file share fails.
        }
      }
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

function showCollapsePanel(panel) {
  if (!panel) return;
  if (window.bootstrap?.Collapse && panel.classList.contains('collapse')) {
    bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false }).show();
  } else if (panel.classList) {
    panel.classList.add('show');
  }
}

function focusPanelField(panel) {
  const nameInput =
    panel?.querySelector('input[name="name"]') ||
    panel?.querySelector('input[name="mobile"]') ||
    document.getElementById('inquiryNameInput') ||
    document.getElementById('visitNameInput');
  nameInput?.focus({ preventScroll: true });
}

function openInquiryPanel(focus = true) {
  const panel = document.getElementById('inquiryPanel') || document.getElementById('inquiryForm');
  const intent = document.getElementById('inquiryIntent');
  if (intent && !intent.value) intent.value = 'property';
  showCollapsePanel(panel);
  panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (focus) setTimeout(() => focusPanelField(panel), 280);
}

function openSiteVisitPanel(focus = true) {
  const panel = document.getElementById('visitPanel') || document.getElementById('visitForm');
  showCollapsePanel(panel);
  panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (focus) setTimeout(() => focusPanelField(panel), 280);
}

document.querySelectorAll('.btn-send-inquiry').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    const panel = document.getElementById('inquiryPanel');
    if (!panel) return;
    e.preventDefault();
    openInquiryPanel(true);
  });
});

document.querySelectorAll('.btn-request-visit').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    const panel = document.getElementById('visitPanel');
    if (!panel) return;
    e.preventDefault();
    openSiteVisitPanel(true);
  });
});

const hash = (location.hash || '').toLowerCase();
if (hash === '#inquiryform' || hash === '#inquirypanel') {
  openInquiryPanel(true);
} else if (hash === '#visitform' || hash === '#visitpanel') {
  openSiteVisitPanel(true);
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
