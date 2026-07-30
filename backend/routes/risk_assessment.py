from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.services import gemini_service

router = APIRouter(prefix="/risk-assessment", tags=["Risk Assessment"])

class RiskAssessmentRequest(BaseModel):
    location: str
    transit_time: str
    weather: str
    crime_index: str
    crowd_density: int
    message: str

@router.post("")
def assess_risk(request: RiskAssessmentRequest, x_gemini_key: Optional[str] = Header(None)):
    """Evaluate real-time risk context using Gemini or offline heuristic engines."""
    try:
        result = gemini_service.generate_risk_assessment(
            location=request.location,
            time_val=request.transit_time,
            weather=request.weather,
            crime_index=request.crime_index,
            crowd_density=request.crowd_density,
            message=request.message,
            api_key=x_gemini_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
