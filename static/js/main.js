// Property Broker AI - shared utilities

function formatINR(amount) {
  return '₹' + Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function renderPropertyCard(p) {
  const img = p.image_url
    ? `<img src="/${p.image_url}" alt="${p.title}">`
    : '<div class="placeholder-img">🏢</div>';
  return `
    <article class="property-card">
      <div class="card-image">${img}</div>
      <div class="card-body">
        <span class="badge">${p.property_type}</span>
        <h3><a href="/property/${p.id}">${p.title}</a></h3>
        <p class="location">${p.locality || ''}${p.locality ? ', ' : ''}${p.city}</p>
        <p class="price">${formatINR(p.price)}</p>
        <p class="meta">${p.bedrooms} BHK · ${p.area_sqft} sqft</p>
      </div>
    </article>
  `;
}

document.querySelectorAll('.chip[data-msg]').forEach((chip) => {
  chip.addEventListener('click', () => {
    const input = document.getElementById('chatInput');
    if (input) {
      input.value = chip.dataset.msg;
      document.getElementById('chatForm')?.requestSubmit();
    }
  });
});
