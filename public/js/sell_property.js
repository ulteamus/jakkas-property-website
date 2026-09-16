(function () {
  const form = document.getElementById('sellPropertyForm');
  const propertyTypeInput = document.getElementById('propertyTypeInput');
  const listingIntentInput = document.getElementById('listingIntentInput');
  const unitWrap = document.getElementById('unitNumberWrap');
  const unitLabel = document.getElementById('unitNumberLabel');
  const unitInput = document.getElementById('unitNumberInput');
  const blockWingWrap = document.getElementById('blockWingWrap');
  const bhkWrap = document.getElementById('bhkWrap');
  const bhkInput = document.getElementById('bhkInput');
  const apartmentWrap = document.getElementById('apartmentNumberWrap');
  const flatWrap = document.getElementById('flatNumberWrap');
  const submitterTypeInput = document.getElementById('submitterTypeInput');
  const sellerTypeInput = document.getElementById('sellerTypeInput');
  const contactSectionTitle = document.getElementById('contactSectionTitle');
  const contactNameLabel = document.getElementById('contactNameLabel');
  const contactNameInput = document.getElementById('contactNameInput');
  const areaValueInput = document.getElementById('areaValueInput');
  const areaValueLabel = document.getElementById('areaValueLabel');
  const areaUnitInput = document.getElementById('areaUnitInput');
  const areaSqFtInput = document.getElementById('areaSqFtInput');
  const areaConvertedHint = document.getElementById('areaConvertedHint');
  const expectedInput = document.getElementById('expectedPriceInput');

  if (!form) return;

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
      const active = chip.getAttribute(attr) === value;
      chip.classList.toggle('is-active', active);
      chip.classList.toggle('btn-orange', active);
    });
  }

  function syncSubmitterFields() {
    const type = (submitterTypeInput?.value || 'owner').toLowerCase();
    const config = submitterLabels[type] || submitterLabels.owner;
    if (contactSectionTitle) contactSectionTitle.textContent = config.section;
    if (contactNameLabel) contactNameLabel.textContent = config.label;
    if (contactNameInput) contactNameInput.placeholder = config.placeholder;
    if (sellerTypeInput) sellerTypeInput.value = type;
    setActiveChip('[data-submitter-type]', type, 'data-submitter-type');
  }

  function syncListingIntent() {
    const intent = (listingIntentInput?.value || 'sell').toLowerCase();
    setActiveChip('[data-listing-intent]', intent, 'data-listing-intent');
  }

  function syncBhkVisibility() {
    const type = getPropertyType();
    const hide = HIDE_BHK.has(type) || (type && !SHOW_BHK.has(type) && HIDE_BHK.has(type));
    const show = !type || SHOW_BHK.has(type);
    const shouldShow = show && !HIDE_BHK.has(type);
    if (bhkWrap) {
      bhkWrap.classList.toggle('d-none', !shouldShow);
      bhkWrap.style.opacity = shouldShow ? '1' : '0';
      bhkWrap.style.transition = 'opacity 180ms ease';
    }
    if (bhkInput) {
      bhkInput.disabled = !shouldShow;
      if (!shouldShow) bhkInput.value = '';
    }
  }

  function syncUnitFields() {
    if (!unitWrap || !unitInput) return;
    const type = getPropertyType();
    const isApartment = type === 'apartment' || type === 'flat';

    apartmentWrap?.classList.add('d-none');
    flatWrap?.classList.add('d-none');
    blockWingWrap?.classList.toggle('d-none', !isApartment);
    unitWrap.classList.remove('d-none');

    unitInput.setAttribute('name', 'unit_number');
    unitInput.disabled = false;
    const text = isApartment ? 'Flat / Unit Number' : (unitLabels[type] || 'Unit Number');
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

  document.querySelectorAll('[data-listing-intent]').forEach((chip) => {
    chip.addEventListener('click', () => {
      if (listingIntentInput) listingIntentInput.value = chip.dataset.listingIntent || 'sell';
      syncListingIntent();
    });
  });

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

  form.addEventListener('submit', async (e) => {
    updateAreaSqFt();
    syncSubmitterFields();

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
      return;
    }

    e.preventDefault();
    const submitBtn = form.querySelector('[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
    }
    try {
      const fd = new FormData(form);
      const res = await fetch(form.action || window.location.pathname, {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      // Treat any 2xx (response.ok) including 200/201 as success.
      let payload = null;
      try {
        payload = await res.json();
      } catch (_) {
        payload = null;
      }
      const ok =
        res.ok ||
        res.status === 200 ||
        res.status === 201 ||
        (payload && (payload.success === true || payload.status === 'success'));
      if (ok) {
        const msg =
          (payload && (payload.message || payload.error)) ||
          'Property submitted successfully! Our team will review and approve it shortly.';
        const serverThumbs = (payload && Array.isArray(payload.image_urls)) ? payload.image_urls : [];
        const localFiles = fd.getAll('images').filter((f) => f && typeof f !== 'string' && f.size);
        const confirmBox = document.getElementById('sellSubmitConfirm');
        const confirmMsg = document.getElementById('sellSubmitConfirmMsg');
        const confirmThumbs = document.getElementById('sellSubmitConfirmThumbs');
        if (confirmBox && confirmThumbs) {
          if (confirmMsg) confirmMsg.textContent = msg;
          confirmThumbs.innerHTML = '';
          const urls = serverThumbs.length
            ? serverThumbs
            : localFiles.slice(0, 8).map((f) => URL.createObjectURL(f));
          urls.forEach((src) => {
            const img = document.createElement('img');
            img.src = src;
            img.alt = 'Uploaded listing photo';
            img.className = 'rounded border';
            img.style.cssText = 'width:96px;height:72px;object-fit:cover;';
            img.onerror = function () {
              this.onerror = null;
              this.src = '/static/img/default-property.jpg';
            };
            confirmThumbs.appendChild(img);
          });
          if (!urls.length) {
            confirmThumbs.innerHTML = '<p class="small text-muted mb-0">No photos were attached to this submission.</p>';
          }
          if (payload && payload.media_warning) {
            const warn = document.createElement('p');
            warn.className = 'small text-warning mb-0 mt-2';
            warn.textContent = payload.media_warning;
            confirmThumbs.appendChild(warn);
          }
          confirmBox.classList.remove('d-none');
          form.classList.add('d-none');
          confirmBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Also land on My Listings after a short beat so both surfaces show thumbs.
          setTimeout(() => {
            window.location.href = '/my-listings';
          }, 2200);
          return;
        }
        alert(msg);
        window.location.href = '/my-listings';
        return;
      }
      const err =
        (payload && (payload.error || payload.message)) ||
        'Unable to submit property right now. Please try again.';
      alert(err);
    } catch (_) {
      alert('Unable to submit property right now. Please try again.');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });

  syncListingIntent();
  syncSubmitterFields();
  syncPropertyType();
  updateAreaSqFt();

  if (window.MediaFileManager) {
    MediaFileManager.bind(
      document.getElementById('sellImagesInput'),
      document.getElementById('sellImagesPreview'),
      { listClass: 'media-file-list--photos' }
    );
    MediaFileManager.bind(
      document.getElementById('sellVideosInput'),
      document.getElementById('sellVideosPreview'),
      { listClass: 'media-file-list--videos' }
    );
  }
})();
