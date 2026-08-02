(function () {
  const form = document.getElementById('sellPropertyForm');
  const propertyTypeInput = document.getElementById('propertyTypeInput');
  const unitWrap = document.getElementById('unitNumberWrap');
  const unitLabel = document.getElementById('unitNumberLabel');
  const unitInput = document.getElementById('unitNumberInput');
  const apartmentWrap = document.getElementById('apartmentNumberWrap');
  const flatWrap = document.getElementById('flatNumberWrap');
  const submitterTypeInput = document.getElementById('submitterTypeInput');
  const contactSectionTitle = document.getElementById('contactSectionTitle');
  const contactNameLabel = document.getElementById('contactNameLabel');
  const contactNameInput = document.getElementById('contactNameInput');
  const areaValueInput = document.getElementById('areaValueInput');
  const areaUnitInput = document.getElementById('areaUnitInput');
  const areaSqFtInput = document.getElementById('areaSqFtInput');
  const areaConvertedHint = document.getElementById('areaConvertedHint');
  const expectedInput = document.getElementById('expectedPriceInput');

  if (!form) return;

  const unitLabels = {
    apartment: 'Apartment Number',
    villa: 'Villa Number',
    bungalow: 'Bungalow Number',
    plot: 'Plot Number',
    shop: 'Shop Number',
    office: 'Office Number',
  };

  const submitterLabels = {
    owner: {
      section: 'Owner Details (Mandatory)',
      label: 'Owner Name *',
      placeholder: 'Owner Name *',
    },
    broker: {
      section: 'Broker Details (Mandatory)',
      label: 'Broker Name *',
      placeholder: 'Broker Name *',
    },
    developer: {
      section: 'Developer Details (Mandatory)',
      label: 'Developer Name *',
      placeholder: 'Developer Name *',
    },
  };

  const AREA_TO_SQ_FT = {
    sq_ft: 1,
    sq_yard: 9,
    vigha: 17424,
    sq_meter: 10.7639,
  };

  function getPropertyType() {
    return (propertyTypeInput?.value || '').toLowerCase();
  }

  function setActiveChip(selector, value, attr) {
    document.querySelectorAll(selector).forEach((chip) => {
      chip.classList.toggle('is-active', chip.getAttribute(attr) === value);
    });
  }

  function syncSubmitterFields() {
    const type = (submitterTypeInput?.value || 'owner').toLowerCase();
    const config = submitterLabels[type] || submitterLabels.owner;
    if (contactSectionTitle) contactSectionTitle.textContent = config.section;
    if (contactNameLabel) contactNameLabel.textContent = config.label;
    if (contactNameInput) contactNameInput.placeholder = config.placeholder;
    setActiveChip('[data-submitter-type]', type, 'data-submitter-type');
  }

  function syncUnitFields() {
    if (!unitWrap || !unitInput) return;
    const type = getPropertyType();
    const isApartment = type === 'apartment';

    apartmentWrap?.classList.toggle('d-none', !isApartment);
    flatWrap?.classList.toggle('d-none', !isApartment);
    unitWrap.classList.toggle('d-none', isApartment);

    if (isApartment) {
      unitInput.removeAttribute('name');
      unitInput.disabled = true;
    } else {
      unitInput.setAttribute('name', 'bungalow_number');
      unitInput.disabled = false;
      const text = unitLabels[type] || 'Unit Number';
      if (unitLabel) unitLabel.textContent = text;
      unitInput.placeholder = text;
    }
  }

  function syncPropertyType() {
    const type = getPropertyType();
    setActiveChip('[data-property-type]', type, 'data-property-type');
    syncUnitFields();
  }

  function updateAreaSqFt() {
    const value = Number(areaValueInput?.value || 0);
    const unit = areaUnitInput?.value || 'sq_ft';
    const factor = AREA_TO_SQ_FT[unit] || 1;
    const sqFt = value > 0 ? value * factor : 0;

    if (areaSqFtInput) {
      areaSqFtInput.value = sqFt > 0 ? String(sqFt) : '';
    }

    if (areaConvertedHint) {
      if (sqFt > 0 && unit !== 'sq_ft') {
        areaConvertedHint.textContent = `≈ ${Math.round(sqFt).toLocaleString('en-IN')} sq. ft.`;
      } else {
        areaConvertedHint.textContent = '';
      }
    }

    setActiveChip('[data-area-unit]', unit, 'data-area-unit');
  }

  document.querySelectorAll('[data-submitter-type]').forEach((chip) => {
    chip.addEventListener('click', () => {
      if (submitterTypeInput) submitterTypeInput.value = chip.dataset.submitterType || 'owner';
      syncSubmitterFields();
    });
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
      return;
    }

    if (!areaSqFtInput?.value || Number(areaSqFtInput.value) <= 0) {
      e.preventDefault();
      areaValueInput?.focus();
      alert('Please enter a valid property area.');
      return;
    }

    if (!expectedInput?.value || Number(expectedInput.value) <= 0) {
      e.preventDefault();
      expectedInput?.focus();
      alert('Please enter your expected price.');
    }
  });

  syncSubmitterFields();
  syncPropertyType();
  updateAreaSqFt();
})();
