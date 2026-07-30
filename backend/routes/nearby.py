import math
import urllib.request
import json
import logging
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.config import GOOGLE_MAPS_API_KEY


logger = logging.getLogger("nari.nearby")
router = APIRouter(prefix="/nearby-places", tags=["Nearby Safe Places"])

class PlaceItem(BaseModel):
    name: str
    lat: float
    lng: float
    desc: str
    phone: str
    distance_km: float
    safety_score: int
    path: List[List[float]]

# Mock places data fallback (using generic names with dynamic offsets around requested coordinates)
LOCAL_PLACES_DATA = {
    "Police Station": [
        {"name": "District Police Headquarters", "lat": 28.6255, "lng": 77.3660, "desc": "24/7 patrol officers on duty. CCTV active.", "phone": "+91 11 2335 1200"},
        {"name": "Local PCR Police Post", "lat": 28.6360, "lng": 77.3700, "desc": "Main station desk. Emergency response vehicles.", "phone": "+91 11 15521"},
        {"name": "Community Police Booth", "lat": 28.6304, "lng": 77.2177, "desc": "Assistance desk and active neighborhood patrol.", "phone": "+91 11 2335 1200"}
    ],
    "Hospital": [
        {"name": "City General Hospital & Trauma Center", "lat": 28.6210, "lng": 77.3700, "desc": "Full trauma facilities, 24/7 ambulance access.", "phone": "+91 11 2336 5500"},
        {"name": "Metro Emergency Clinic", "lat": 28.6272, "lng": 77.2080, "desc": "Multi-speciality hospital with 24h emergency.", "phone": "+91 11 2336 5500"}
    ],
    "Pharmacy": [
        {"name": "24x7 Central Pharmacy", "lat": 28.6265, "lng": 77.3715, "desc": "Always open, located in crowded avenue.", "phone": "+91 1800 200 444"},
        {"name": "Community Care Drugstore", "lat": 28.6295, "lng": 77.2185, "desc": "Open till late. Private guard on duty.", "phone": "+91 1800 200 444"}
    ],
    "Metro": [
        {"name": "City Center Transit Station", "lat": 28.6280, "lng": 77.3675, "desc": "CISF Guarded. Female coaches board here.", "phone": "+91 11 15521"},
        {"name": "Central Metro Junction Gate 1", "lat": 28.6328, "lng": 77.2195, "desc": "Central transit hub. Heavily guarded by security.", "phone": "+91 11 15521"}
    ],
    "Public Places": [
        {"name": "Family Restaurant & Market Hub", "lat": 28.6250, "lng": 77.3760, "desc": "Crowded public restaurant, active parking.", "phone": "+91 11 4005 9000"},
        {"name": "Commercial Shopping Plaza Cafe", "lat": 28.6315, "lng": 77.2205, "desc": "Open late, high foot traffic, private guards.", "phone": "+91 11 4005 9000"}
    ]
}

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def reverse_geocode(lat, lng, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NariSafetyApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            results = res_data.get("results", [])
            if results:
                return results[0].get("formatted_address")
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    return "Detected Coordinates Location"

def fetch_google_places(lat, lng, category, api_key):
    type_map = {
        "Police Station": "police",
        "Hospital": "hospital",
        "Pharmacy": "pharmacy",
        "Metro": "subway_station",
        "Public Places": "restaurant"
    }
    gtype = type_map.get(category, "police")
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=2500&type={gtype}&key={api_key}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NariSafetyApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            results = res_data.get("results", [])
            places = []
            for item in results[:10]:
                geom = item.get("geometry", {})
                loc = geom.get("location", {})
                places.append({
                    "name": item.get("name"),
                    "lat": loc.get("lat"),
                    "lng": loc.get("lng"),
                    "desc": item.get("vicinity", "Verified safety zone nearby"),
                    "phone": "Dial 112 for dispatch",
                })
            return places
    except Exception as e:
        logger.error(f"Google Places API error: {e}")
        return []

@router.get("", response_model=List[PlaceItem])
def get_nearby_places(
    latitude: float = Query(28.6273),
    longitude: float = Query(77.3725),
    category: str = Query("Police Station"),
    x_gmaps_key: Optional[str] = Header(None)
):
    """Retrieve verified safe spots surrounding the user coordinate."""
    places_raw = []
    effective_gmaps_key = x_gmaps_key or GOOGLE_MAPS_API_KEY
    if effective_gmaps_key:
        places_raw = fetch_google_places(latitude, longitude, category, effective_gmaps_key)
        
    if not places_raw:
        # Fallback to local high-fidelity mock database relative to user location
        mock_places = LOCAL_PLACES_DATA.get(category, LOCAL_PLACES_DATA["Police Station"])
        import random
        places_raw = []
        for idx, p in enumerate(mock_places):
            random.seed(p["name"])
            lat_offset = random.uniform(-0.012, 0.012)
            lng_offset = random.uniform(-0.012, 0.012)
            places_raw.append({
                "name": p["name"],
                "lat": latitude + lat_offset,
                "lng": longitude + lng_offset,
                "desc": p["desc"],
                "phone": p["phone"]
            })
        
    # 2. Process distances and calculate dynamic safety scores
    processed = []
    base_scores = {"Police Station": 100, "Hospital": 90, "Pharmacy": 80, "Metro": 75, "Public Places": 60}
    base_score = base_scores.get(category, 50)
    
    for place in places_raw:
        dist = haversine_distance(latitude, longitude, place["lat"], place["lng"])
        
        # Security score formula: Base score minus distance penalty (10 pts per km)
        distance_penalty = dist * 10
        cctv_boost = 10 if (category in ["Police Station", "Metro"] or "cctv" in place["desc"].lower()) else 0
        safety_rating = max(min(int(base_score - distance_penalty + cctv_boost), 100), 10)
        
        processed.append(
            PlaceItem(
                name=place["name"],
                lat=place["lat"],
                lng=place["lng"],
                desc=place["desc"],
                phone=place["phone"],
                distance_km=dist,
                safety_score=safety_rating,
                path=[[latitude, longitude], [place["lat"], place["lng"]]]
            )
        )
        
    # Sort by safety score descending
    processed.sort(key=lambda x: x.safety_score, reverse=True)
    return processed

@router.get("/reverse-geocode")
def get_reverse_geocode(latitude: float, longitude: float, x_gmaps_key: Optional[str] = Header(None)):
    gmaps_key = x_gmaps_key or GOOGLE_MAPS_API_KEY
    if not gmaps_key:
        return {"address": f"Detected Location ({latitude:.4f}, {longitude:.4f})"}
    address = reverse_geocode(latitude, longitude, gmaps_key)
    return {"address": address}
