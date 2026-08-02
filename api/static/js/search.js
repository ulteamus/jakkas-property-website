const searchForm = document.getElementById('searchForm');
const searchResults = document.getElementById('searchResults');
const predictForm = document.getElementById('predictForm');
const predictResult = document.getElementById('predictResult');

async function runSearch(e) {
  if (e) e.preventDefault();
  const params = new URLSearchParams();
  ['q', 'city', 'type', 'listing_type', 'min_price', 'max_price', 'min_bedrooms'].forEach((key) => {
    const el = document.getElementById(key === 'type' ? 'type' : key);
    const val = el?.value;
    if (val) params.set(key === 'type' ? 'type' : key, val);
  });

  const res = await fetch(`/api/properties/search?${params}`);
  const data = await res.json();
  if (!data.success) return;

  if (!data.properties.length) {
    searchResults.innerHTML = '<p class="text-muted">No properties found.</p>';
    return;
  }
  searchResults.innerHTML = data.properties.map(renderPropertyCard).join('');
}

searchForm?.addEventListener('submit', runSearch);
runSearch();

predictForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const res = await apiFetch('/api/predict-price', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      area_sqft: +document.getElementById('pred_area').value,
      bedrooms: +document.getElementById('pred_beds').value,
      city: document.getElementById('pred_city').value,
      property_type: document.getElementById('pred_type').value,
    }),
  });
  const d = await res.json();
  if (d.success) {
    predictResult.innerHTML = `
      Predicted: ${formatINR(d.predicted_price)} |
      ${formatINR(d.price_per_sqft)}/sqft |
      Method: ${d.method} (${d.confidence} confidence)
    `;
  }
});
