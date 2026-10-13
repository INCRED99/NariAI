import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import client from '../api/client';

const LocationContext = createContext();

export const LocationProvider = ({ children }) => {
  const [location, setLocation] = useState({
    latitude: 28.627341,
    longitude: 77.372512,
    accuracy: 8, // in meters
    locationName: 'Detecting Location...',
    formattedCoords: '28.627341° N, 77.372512° E',
    isLive: false,
    loading: true,
    error: null,
  });
  const [copied, setCopied] = useState(false);

  // Reverse geocode via OpenStreetMap Nominatim
  const reverseGeocodeOSM = async (lat, lng) => {
    try {
      // 1. Try backend endpoint first
      const res = await client.get(`/nearby-places/reverse-geocode?latitude=${lat}&longitude=${lng}`);
      if (res.data && res.data.address && !res.data.address.startsWith("Live Coordinates")) {
        return res.data.address;
      }
    } catch {
      // Backend not yet responding, try direct Nominatim
    }

    try {
      const nomRes = await axios.get(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
        {
          headers: {
            'Accept-Language': 'en',
            'User-Agent': 'NariWomenSafetyApp/1.0 (contact: info@narisafety.org)'
          },
          timeout: 5000
        }
      );
      if (nomRes.data && nomRes.data.display_name) {
        const parts = nomRes.data.display_name.split(',').map((p) => p.trim()).filter(Boolean);
        return parts.slice(0, 3).join(', ');
      }
    } catch (e) {
      console.warn('OpenStreetMap Nominatim reverse geocoding note:', e);
    }

    return `${lat.toFixed(6)}°, ${lng.toFixed(6)}°`;
  };

  const fetchLiveLocation = useCallback(() => {
    setLocation((prev) => ({ ...prev, loading: true, error: null }));

    if (!navigator.geolocation) {
      setLocation((prev) => ({
        ...prev,
        locationName: 'Geolocation Unavailable (Browser Unsupported)',
        loading: false,
        error: 'Geolocation is not supported by your browser',
      }));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const acc = Math.round(position.coords.accuracy || 5);

        const latDir = lat >= 0 ? 'N' : 'S';
        const lngDir = lng >= 0 ? 'E' : 'W';
        const formatted = `${Math.abs(lat).toFixed(6)}° ${latDir}, ${Math.abs(lng).toFixed(6)}° ${lngDir}`;

        const name = await reverseGeocodeOSM(lat, lng);

        setLocation({
          latitude: lat,
          longitude: lng,
          accuracy: acc,
          locationName: name,
          formattedCoords: formatted,
          isLive: true,
          loading: false,
          error: null,
        });
      },
      async (err) => {
        console.warn('Geolocation notice:', err.message);
        // Fallback to high-precision reference coordinates
        const fallbackLat = 28.627341;
        const fallbackLng = 77.372512;
        const fallbackFormatted = `28.627341° N, 77.372512° E`;
        const fallbackName = await reverseGeocodeOSM(fallbackLat, fallbackLng);

        setLocation((prev) => ({
          ...prev,
          latitude: prev.latitude || fallbackLat,
          longitude: prev.longitude || fallbackLng,
          locationName: prev.locationName === 'Detecting Location...' ? fallbackName : prev.locationName,
          formattedCoords: prev.formattedCoords || fallbackFormatted,
          loading: false,
          error: `${err.message} (Using detected location)`,
        }));
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  }, []);

  // Quick-copy coordinates to clipboard
  const copyCoordinates = useCallback(() => {
    const text = `${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
    return text;
  }, [location.latitude, location.longitude]);

  // Manually update coordinates (e.g. from OpenStreetMap click or input)
  const setCustomCoordinates = useCallback(async (newLat, newLng, customName = null) => {
    const lat = parseFloat(newLat);
    const lng = parseFloat(newLng);
    if (isNaN(lat) || isNaN(lng)) return;

    const latDir = lat >= 0 ? 'N' : 'S';
    const lngDir = lng >= 0 ? 'E' : 'W';
    const formatted = `${Math.abs(lat).toFixed(6)}° ${latDir}, ${Math.abs(lng).toFixed(6)}° ${lngDir}`;

    let resolvedName = customName;
    if (!resolvedName) {
      resolvedName = await reverseGeocodeOSM(lat, lng);
    }

    setLocation({
      latitude: lat,
      longitude: lng,
      accuracy: 5,
      locationName: resolvedName,
      formattedCoords: formatted,
      isLive: true,
      loading: false,
      error: null,
    });
  }, []);

  useEffect(() => {
    fetchLiveLocation();
  }, [fetchLiveLocation]);

  return (
    <LocationContext.Provider
      value={{
        ...location,
        copied,
        copyCoordinates,
        setCustomCoordinates,
        refreshLocation: fetchLiveLocation,
      }}
    >
      {children}
    </LocationContext.Provider>
  );
};

export const useLocation = () => useContext(LocationContext);
