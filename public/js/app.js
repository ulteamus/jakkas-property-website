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
    alert('Property saved successfully.');
  } catch (err) {
    alert('Unable to save property right now.');
  }
}

document.querySelectorAll('.btn-save').forEach(btn => {
  btn.addEventListener('click', () => saveProperty(btn.dataset.id));
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
