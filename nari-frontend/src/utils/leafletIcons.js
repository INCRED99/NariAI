import L from 'leaflet';

// Fix for default Leaflet icon paths in bundled environments
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom glowing pulse icon for user's live coordinates
export const createUserLocationIcon = () =>
  L.divIcon({
    className: 'osm-user-pulse-icon',
    html: `
      <div style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
        <div style="position: absolute; width: 32px; height: 32px; border-radius: 50%; background: rgba(0, 198, 255, 0.35); animation: osm-pulse 2s infinite ease-out;"></div>
        <div style="position: absolute; width: 20px; height: 20px; border-radius: 50%; background: rgba(0, 198, 255, 0.6); box-shadow: 0 0 14px #00C6FF;"></div>
        <div style="position: absolute; width: 12px; height: 12px; border-radius: 50%; background: #ffffff; border: 2.5px solid #0072FF;"></div>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });

// Map pin creator with custom category styles
export const createCategoryIcon = (category = 'Police Station') => {
  let color = '#7A5CFF'; // default purple
  let symbol = '🛡️';

  const catLower = (category || '').toLowerCase();
  if (catLower.includes('police') || catLower.includes('women')) {
    color = '#0072FF';
    symbol = '👮';
  } else if (catLower.includes('hospital') || catLower.includes('medical') || catLower.includes('clinic')) {
    color = '#34C759';
    symbol = '🏥';
  } else if (catLower.includes('pharmacy')) {
    color = '#FF9500';
    symbol = '💊';
  } else if (catLower.includes('safe') || catLower.includes('haven') || catLower.includes('cafe')) {
    color = '#AF52DE';
    symbol = '☕';
  } else if (catLower.includes('metro') || catLower.includes('station')) {
    color = '#5856D6';
    symbol = '🚇';
  }

  return L.divIcon({
    className: 'osm-custom-pin',
    html: `
      <div style="
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        background: ${color};
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.35), 0 0 10px ${color}88;
        border: 2px solid #ffffff;
      ">
        <span style="transform: rotate(45deg); font-size: 14px; user-select: none;">${symbol}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

// Inspector pin when user clicks on OpenStreetMap to inspect exact coordinates
export const createInspectorIcon = () =>
  L.divIcon({
    className: 'osm-inspector-pin',
    html: `
      <div style="
        width: 34px;
        height: 34px;
        border-radius: 50% 50% 50% 0;
        background: #FF3B30;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 16px rgba(255, 59, 48, 0.7);
        border: 2px solid #ffffff;
      ">
        <span style="transform: rotate(45deg); font-size: 14px;">🎯</span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -34],
  });
