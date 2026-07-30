from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.services import qdrant_service

router = APIRouter(prefix="/rag", tags=["Knowledge Base RAG"])

class RAGRequest(BaseModel):
    query: str
    limit: Optional[int] = 3

class RAGDocument(BaseModel):
    title: str
    category: str
    text: str
    score: float

@router.post("/query", response_model=List[RAGDocument])
def query_knowledge_base(request: RAGRequest, x_gemini_key: Optional[str] = Header(None)):
    """Search vector KB documents for safety advice, rights information, or ngo directories."""
    try:
        results = qdrant_service.search_safety_kb(
            query=request.query,
            limit=request.limit,
            api_key=x_gemini_key
        )
        
        doc_list = []
        for res in results:
            doc_list.append(RAGDocument(
                title=res["title"],
                category=res["category"],
                text=res["text"],
                score=res["score"]
            ))
        return doc_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
