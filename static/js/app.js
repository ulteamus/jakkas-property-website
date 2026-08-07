function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

function apiFetch(url, options = {}) {
  const requestOptions = { credentials: 'same-origin', ...options };
  const method = String(requestOptions.method || 'GET').toUpperCase();
  const headers = new Headers(requestOptions.headers || {});
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken && !headers.has('X-CSRFToken')) {
      headers.set('X-CSRFToken', csrfToken);
    }
  }
  requestOptions.headers = headers;
  return fetch(url, requestOptions);
}

window.apiFetch = apiFetch;

/** Swap broken property/media images to the shared placeholder (no black boxes). */
document.addEventListener(
  'error',
  (event) => {
    const el = event.target;
    if (!el || el.tagName !== 'IMG') return;
    const fallback = '/static/img/default-property.jpg';
    if (el.dataset.fallbackApplied === '1') return;
    if ((el.getAttribute('src') || '').includes('default-property.jpg')) return;
    el.dataset.fallbackApplied = '1';
    el.src = fallback;
  },
  true
);

function formatINR(n) {
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

async function saveProperty(id) {
  try {
    await apiFetch('/api/saved', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ property_id: id }),
    });
    window.location.href = '/saved';
  } catch (err) {
    alert('Unable to save property right now.');
  }
}

document.querySelectorAll('.btn-save').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const id = btn.dataset.id;
    if (id) saveProperty(id);
    else window.location.href = '/saved';
  });
});

const inquiryPanel = document.getElementById('quickInquiryPanel');
const inquiryToggle = document.getElementById('quickInquiryToggle');
const inquiryClose = document.getElementById('quickInquiryClose');

function toggleInquiryPanel(open) {
  if (!inquiryPanel) return;
  inquiryPanel.classList.toggle('open', open);
  inquiryPanel.setAttribute('aria-hidden', open ? 'false' : 'true');
}

inquiryToggle?.addEventListener('click', () => {
  toggleInquiryPanel(!inquiryPanel.classList.contains('open'));
});

inquiryClose?.addEventListener('click', () => toggleInquiryPanel(false));

document.getElementById('quickInquiryForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = Object.fromEntries(new FormData(e.target));
  payload.source = 'quick_inquiry_widget';
  const response = await apiFetch('/api/inquiry', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  alert(data.message || data.error || 'Request sent');
  if (data.success) {
    e.target.reset();
    toggleInquiryPanel(false);
  }
});
