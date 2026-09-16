(function () {
  const form = document.getElementById('adminPropertyForm');
  if (!form) return;

  const propertyTypeInput = document.getElementById('propertyTypeInput');
  const listingIntentInput = document.getElementById('listingIntentInput');
  const listingTypeInput = document.getElementById('adminListingTypeInput');
  const unitWrap = document.getElementById('unitNumberWrap');
  const unitLabel = document.getElementById('unitNumberLabel');
  const unitInput = document.getElementById('unitNumberInput');
  const blockWingWrap = document.getElementById('blockWingWrap');
  const bhkWrap = document.getElementById('bhkWrap');
  const bhkInput = document.getElementById('bhkInput');
  const submitterTypeInput = document.getElementById('submitterTypeInput');
  const sellerTypeInput = document.getElementById('sellerTypeInput');
  const adminSellerTypeInput = document.getElementById('adminSellerTypeInput');
  const contactSectionTitle = document.getElementById('adminContactSectionTitle');
  const contactNameLabel = document.getElementById('contactNameLabel');
  const contactNameInput = document.getElementById('contactNameInput');
  const areaValueInput = document.getElementById('areaValueInput');
  const areaValueLabel = document.getElementById('areaValueLabel');
  const areaUnitInput = document.getElementById('areaUnitInput');
  const areaSqFtInput = document.getElementById('areaSqFtInput');
  const areaConvertedHint = document.getElementById('areaConvertedHint');

  const HIDE_BHK = new Set(['plot', 'land', 'shop', 'office']);
  const SHOW_BHK = new Set(['apartment', 'flat', 'bungalow', 'house', 'villa']);

  const unitLabels = {
    apartment: 'Flat / Unit Number',
    villa: 'Villa Number',
    bungalow: 'Bungalow Number',
    plot: 'Plot Number',
    shop: 'Shop Number',
    office: 'Office Number',
  };

  const areaUnitLabels = {
    sq_ft: { label: 'Enter the area in sqft *', placeholder: 'Enter the area in sqft' },
    sq_yard: { label: 'Enter the area in sq. yard *', placeholder: 'Enter the area in sq. yard' },
    vigha: { label: 'Enter the area in vigha *', placeholder: 'Enter the area in vigha' },
    sq_meter: { label: 'Enter the area in sq. meter *', placeholder: 'Enter the area in sq. meter' },
  };

  const submitterLabels = {
    owner: {
      section: 'Owner Details',
      label: 'Owner Name',
      placeholder: 'Owner Name',
    },
    broker: {
      section: 'Broker Details',
      label: 'Broker Name',
      placeholder: 'Broker Name',
    },
    developer: {
      section: 'Developer Details',
      label: 'Developer Name',
      placeholder: 'Developer Name',
    },
  };

  const AREA_TO_SQ_FT = {
    sq_ft: 1,
    sq_yard: 9,
    vigha: 17424,
    sq_meter: 10.7639,
  };

  function setActiveChip(selector, value, attr) {
    document.querySelectorAll(selector).forEach((chip) => {
      const active = chip.getAttribute(attr) === value;
      chip.classList.toggle('is-active', active);
      chip.classList.toggle('btn-orange', active);
    });
  }

  function getPropertyType() {
    return (propertyTypeInput?.value || '').toLowerCase();
  }

  function setSellerType(type) {
    const value = (type || 'owner').toLowerCase();
    const config = submitterLabels[value] || submitterLabels.owner;
    if (submitterTypeInput) submitterTypeInput.value = value;
    if (sellerTypeInput) sellerTypeInput.value = value;
    if (adminSellerTypeInput) adminSellerTypeInput.value = value;
    if (contactSectionTitle) contactSectionTitle.textContent = config.section;
    if (contactNameLabel) contactNameLabel.textContent = config.label;
    if (contactNameInput) contactNameInput.placeholder = config.placeholder;
    setActiveChip('[data-submitter-type]', value, 'data-submitter-type');
    setActiveChip('[data-admin-seller-type]', value, 'data-admin-seller-type');
  }

  function setListingPair(intentOrType) {
    const raw = (intentOrType || 'sell').toLowerCase();
    const isRent = raw === 'rent' || raw === 'rental';
    const intent = isRent ? 'rent' : 'sell';
    const listingType = isRent ? 'rent' : 'sale';
    if (listingIntentInput) listingIntentInput.value = intent;
    if (listingTypeInput) listingTypeInput.value = listingType;
    setActiveChip('[data-listing-intent]', intent, 'data-listing-intent');
    setActiveChip('[data-listing-type]', listingType, 'data-listing-type');
  }

  function syncBhkVisibility() {
    const type = getPropertyType();
    const shouldShow = !type || (SHOW_BHK.has(type) && !HIDE_BHK.has(type));
    bhkWrap?.classList.toggle('d-none', !shouldShow);
    if (bhkInput) bhkInput.disabled = !shouldShow;
  }

  function syncUnitFields() {
    if (!unitWrap || !unitInput) return;
    const type = getPropertyType();
    const isApartment = type === 'apartment' || type === 'flat';
    blockWingWrap?.classList.toggle('d-none', !isApartment);
    unitWrap.classList.remove('d-none');
    const text = isApartment ? 'Flat / Unit Number' : unitLabels[type] || 'Unit Number';
    if (unitLabel) unitLabel.textContent = text;
    unitInput.placeholder = isApartment ? 'e.g. 101, 903' : text;
  }

  function syncPropertyType() {
    const type = getPropertyType();
    setActiveChip('[data-property-type]', type, 'data-property-type');
    syncUnitFields();
    syncBhkVisibility();
  }

  function updateAreaSqFt() {
    const value = Number(areaValueInput?.value || 0);
    const unit = areaUnitInput?.value || 'sq_ft';
    const factor = AREA_TO_SQ_FT[unit] || 1;
    const sqFt = value > 0 ? value * factor : 0;
    const labels = areaUnitLabels[unit] || areaUnitLabels.sq_ft;
    if (areaValueLabel) areaValueLabel.textContent = labels.label;
    if (areaValueInput) areaValueInput.placeholder = labels.placeholder;
    if (areaSqFtInput) areaSqFtInput.value = sqFt > 0 ? String(sqFt) : '';
    if (areaConvertedHint) {
      areaConvertedHint.textContent =
        sqFt > 0 && unit !== 'sq_ft'
          ? `≈ ${Math.round(sqFt).toLocaleString('en-IN')} sq. ft.`
          : '';
    }
    setActiveChip('[data-area-unit]', unit, 'data-area-unit');
  }

  document.querySelectorAll('[data-listing-intent]').forEach((chip) => {
    chip.addEventListener('click', () => setListingPair(chip.dataset.listingIntent || 'sell'));
  });
  document.querySelectorAll('[data-listing-type]').forEach((chip) => {
    chip.addEventListener('click', () => setListingPair(chip.dataset.listingType || 'sale'));
  });
  document.querySelectorAll('[data-submitter-type]').forEach((chip) => {
    chip.addEventListener('click', () => setSellerType(chip.dataset.submitterType || 'owner'));
  });
  document.querySelectorAll('[data-admin-seller-type]').forEach((chip) => {
    chip.addEventListener('click', () => setSellerType(chip.dataset.adminSellerType || 'owner'));
  });
  document.querySelectorAll('[data-property-type]').forEach((chip) => {
    chip.addEventListener('click', () => {
      if (propertyTypeInput) propertyTypeInput.value = chip.dataset.propertyType || '';
      syncPropertyType();
    });
  });
  document.querySelectorAll('[data-area-unit]').forEach((chip) => {
    chip.addEventListener('click', () => {
      if (areaUnitInput) areaUnitInput.value = chip.dataset.areaUnit || 'sq_ft';
      updateAreaSqFt();
    });
  });
  areaValueInput?.addEventListener('input', updateAreaSqFt);

  form.addEventListener('submit', (e) => {
    updateAreaSqFt();
    if (!getPropertyType()) {
      e.preventDefault();
      alert('Please select a property type.');
      activateTab('property', { scrollTab: true });
    }
  });

  /* Horizontal tabs */
  const tabRoot = form.querySelector('[data-jk-tabs="admin-property"]');
  const tabButtons = tabRoot ? Array.from(tabRoot.querySelectorAll('[data-jk-tab]')) : [];
  const tabPanels = tabRoot ? Array.from(tabRoot.querySelectorAll('[data-jk-tab-panel]')) : [];

  function activateTab(name, opts) {
    if (!tabRoot || !name) return;
    tabButtons.forEach((btn) => {
      const on = btn.getAttribute('data-jk-tab') === name;
      btn.classList.toggle('is-active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
      if (on && opts && opts.scrollTab) {
        btn.scrollIntoView({ inline: 'nearest', block: 'nearest', behavior: 'smooth' });
      }
    });
    tabPanels.forEach((panel) => {
      const on = panel.getAttribute('data-jk-tab-panel') === name;
      panel.classList.toggle('is-active', on);
      if (on) panel.removeAttribute('hidden');
      else panel.setAttribute('hidden', '');
    });
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      activateTab(btn.getAttribute('data-jk-tab'), { scrollTab: true });
    });
  });

  form.addEventListener(
    'invalid',
    (e) => {
      const panel = e.target && e.target.closest ? e.target.closest('[data-jk-tab-panel]') : null;
      if (!panel) return;
      activateTab(panel.getAttribute('data-jk-tab-panel'), { scrollTab: true });
    },
    true
  );

  if (window.MediaFileManager) {
    MediaFileManager.bind(
      document.getElementById('adminImagesInput'),
      document.getElementById('adminImagesPreview'),
      { listClass: 'media-file-list--photos' }
    );
    MediaFileManager.bind(
      document.getElementById('adminVideosInput'),
      document.getElementById('adminVideosPreview'),
      { listClass: 'media-file-list--videos' }
    );
    MediaFileManager.bind(
      document.getElementById('adminDocsInput'),
      document.getElementById('adminDocsPreview')
    );
  }

  setSellerType(adminSellerTypeInput?.value || submitterTypeInput?.value || 'owner');
  setListingPair(listingIntentInput?.value || listingTypeInput?.value || 'sell');
  syncPropertyType();
  updateAreaSqFt();
})();
