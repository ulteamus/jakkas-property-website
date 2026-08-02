const map = L.map('propertyMap').setView([21.1702, 72.8311], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map);

function icon() {
  const c = '#F79433';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="background:${c};width:28px;height:28px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

fetch('/api/properties/map')
  .then(r => r.json())
  .then(d => {
    d.markers.forEach(m => {
      if (!m.latitude || !m.longitude) return;
      const thumb = m.primary_image ? `/uploads/${m.primary_image}` : '';
      const popup = `
        <div style="min-width:180px">
          ${thumb ? `<img src="${thumb}" style="width:100%;height:80px;object-fit:cover;border-radius:6px">` : ''}
          <strong>${m.property_name}</strong><br>
          ${m.area_name}<br>
          <b>${m.price_fmt}</b><br>
          <a href="/property/${m.slug}" class="btn btn-sm btn-warning mt-1">View Details</a>
        </div>`;
      L.marker([m.latitude, m.longitude], { icon: icon() })
        .addTo(map).bindPopup(popup);
    });
  });
