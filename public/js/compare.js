const compareForm = document.getElementById('compareForm');
const compareTable = document.getElementById('compareTable');

async function runCompare(e) {
  if (e) e.preventDefault();
  const ids = document.getElementById('compareIds').value.trim();
  if (!ids) return;

  const res = await fetch(`/api/compare?ids=${encodeURIComponent(ids)}`);
  const data = await res.json();
  if (!data.success || !data.properties.length) {
    compareTable.innerHTML = '<p class="text-muted">No properties to compare.</p>';
    return;
  }

  const props = data.properties;
  const fields = [
    ['Title', (p) => p.title],
    ['City', (p) => p.city],
    ['Type', (p) => p.property_type],
    ['Price', (p) => formatINR(p.price)],
    ['Bedrooms', (p) => p.bedrooms],
    ['Bathrooms', (p) => p.bathrooms],
    ['Area (sqft)', (p) => p.area_sqft],
    ['Price/sqft', (p) => formatINR(p.price / Math.max(p.area_sqft, 1))],
    ['Listing', (p) => p.listing_type],
  ];

  let html = '<table class="compare-table"><thead><tr><th>Feature</th>';
  props.forEach((p) => { html += `<th>${p.title}</th>`; });
  html += '</tr></thead><tbody>';

  fields.forEach(([label, fn]) => {
    html += `<tr><td><strong>${label}</strong></td>`;
    props.forEach((p) => { html += `<td>${fn(p)}</td>`; });
    html += '</tr>';
  });

  html += '</tbody></table>';
  compareTable.innerHTML = html;
}

compareForm?.addEventListener('submit', runCompare);

if (document.getElementById('compareIds')?.value) {
  runCompare();
}
