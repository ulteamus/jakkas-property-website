const smartForm = document.getElementById('smartSearchForm');
const smartInput = document.getElementById('smartQuery');
const smartResults = document.getElementById('smartResults');
const smartSuggest = document.getElementById('smartSuggest');

let activeIntent = '';

function propertyCard(p) {
  const src = p.primary_image_url || (p.primary_image ? `/uploads/${p.primary_image}` : '/static/img/default-property.jpg');
  const img = `<div class="property-image-wrap"><img src="${src}" alt="" onerror="this.onerror=null;this.src='/static/img/default-property.jpg';"></div>`;
  return `
    <div class="col-md-6 col-lg-4">
      <div class="card property-card h-100">
        ${img}
        <div class="card-body">
          <div class="d-flex flex-wrap gap-2 mb-2">
            <span class="badge badge-type">${p.display_type || p.property_type || 'Property'}</span>
            <span class="badge badge-status ${(p.listing_intent || '').toLowerCase() === 'rent' ? 'badge-rent' : 'badge-buy'}">${(p.listing_intent || 'buy').toUpperCase()}</span>
          </div>
          <h6 class="mb-1">${p.property_name}</h6>
          <p class="text-muted small mb-1">${p.area_name || 'Surat'}</p>
          ${p.distance_km ? `<p class="small text-muted mb-1"><i class="bi bi-sign-turn-right"></i> ${p.distance_km} km away</p>` : ''}
          <p class="price mb-2">${formatINR(p.price || 0)}${p.listing_type === 'rent' ? '/mo' : ''}</p>
          <a href="/property/${p.slug}" class="btn btn-sm btn-jk-primary">View Details</a>
        </div>
      </div>
    </div>
  `;
}

function debounce(fn, wait = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function runSmartSearch(event) {
  if (event) event.preventDefault();
  const query = (smartInput?.value || '').trim();
  if (!query) {
    smartResults.innerHTML = '';
    return;
  }

  const smartRes = await apiFetch('/api/properties/smart-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 12 }),
  });
  const smartData = await smartRes.json();
  if (!smartData.success) {
    smartResults.innerHTML = '<p class="text-muted">No results found.</p>';
    return;
  }

  const parsed = smartData.parsed || {};
  if (activeIntent) parsed.listing_intent = activeIntent;
  const hasStructuredFilters = Boolean(
    parsed.location || parsed.property_type || parsed.bhk || parsed.min_price || parsed.max_price || parsed.listing_intent
  );

  const params = new URLSearchParams();
  if (parsed.query && !hasStructuredFilters) params.set('q', parsed.query);
  if (parsed.location) params.set('area', parsed.location);
  if (parsed.property_type) params.set('type', parsed.property_type);
  if (parsed.bhk) params.set('bhk', parsed.bhk);
  if (parsed.min_price) params.set('min_price', parsed.min_price);
  if (parsed.max_price) params.set('max_price', parsed.max_price);
  if (parsed.listing_intent) params.set('listing_intent', parsed.listing_intent);
  params.set('limit', '9');

  const response = await fetch(`/api/properties?${params.toString()}`);
  const data = await response.json();
  if (!data.properties?.length) {
    smartResults.innerHTML = '<p class="text-muted mt-3">No properties match this search.</p>';
    return;
  }
  smartResults.innerHTML = data.properties.map((p) => propertyCard(p)).join('');
}

async function loadSuggest() {
  const query = (smartInput?.value || '').trim();
  if (query.length < 2) {
    smartSuggest.innerHTML = '';
    return;
  }
  const response = await fetch(`/api/properties/suggest?q=${encodeURIComponent(query)}`);
  const data = await response.json();
  if (!data.properties?.length) {
    smartSuggest.innerHTML = '';
    return;
  }
  smartSuggest.innerHTML = data.properties
    .map((p) => `<button type="button" class="suggest-item" data-query="${p.property_name}">${p.property_name} <small>${p.area_name}</small></button>`)
    .join('');
  smartSuggest.querySelectorAll('.suggest-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      smartInput.value = btn.dataset.query;
      smartSuggest.innerHTML = '';
      runSmartSearch();
    });
  });
}

document.querySelectorAll('.intent-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.intent-tab').forEach((item) => item.classList.remove('active'));
    tab.classList.add('active');
    activeIntent = tab.dataset.intent || '';
    if ((smartInput?.value || '').trim()) runSmartSearch();
  });
});

smartForm?.addEventListener('submit', runSmartSearch);
smartInput?.addEventListener('input', debounce(loadSuggest, 250));

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function discoverCardHTML(p) {
  const forLabel = (p.listing_intent || '').toLowerCase() === 'rent' ? 'Rent' : 'Sale';
  const media = listingMediaHTML(p, { height: 240, badgeText: `For ${forLabel}` });
  const type = escapeHtml(p.display_type || p.property_type || 'Property');
  const area = escapeHtml(p.area_name || 'Surat');
  const name = escapeHtml(p.property_name);
  const rentSuffix = p.listing_type === 'rent' ? '/mo' : '';
  return `<div class="col-md-6 col-lg-4">
    <article class="jv-property-card property-card">
      ${media}
      <div class="jv-property-body">
        <h3 class="jv-property-title"><a href="/property/${p.slug}">${name}</a></h3>
        <p class="jv-property-meta">${type} · ${area}, Surat</p>
        <p class="jv-property-price">From ${formatINR(p.price || 0)}${rentSuffix}</p>
        <a href="/property/${p.slug}" class="btn btn-sm btn-jk-primary">View Details</a>
      </div>
    </article>
  </div>`;
}

async function loadDiscoverProperties() {
  const grid = document.getElementById('jvDiscoverGrid');
  if (!grid) return;
  if (grid.querySelector('.jv-property-card')) return;

  try {
    const res = await fetch('/api/properties?sort=newest&limit=9');
    const data = await res.json();
    const properties = data.properties || [];
    if (!properties.length) {
      grid.innerHTML = `<div class="col-12 text-center py-4">
        <p class="text-muted mb-3">New listings will appear here soon.</p>
        <a href="/properties" class="btn btn-jk-accent">Browse All Listings</a>
      </div>`;
      return;
    }
    grid.innerHTML = properties.map(discoverCardHTML).join('');
    initListingMedia(grid);
  } catch (_err) {
    grid.innerHTML = '<p class="text-muted text-center col-12">Unable to load properties right now.</p>';
  }
}

loadDiscoverProperties();

document.querySelectorAll('.popular-search-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const query = chip.dataset.query || chip.textContent.trim();
    if (!smartInput) return;
    smartInput.value = query;
    smartSuggest.innerHTML = '';
    runSmartSearch();
  });
});
