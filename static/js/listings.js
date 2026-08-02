const results = document.getElementById('results');
const noResults = document.getElementById('noResults');
const listingsPromo = document.getElementById('listingsPromo');
const listingsPromoCount = document.getElementById('listingsPromoCount');
const form = document.getElementById('filterForm');
const resultsCount = document.getElementById('resultsCount');
const intentInput = document.getElementById('f_listing_intent');
const filterDrawer = document.getElementById('filterDrawer');
const filterOverlay = document.getElementById('filterOverlay');
const openFiltersBtn = document.getElementById('openFilters');
const closeFiltersBtn = document.getElementById('closeFilters');
const GRID_COL_CLASS = 'col-12 col-md-6 col-lg-4 col-xxl-3 listing-card-col';
const LIST_COL_CLASS = 'col-12 listing-card-col';
const FILTER_KEYS = [
  'area', 'type', 'max_price', 'min_price', 'q', 'listing_intent', 'bhk',
  'property_id', 'min_sq_ft', 'max_sq_ft', 'city', 'location', 'sort',
];

function buildParams() {
  const params = new URLSearchParams();
  FILTER_KEYS.forEach((key) => {
    const el = form.elements.namedItem(key);
    if (!el || el.value == null) return;
    const val = String(el.value).trim();
    if (val) params.set(key, val);
  });
  return params;
}

function syncFormFromUrl() {
  const qs = new URLSearchParams(location.search);
  FILTER_KEYS.forEach((key) => {
    const el = form.elements.namedItem(key);
    if (!el || !qs.has(key)) return;
    el.value = qs.get(key);
  });
  setIntent(qs.get('listing_intent') || '');
}

function syncUrlFromParams(params) {
  const query = params.toString();
  history.replaceState(null, '', query ? `${location.pathname}?${query}` : location.pathname);
}

function showLoadingState() {
  if (!results) return;
  results.innerHTML = `
    <div class="col-12 listings-loading text-center py-5">
      <div class="spinner-border text-warning mb-3" role="status" aria-hidden="true"></div>
      <p class="mb-0 fw-semibold">Loading available properties…</p>
      <p class="text-muted small mt-1">Listings will appear here in a moment.</p>
    </div>`;
  noResults?.classList.add('d-none');
  listingsPromo?.classList.add('d-none');
  if (resultsCount) resultsCount.textContent = 'Loading properties...';
}

function syncQuickChips() {
  const intent = (intentInput?.value || '').trim();
  const type = (form.elements.namedItem('type')?.value || '').trim();
  document.querySelectorAll('.listing-quick-chip').forEach((chip) => {
    const chipIntent = chip.dataset.quickFilter;
    const chipType = chip.dataset.quickType;
    let active = false;
    if (chipIntent !== undefined) {
      active = chipIntent === intent;
    } else if (chipType) {
      active = chipType === type && !intent;
    }
    chip.classList.toggle('is-active', active);
  });
}

function cardHTML(p) {
  const media = listingMediaHTML(p);
  const intent = (p.listing_intent || 'buy').toUpperCase();
  const type = p.display_type || p.property_type;
  const sqft = p.sq_ft ? Math.round(p.sq_ft) : '-';
  return `<div class="${GRID_COL_CLASS}">
    <div class="card property-card">${media}<div class="card-body">
    <div class="d-flex gap-2 mb-2 flex-wrap">
      <span class="badge badge-listed"><i class="bi bi-check-circle"></i> Listed</span>
      <span class="badge badge-type">${type}</span>
      <span class="badge badge-status ${intent === 'RENT' ? 'badge-rent' : 'badge-buy'}">${intent}</span>
    </div>
    <h5 class="mb-1"><a href="/property/${p.slug}" class="text-decoration-none text-dark">${p.property_name}</a></h5>
    <p class="text-muted mb-1"><i class="bi bi-geo-alt"></i> ${p.area_name}, Surat</p>
    <p class="text-muted mb-2"><i class="bi bi-rulers"></i> ${sqft} sq.ft ${p.bhk ? `· ${p.bhk} BHK` : ''}</p>
    <p class="price">${formatINR(p.price)}${p.listing_type === 'rent' ? '/mo' : ''}</p>
    <p class="small text-muted line-clamp-2">${p.description || 'Verified property listing from JAKKASH.'}</p>
    <div class="d-flex gap-2 mt-2">
      <a href="/property/${p.slug}" class="btn btn-sm btn-jk-primary">View Details</a>
      <button class="btn btn-sm btn-jk-outline btn-save" data-id="${p.id}"><i class="bi bi-heart"></i></button>
    </div>
  </div></div></div>`;
}

function setIntent(value) {
  const selected = value || '';
  intentInput.value = selected;
  document.querySelectorAll('.btn-intent').forEach((item) => {
    item.classList.toggle('active', (item.dataset.intent || '') === selected);
  });
}

function openFilterDrawer() {
  if (!filterDrawer || !filterOverlay) return;
  filterDrawer.classList.add('open');
  filterOverlay.classList.add('open');
  filterDrawer.setAttribute('aria-hidden', 'false');
  filterOverlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('drawer-open');
}

function closeFilterDrawer() {
  if (!filterDrawer || !filterOverlay) return;
  filterDrawer.classList.remove('open');
  filterOverlay.classList.remove('open');
  filterDrawer.setAttribute('aria-hidden', 'true');
  filterOverlay.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('drawer-open');
}

async function load(options = {}) {
  showLoadingState();
  const params = buildParams();
  if (!options.skipUrlSync) {
    syncUrlFromParams(params);
  }
  setIntent(params.get('listing_intent') || '');
  syncQuickChips();
  const r = await fetch('/api/properties?' + params);
  const d = await r.json();
  if (!d.properties.length) {
    results.innerHTML = '';
    noResults.classList.remove('d-none');
    listingsPromo?.classList.add('d-none');
    resultsCount.textContent = '0 properties found';
    return;
  }
  noResults.classList.add('d-none');
  listingsPromo?.classList.remove('d-none');
  if (listingsPromoCount) {
    listingsPromoCount.textContent = `${d.properties.length} propert${d.properties.length === 1 ? 'y' : 'ies'}`;
  }
  resultsCount.textContent = `${d.properties.length} properties found`;
  results.innerHTML = d.properties.map(cardHTML).join('');
  initListingMedia(results);
  if (results.classList.contains('list-mode')) {
    results.querySelectorAll('.listing-card-col').forEach((col) => { col.className = LIST_COL_CLASS; });
  }
  document.querySelectorAll('.btn-save').forEach(btn => {
    btn.onclick = () => saveProperty(btn.dataset.id);
  });
}

function debounce(fn, wait = 350) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  load();
  closeFilterDrawer();
});

const debouncedLoad = debounce(load, 280);
document.getElementById('f_q')?.addEventListener('input', debouncedLoad);
document.getElementById('f_property_id')?.addEventListener('input', debouncedLoad);
document.getElementById('f_location')?.addEventListener('input', debouncedLoad);

document.querySelectorAll('.btn-intent').forEach((btn) => {
  btn.addEventListener('click', () => {
    setIntent(btn.dataset.intent || '');
    load();
  });
});

document.getElementById('resetFilters')?.addEventListener('click', () => {
  form.reset();
  setIntent('');
  history.replaceState(null, '', location.pathname);
  load({ skipUrlSync: true });
});

document.getElementById('browseAllBtn')?.addEventListener('click', () => {
  form.reset();
  setIntent('');
  history.replaceState(null, '', location.pathname);
  load({ skipUrlSync: true });
});

document.getElementById('openFiltersFromEmpty')?.addEventListener('click', openFilterDrawer);

document.querySelectorAll('.listing-quick-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    if (chip.dataset.quickFilter !== undefined) {
      setIntent(chip.dataset.quickFilter || '');
      const typeEl = form.elements.namedItem('type');
      if (typeEl) typeEl.value = '';
    } else if (chip.dataset.quickType) {
      const typeEl = form.elements.namedItem('type');
      if (typeEl) typeEl.value = chip.dataset.quickType;
      setIntent('');
    }
    load();
  });
});

openFiltersBtn?.addEventListener('click', (event) => {
  event.preventDefault();
  openFilterDrawer();
});
closeFiltersBtn?.addEventListener('click', closeFilterDrawer);
filterOverlay?.addEventListener('click', closeFilterDrawer);
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeFilterDrawer();
  }
});

closeFilterDrawer();
syncFormFromUrl();
load({ skipUrlSync: true });

document.getElementById('viewList')?.addEventListener('click', () => {
  document.getElementById('viewGrid')?.classList.remove('active');
  document.getElementById('viewList')?.classList.add('active');
  results.classList.add('list-mode');
  results.querySelectorAll('.listing-card-col').forEach((col) => { col.className = LIST_COL_CLASS; });
});

document.getElementById('viewGrid')?.addEventListener('click', () => {
  document.getElementById('viewList')?.classList.remove('active');
  document.getElementById('viewGrid')?.classList.add('active');
  results.classList.remove('list-mode');
  results.querySelectorAll('.listing-card-col').forEach((col) => { col.className = GRID_COL_CLASS; });
});
