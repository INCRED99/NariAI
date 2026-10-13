import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import { MapPin, Phone, Navigation, Shield, Clock, Loader2, Copy, Check, Crosshair, ExternalLink, RotateCw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import client from '../api/client';
import { useLocation } from '../context/LocationContext';
import { createUserLocationIcon, createCategoryIcon, createInspectorIcon } from '../utils/leafletIcons';

// Subcomponent to capture map click events and report exact coordinates
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng);
    },
  });
  return null;
}

const NearbyPage = () => {
  const {
    latitude,
    longitude,
    locationName,
    isLive,
    copyCoordinates,
    copied,
    setCustomCoordinates,
    refreshLocation,
  } = useLocation();

  const [selectedCategory, setSelectedCategory] = useState('All');
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clickedSpot, setClickedSpot] = useState(null);
  const [copiedSpot, setCopiedSpot] = useState(false);

  const categories = ['All', 'Police Station', 'Hospital', 'Safe Haven', 'Pharmacy', 'Women Help Desk'];

  const userIcon = createUserLocationIcon();
  const inspectorIcon = createInspectorIcon();

  useEffect(() => {
    const fetchPlaces = async () => {
      setLoading(true);
      try {
        const res = await client.get(
          `/nearby-places?latitude=${latitude}&longitude=${longitude}&category=${encodeURIComponent(selectedCategory)}`
        );
        if (res.data) {
          setPlaces(
            res.data.map((item, idx) => ({
              id: idx + 1,
              name: item.name,
              category: item.name.toLowerCase().includes('police') ? 'Police Station' :
                        item.name.toLowerCase().includes('hospital') ? 'Hospital' :
                        item.name.toLowerCase().includes('pharmacy') ? 'Pharmacy' : selectedCategory,
              distance: `${item.distance_km.toFixed(2)} km`,
              address: item.desc,
              phone: item.phone,
              open: item.open || 'Verified Open',
              lat: item.lat,
              lng: item.lng,
              safety_score: item.safety_score,
              verified: true,
            }))
          );
        }
      } catch (err) {
        console.error('Error fetching nearby safe places:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPlaces();
  }, [latitude, longitude, selectedCategory]);

  const handleMapClick = (latlng) => {
    setClickedSpot({
      lat: latlng.lat,
      lng: latlng.lng,
    });
  };

  const copyClickedSpotCoords = () => {
    if (!clickedSpot) return;
    const txt = `${clickedSpot.lat.toFixed(6)}, ${clickedSpot.lng.toFixed(6)}`;
    navigator.clipboard?.writeText(txt);
    setCopiedSpot(true);
    setTimeout(() => setCopiedSpot(false), 2000);
  };

  const handleSetLocationFromClick = () => {
    if (!clickedSpot) return;
    setCustomCoordinates(clickedSpot.lat, clickedSpot.lng);
    setClickedSpot(null);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '24px', height: 'calc(100vh - 120px)' }}>
      
      {/* Left List & Filters Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto', paddingRight: '4px' }}>
        
        {/* Exact Coordinates Info Banner */}
        <div className="glass-panel" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Your Exact Coordinates
            </span>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '10px',
              background: isLive ? 'rgba(52, 199, 89, 0.15)' : 'rgba(255, 149, 0, 0.15)',
              color: isLive ? 'var(--accent-green)' : 'var(--accent-amber)',
              fontWeight: '700'
            }}>
              {isLive ? '● Live Sensor' : '● Reference GPS'}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '15px', fontWeight: '800', fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>
              {latitude.toFixed(6)}, {longitude.toFixed(6)}
            </span>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={copyCoordinates}
                className="glass-btn"
                style={{
                  padding: '6px 12px',
                  borderRadius: '8px',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                }}
              >
                {copied ? <Check style={{ width: '12px', height: '12px', color: 'var(--accent-green)' }} /> : <Copy style={{ width: '12px', height: '12px' }} />}
                {copied ? 'Copied' : 'Copy'}
              </button>

              <button
                onClick={refreshLocation}
                title="Refresh GPS"
                style={{
                  padding: '6px 8px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <RotateCw style={{ width: '12px', height: '12px' }} />
              </button>
            </div>
          </div>

          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            💡 <em>Tip: Click anywhere on the OpenStreetMap to inspect exact coordinates of any spot!</em>
          </p>
        </div>

        {/* Category Pills */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              style={{
                whiteSpace: 'nowrap',
                padding: '8px 16px',
                borderRadius: '20px',
                border: 'none',
                background: selectedCategory === cat ? 'var(--primary-gradient)' : 'var(--bg-input)',
                color: selectedCategory === cat ? '#fff' : 'var(--text-secondary)',
                fontWeight: '600',
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Places List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px', color: 'var(--text-secondary)', gap: '10px' }}>
              <Loader2 className="animate-spin" style={{ width: '20px', height: '20px' }} />
              <span>Discovering verified spots via OpenStreetMap...</span>
            </div>
          ) : places.length === 0 ? (
            <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No safe spots found nearby for this category.
            </div>
          ) : (
            places.map((place) => (
              <div key={place.id} className="glass-panel" style={{ padding: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h4 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>{place.name}</h4>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{place.address}</p>
                    <p style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--accent-cyan)', marginTop: '4px' }}>
                      📍 {place.lat.toFixed(5)}, {place.lng.toFixed(5)}
                    </p>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      background: 'rgba(52, 199, 89, 0.15)',
                      color: 'var(--accent-green)'
                    }}>
                      {place.distance}
                    </span>
                    {place.safety_score && (
                      <span style={{ fontSize: '10px', color: 'var(--accent-cyan)', fontWeight: '600' }}>
                        Safety: {place.safety_score}/100
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock style={{ width: '14px', height: '14px', color: 'var(--accent-amber)' }} />
                    {place.open}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
                  <a
                    href={`tel:${place.phone}`}
                    style={{
                      flex: 1,
                      textDecoration: 'none',
                      padding: '8px',
                      borderRadius: '8px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                      fontWeight: '600',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                    }}
                  >
                    <Phone style={{ width: '14px', height: '14px', color: 'var(--accent-green)' }} />
                    Call Now
                  </a>
                  <a
                    href={`https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${latitude}%2C${longitude}%3B${place.lat}%2C${place.lng}`}
                    target="_blank"
                    rel="noreferrer"
                    className="gradient-btn"
                    style={{ flex: 1, padding: '8px', fontSize: '12px', borderRadius: '8px', textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                  >
                    <Navigation style={{ width: '14px', height: '14px' }} />
                    OSM Route
                  </a>
                </div>
              </div>
            ))
          )}
        </div>

      </div>

      {/* Right Leaflet OpenStreetMap */}
      <div className="glass-panel" style={{ overflow: 'hidden', height: '100%', position: 'relative' }}>
        <MapContainer
          key={`${latitude}-${longitude}`}
          center={[latitude, longitude]}
          zoom={14}
          style={{ width: '100%', height: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />

          <MapClickHandler onMapClick={handleMapClick} />

          {/* Live User Location Pin */}
          <Marker position={[latitude, longitude]} icon={userIcon}>
            <Popup>
              <div style={{ padding: '4px' }}>
                <strong style={{ fontSize: '13px' }}>📍 Your Exact Position</strong><br />
                <span style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>
                  {latitude.toFixed(6)}, {longitude.toFixed(6)}
                </span><br />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{locationName}</span>
              </div>
            </Popup>
          </Marker>

          {/* Clicked Coordinate Inspector Pin */}
          {clickedSpot && (
            <Marker position={[clickedSpot.lat, clickedSpot.lng]} icon={inspectorIcon}>
              <Popup autoPan={true}>
                <div style={{ padding: '6px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <strong style={{ fontSize: '13px' }}>🎯 Inspected Coordinates</strong>
                  <div style={{ fontFamily: 'monospace', fontSize: '12px', background: 'var(--bg-input)', padding: '4px 8px', borderRadius: '6px' }}>
                    {clickedSpot.lat.toFixed(6)}, {clickedSpot.lng.toFixed(6)}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                    <button
                      onClick={copyClickedSpotCoords}
                      style={{
                        padding: '4px 8px',
                        fontSize: '11px',
                        borderRadius: '6px',
                        background: 'var(--primary-gradient)',
                        color: '#fff',
                        border: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      {copiedSpot ? 'Copied!' : 'Copy'}
                    </button>
                    <button
                      onClick={handleSetLocationFromClick}
                      style={{
                        padding: '4px 8px',
                        fontSize: '11px',
                        borderRadius: '6px',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        color: 'var(--text-primary)',
                        cursor: 'pointer'
                      }}
                    >
                      Set as My Position
                    </button>
                  </div>
                </div>
              </Popup>
            </Marker>
          )}

          {/* Safe Place Markers */}
          {places.map((p) => (
            <Marker key={p.id} position={[p.lat, p.lng]} icon={createCategoryIcon(p.category)}>
              <Popup>
                <div style={{ padding: '4px' }}>
                  <strong style={{ fontSize: '13px' }}>{p.name}</strong><br />
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{p.address}</span><br />
                  <span style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>
                    Coords: {p.lat.toFixed(5)}, {p.lng.toFixed(5)}
                  </span><br />
                  <div style={{ marginTop: '6px', display: 'flex', gap: '8px' }}>
                    <a href={`tel:${p.phone}`} style={{ color: '#0072FF', fontWeight: 'bold', fontSize: '12px' }}>
                      Call {p.phone}
                    </a>
                    <a
                      href={`https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${latitude}%2C${longitude}%3B${p.lat}%2C${p.lng}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#34C759', fontWeight: 'bold', fontSize: '12px' }}
                    >
                      Navigate (OSM)
                    </a>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Floating OpenStreetMap Attribution Badge */}
        <div style={{
          position: 'absolute',
          bottom: '16px',
          right: '16px',
          background: 'var(--bg-card)',
          backdropFilter: 'blur(12px)',
          padding: '8px 14px',
          borderRadius: '10px',
          border: '1px solid var(--border-color)',
          zIndex: 1000,
          fontSize: '11px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          boxShadow: '0 4px 14px rgba(0,0,0,0.2)'
        }}>
          <span style={{ color: 'var(--accent-green)', fontWeight: '700' }}>● OpenStreetMap</span>
          <a
            href={`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=15/${latitude}/${longitude}`}
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--accent-cyan)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <span>Full View</span>
            <ExternalLink style={{ width: '10px', height: '10px' }} />
          </a>
        </div>
      </div>

    </div>
  );
};

export default NearbyPage;
