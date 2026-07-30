import hashlib
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.services import gemini_service

router = APIRouter(prefix="/safe-routes", tags=["Route Safety"])

class RouteRequest(BaseModel):
    origin: str
    destination: str
    time_of_day: Optional[str] = "20:00"
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None

class RouteMetrics(BaseModel):
    safety_score: int
    streetlight_density: int
    police_booths: int
    cctv_zones: int
    foot_traffic: str
    duration_mins: int

class RouteItem(BaseModel):
    category: str  # "Safest" | "Fastest" | "Balanced"
    description: str
    path: List[List[float]]
    metrics: RouteMetrics
    explanation_html: str

class RouteResponse(BaseModel):
    origin: str
    destination: str
    routes: List[RouteItem]

# Pre-defined Noida Sector 62 coordinates for fallback paths
FALLBACK_SAFE_PATH = [
    [28.6273, 77.3725],  # Sector 62 Main Road
    [28.6250, 77.3500],  # Sector 61 Corridor
    [28.6120, 77.3500],  # Sector 50 Boulevard
    [28.5830, 77.3300],  # Sector 37 Metro Line
    [28.5730, 77.3220]   # Sector 18 Commercial Hub
]

FALLBACK_FASTEST_PATH = [
    [28.6273, 77.3725],  # Sector 62
    [28.6050, 77.3600],  # Industrial Area Block B (Dark Stretch)
    [28.5900, 77.3400],  # Sector 34 Back lanes
    [28.5730, 77.3220]   # Sector 18
]

FALLBACK_BALANCED_PATH = [
    [28.6273, 77.3725],  # Sector 62
    [28.6180, 77.3650],  # Sector 58 Commercial
    [28.6000, 77.3450],  # Sector 33 Residential
    [28.5850, 77.3350],  # Sector 36 Main Road
    [28.5730, 77.3220]   # Sector 18
]

# Pre-defined Bangalore coordinates for fallback paths (HSR to Koramangala)
BLR_SAFE_PATH = [
    [12.9141, 77.6413],  # HSR Layout
    [12.9250, 77.6350],  # Sector 3 Corridor
    [12.9300, 77.6300],  # 80 Feet Road
    [12.9352, 77.6244]   # Koramangala
]

BLR_FASTEST_PATH = [
    [12.9141, 77.6413],  # HSR
    [12.9200, 77.6250],  # Silk Board Back lanes (Dark stretch)
    [12.9352, 77.6244]   # Koramangala
]

BLR_BALANCED_PATH = [
    [12.9141, 77.6413],  # HSR
    [12.9280, 77.6380],  # Sector 4 Main Road
    [12.9352, 77.6244]   # Koramangala
]

def get_dynamic_metrics(origin: str, destination: str, category: str, time_of_day: str = "20:00") -> RouteMetrics:
    hash_str = f"{origin.strip().lower()}-{destination.strip().lower()}-{category}"
    h = int(hashlib.md5(hash_str.encode('utf-8')).hexdigest(), 16)
    
    # Parse transit hour to apply time-based factors
    try:
        hour = int(time_of_day.split(":")[0])
    except Exception:
        hour = 20
        
    is_late_night = hour >= 22 or hour < 5
    is_evening = hour >= 18 and hour < 22
    
    if category == "Safest":
        safety_score = 85 + (h % 15)  # 85 to 99
        if is_late_night:
            safety_score -= 8  # drops slightly at night, but remains the safest route
        elif is_evening:
            safety_score -= 2
        streetlight_density = 85 + (h % 15)  # 85 to 100
        police_booths = 1 + (h % 3)  # 1 to 3
        cctv_zones = 4 + (h % 5)  # 4 to 8
        foot_traffic = "Moderately Active" if is_late_night else "Highly Crowded"
        duration_mins = 15 + (h % 15)  # 15 to 29
    elif category == "Fastest":
        safety_score = 25 + (h % 25)  # 25 to 49
        if is_late_night:
            safety_score -= 15  # drops significantly at late night
        elif is_evening:
            safety_score -= 5
        streetlight_density = 25 + (h % 30)  # 25 to 54
        police_booths = 0
        cctv_zones = h % 2  # 0 or 1
        foot_traffic = "Isolated" if is_late_night else "Sparse"
        duration_mins = 8 + (h % 8)  # 8 to 15
    else:  # Balanced
        safety_score = 65 + (h % 18)  # 65 to 82
        if is_late_night:
            safety_score -= 10
        elif is_evening:
            safety_score -= 3
        streetlight_density = 65 + (h % 20)  # 65 to 84
        police_booths = h % 2  # 0 or 1
        cctv_zones = 1 + (h % 3)  # 1 to 3
        foot_traffic = "Sparse" if is_late_night else "Average"
        duration_mins = 11 + (h % 11)  # 11 to 21
        
    return RouteMetrics(
        safety_score=max(5, safety_score),
        streetlight_density=streetlight_density,
        police_booths=police_booths,
        cctv_zones=cctv_zones,
        foot_traffic=foot_traffic,
        duration_mins=duration_mins
    )

def interpolate_path(start_lat: float, start_lng: float, end_lat: float, end_lng: float, num_points=5, category="Safest") -> List[List[float]]:
    path = []
    h_seed = f"{start_lat:.4f}-{start_lng:.4f}-{end_lat:.4f}-{end_lng:.4f}-{category}"
    h_val = int(hashlib.md5(h_seed.encode()).hexdigest(), 16)
    
    for i in range(num_points):
        fraction = i / (num_points - 1)
        lat = start_lat + fraction * (end_lat - start_lat)
        lng = start_lng + fraction * (end_lng - start_lng)
        
        # Add dynamic wiggle to simulate actual road curves
        if 0 < i < num_points - 1:
            if category == "Safest":
                offset_lat = ((h_val % 40) - 20) / 4000.0
                offset_lng = (((h_val // 40) % 40) - 20) / 4000.0
            elif category == "Fastest":
                offset_lat = ((h_val % 20) - 10) / 6000.0
                offset_lng = (((h_val // 20) % 20) - 10) / 6000.0
            else: # Balanced
                offset_lat = ((h_val % 30) - 15) / 5000.0
                offset_lng = (((h_val // 30) % 30) - 15) / 5000.0
            lat += offset_lat
            lng += offset_lng
            
        path.append([lat, lng])
    return path

@router.post("", response_model=RouteResponse)
def get_safe_routes(request: RouteRequest, x_gemini_key: Optional[str] = Header(None), x_gmaps_key: Optional[str] = Header(None)):
    """Analyze alternative travel paths and return their safety metrics and explanation."""
    try:
        # Determine path coordinates based on input payload coordinates or keywords fallback
        start_lat = request.origin_lat
        start_lng = request.origin_lng
        end_lat = request.dest_lat
        end_lng = request.dest_lng

        if not start_lat or not start_lng or not end_lat or not end_lng:
            # Fallback coordinate checks based on text
            is_bangalore = any(k in request.origin.lower() or k in request.destination.lower() for k in ["bangalore", "hsr", "koramangala", "blr"])
            is_delhi = any(k in request.origin.lower() or k in request.destination.lower() for k in ["delhi", "cp", "connaught", "noida", "sector"])
            
            if is_bangalore:
                start_lat, start_lng = 12.9141, 77.6413
                end_lat, end_lng = 12.9352, 77.6244
            elif is_delhi:
                start_lat, start_lng = 28.6273, 77.3725
                end_lat, end_lng = 28.5730, 77.3220
            else:
                # Fallback to defaults
                start_lat, start_lng = 28.6273, 77.3725
                end_lat, end_lng = 28.5730, 77.3220

        safe_path = interpolate_path(start_lat, start_lng, end_lat, end_lng, 5, "Safest")
        fastest_path = interpolate_path(start_lat, start_lng, end_lat, end_lng, 4, "Fastest")
        balanced_path = interpolate_path(start_lat, start_lng, end_lat, end_lng, 5, "Balanced")

        # Get dynamic metrics with time of day context
        safest_metrics = get_dynamic_metrics(request.origin, request.destination, "Safest", request.time_of_day)
        fastest_metrics = get_dynamic_metrics(request.origin, request.destination, "Fastest", request.time_of_day)
        balanced_metrics = get_dynamic_metrics(request.origin, request.destination, "Balanced", request.time_of_day)
        
        # Get AI Explanations for each route option in parallel to avoid timeouts
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            fut_safest = executor.submit(
                gemini_service.generate_safe_route_explanation,
                "Safest Route B (AI Recommended)", request.origin, request.destination, safest_metrics.dict(), request.time_of_day, x_gemini_key
            )
            fut_fastest = executor.submit(
                gemini_service.generate_safe_route_explanation,
                "Shortest Route A (Unsafe)", request.origin, request.destination, fastest_metrics.dict(), request.time_of_day, x_gemini_key
            )
            fut_balanced = executor.submit(
                gemini_service.generate_safe_route_explanation,
                "Balanced Route C", request.origin, request.destination, balanced_metrics.dict(), request.time_of_day, x_gemini_key
            )
            safest_explanation = fut_safest.result()
            fastest_explanation = fut_fastest.result()
            balanced_explanation = fut_balanced.result()
        
        # Assemble routes list
        routes = [
            RouteItem(
                category="Safest",
                description="Route B: Safe Route (+5 min longer)",
                path=safe_path,
                metrics=safest_metrics,
                explanation_html=safest_explanation
            ),
            RouteItem(
                category="Fastest",
                description="Route A: Shortest Route (Direct)",
                path=fastest_path,
                metrics=fastest_metrics,
                explanation_html=fastest_explanation
            ),
            RouteItem(
                category="Balanced",
                description="Route C: Balanced Lighting",
                path=balanced_path,
                metrics=balanced_metrics,
                explanation_html=balanced_explanation
            )
        ]
        
        return RouteResponse(
            origin=request.origin,
            destination=request.destination,
            routes=routes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
