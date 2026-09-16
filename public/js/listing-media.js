const DEFAULT_PROPERTY_IMAGE = '/static/img/default-property.jpg';

function mediaSrc(path) {
  if (!path) return DEFAULT_PROPERTY_IMAGE;
  const value = String(path).trim();
  if (!value) return DEFAULT_PROPERTY_IMAGE;
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/static/') || value.startsWith('static/')) {
    return value.startsWith('/') ? value : `/${value}`;
  }
  // Prefer API-resolved urls; never invent /uploads/ for relative storage keys
  // (those 404 on Vercel — static/property-uploads is ignored).
  if (value.startsWith('/uploads/')) return DEFAULT_PROPERTY_IMAGE;
  if (value.startsWith('/')) return value;
  return DEFAULT_PROPERTY_IMAGE;
}

function listingMediaPaths(p) {
  const images = [];
  (p.images || []).forEach((img) => {
    const path = typeof img === 'string' ? img : (img.url || img.file_path);
    const src = mediaSrc(path);
    if (src && !images.includes(src)) images.push(src);
  });
  (p.listing_images || []).forEach((path) => {
    const src = mediaSrc(path);
    if (src && !images.includes(src)) images.push(src);
  });
  const primary = p.primary_image_url || p.primary_image;
  const primarySrc = mediaSrc(primary);
  if (primarySrc && primarySrc !== DEFAULT_PROPERTY_IMAGE && !images.includes(primarySrc)) {
    images.unshift(primarySrc);
  } else if (primarySrc === DEFAULT_PROPERTY_IMAGE && !images.length) {
    // keep empty → empty-state placeholder rendered below
  }
  const videos = (p.videos || [])
    .map((v) => (typeof v === 'string' ? v : (v.url || v.file_path)))
    .map((path) => mediaSrc(path))
    .filter((src) => src && src !== DEFAULT_PROPERTY_IMAGE);
  return { images, videos };
}

function listingMediaHTML(p, options = {}) {
  const { images, videos } = listingMediaPaths(p);
  const wrapClass = options.wrapClass || 'listing-media';
  const height = options.height || 220;
  const fallbackAttr = "onerror=\"this.onerror=null;this.src='/static/img/default-property.jpg';\"";
  const defaultImg = `/static/img/default-property.jpg`;

  if (!images.length && !videos.length) {
    return `<div class="${wrapClass} ${wrapClass}--empty" style="height:${height}px">
      <img src="${defaultImg}" alt="" loading="lazy" ${fallbackAttr}>
    </div>`;
  }

  const hasBoth = images.length && videos.length;
  const tabs = hasBoth
    ? `<div class="listing-media-tabs" role="tablist">
        <button type="button" class="listing-media-tab is-active" data-tab="photos" role="tab">Photos</button>
        <button type="button" class="listing-media-tab" data-tab="videos" role="tab">Videos</button>
      </div>`
    : '';

  const photoSlides = images
    .map(
      (path, idx) =>
        `<img src="${mediaSrc(path)}" alt="" class="listing-media-slide${idx === 0 ? ' is-active' : ''}" loading="lazy" ${fallbackAttr}>`
    )
    .join('');

  const photoNav =
    images.length > 1
      ? `<button type="button" class="listing-media-nav listing-media-prev" aria-label="Previous photo"><i class="bi bi-chevron-left"></i></button>
         <button type="button" class="listing-media-nav listing-media-next" aria-label="Next photo"><i class="bi bi-chevron-right"></i></button>
         <div class="listing-media-dots">${images
           .map(
             (_, idx) =>
               `<button type="button" class="listing-media-dot${idx === 0 ? ' is-active' : ''}" data-index="${idx}" aria-label="Photo ${idx + 1}"></button>`
           )
           .join('')}</div>`
      : '';

  const videoSlides = videos
    .map(
      (path, idx) =>
        `<div class="listing-media-video${idx === 0 ? ' is-active' : ''}">
          <video controls playsinline preload="metadata" src="${mediaSrc(path)}"></video>
        </div>`
    )
    .join('');

  const badges = `<div class="listing-media-badges">
    ${images.length ? `<span class="listing-media-badge"><i class="bi bi-images"></i> ${images.length}</span>` : ''}
    ${videos.length ? `<span class="listing-media-badge listing-media-badge--video"><i class="bi bi-camera-video"></i> ${videos.length}</span>` : ''}
    ${options.badgeText ? `<span class="jv-property-badge">${options.badgeText}</span>` : ''}
  </div>`;

  const defaultTab = images.length ? 'photos' : 'videos';

  return `<div class="${wrapClass}" data-default-tab="${defaultTab}" style="--listing-media-height:${height}px">
    ${badges}
    ${tabs}
    <div class="listing-media-panel listing-media-panel--photos${images.length ? '' : ' d-none'}">
      ${photoSlides}
      ${photoNav}
    </div>
    <div class="listing-media-panel listing-media-panel--videos${videos.length ? '' : ' d-none'}">
      ${videoSlides}
    </div>
  </div>`;
}

function initListingMedia(root = document) {
  root.querySelectorAll('.listing-media:not([data-media-init])').forEach((block) => {
    block.dataset.mediaInit = 'true';
    const photosPanel = block.querySelector('.listing-media-panel--photos');
    const videosPanel = block.querySelector('.listing-media-panel--videos');
    const slides = photosPanel ? Array.from(photosPanel.querySelectorAll('.listing-media-slide')) : [];
    const dots = photosPanel ? Array.from(photosPanel.querySelectorAll('.listing-media-dot')) : [];
    let activeIndex = 0;

    function showSlide(index) {
      if (!slides.length) return;
      activeIndex = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => slide.classList.toggle('is-active', i === activeIndex));
      dots.forEach((dot, i) => dot.classList.toggle('is-active', i === activeIndex));
    }

    block.querySelector('.listing-media-prev')?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      showSlide(activeIndex - 1);
    });

    block.querySelector('.listing-media-next')?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      showSlide(activeIndex + 1);
    });

    dots.forEach((dot) => {
      dot.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        showSlide(Number(dot.dataset.index || 0));
      });
    });

    block.querySelectorAll('.listing-media-tab').forEach((tab) => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const mode = tab.dataset.tab;
        block.querySelectorAll('.listing-media-tab').forEach((t) => {
          t.classList.toggle('is-active', t === tab);
        });
        photosPanel?.classList.toggle('d-none', mode !== 'photos');
        videosPanel?.classList.toggle('d-none', mode !== 'videos');
      });
    });
  });
}

window.listingMediaHTML = listingMediaHTML;
window.initListingMedia = initListingMedia;
