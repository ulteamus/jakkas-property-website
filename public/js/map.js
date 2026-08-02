const map = L.map('propertyMap').setView([21.1702, 72.8311], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 14,
  attribution: '© OpenStreetMap',
}).addTo(map);

fetch('/api/properties/map')
  .then(r => r.json())
  .then(d => {
    const bounds = [];
    (d.markers || []).forEach(m => {
      if (!m.latitude || !m.longitude) return;
      const area = (m.area_name || 'Surat').trim() || 'Surat';
      const circle = L.circle([m.latitude, m.longitude], {
        radius: 1200,
        color: '#e67e22',
        fillColor: '#e67e22',
        fillOpacity: 0.25,
      })
        .addTo(map)
        .bindPopup(`Approximate Locality: ${area}, Surat`);
      bounds.push(circle.getBounds());
    });
    if (bounds.length) {
      const group = bounds.reduce((acc, b) => acc.extend(b), L.latLngBounds(bounds[0]));
      map.fitBounds(group.pad(0.15), { maxZoom: 13 });
    }
  });
