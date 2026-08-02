document.querySelectorAll('.gallery-thumb').forEach(th => {
  th.addEventListener('click', () => {
    document.getElementById('mainImg').src = th.dataset.full;
    document.querySelectorAll('.gallery-thumb').forEach(x => x.classList.remove('active'));
    th.classList.add('active');
  });
});

const lat = parseFloat(document.getElementById('detailMap')?.dataset.lat);
const lng = parseFloat(document.getElementById('detailMap')?.dataset.lng);
if (lat && lng && typeof L !== 'undefined') {
  const m = L.map('detailMap').setView([lat, lng], 15);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OSM' }).addTo(m);
  L.marker([lat, lng]).addTo(m);
}

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
