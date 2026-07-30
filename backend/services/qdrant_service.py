import logging
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import google.generativeai as genai
from backend.services.gemini_service import configure_gemini

logger = logging.getLogger("nari.qdrant")

# Initialize in-memory Qdrant Client
# This handles local semantic storage without requiring Docker
qdrant_client = QdrantClient(location=":memory:")
COLLECTION_NAME = "nari_safety_kb"

# Seed raw documents
SEED_DOCUMENTS = [
    # Women's Safety Laws
    {
        "id": 1,
        "title": "IPC Section 354D - Stalking Law",
        "category": "Laws",
        "text": "Under Section 354D of the Indian Penal Code (IPC), stalking is a criminal offense. It is defined as a man following or contacting a woman repeatedly despite her clear indication of disinterest, or monitoring her internet/electronic communication. First offense is bailable with up to 3 years imprisonment; subsequent offenses are non-bailable with up to 5 years."
    },
    {
        "id": 2,
        "title": "IPC Section 354 - Outraging Modesty",
        "category": "Laws",
        "text": "IPC Section 354 criminalizes assault or use of criminal force to any woman with intent to outrage her modesty. This offense is non-bailable and carries a punishment of 1 to 5 years imprisonment and a fine."
    },
    {
        "id": 3,
        "title": "Code of Criminal Procedure Section 46(4) - Arrest after sunset",
        "category": "Laws",
        "text": "Under Section 46(4) of the CrPC, women cannot be arrested after sunset and before sunrise except in exceptional circumstances. Even in such exceptions, the arrest must be made by a woman police officer and requires prior written permission from a Judicial Magistrate First Class."
    },
    {
        "id": 4,
        "title": "IPC Section 509 - Verbal Harassment",
        "category": "Laws",
        "text": "Section 509 of the IPC penalizes words, gestures, or acts intended to insult the modesty of a woman. Using obscene words, making noises, or showing objects that intrude on a woman's privacy is bailable and carries up to 3 years imprisonment."
    },
    # Government Helplines
    {
        "id": 5,
        "title": "Emergency National Helpline - 112",
        "category": "Helplines",
        "text": "Dial 112 for the single emergency response support system in India. Integrates Police (100), Fire (101), Health (102), and Women Safety Help Desk. Available 24/7 across all states."
    },
    {
        "id": 6,
        "title": "Women Helpline - 1091",
        "category": "Helplines",
        "text": "Dial 1091 for the Women Helpline. This helpline is dedicated to women in distress, facing domestic violence, harassment, or transit threats. They coordinate immediate rescue and counseling."
    },
    {
        "id": 7,
        "title": "National Commission for Women Helpline - 7827170170",
        "category": "Helplines",
        "text": "NCW Helpline 7827170170 is a 24x7 helpline for women facing violence or harassment. It offers legal advice, safety coordination, and registers formal police reports."
    },
    {
        "id": 8,
        "title": "Cyber Cell Helpline - 1930 / Cyber Crime Portal",
        "category": "Helplines",
        "text": "For online harassment, morphing, stalking, or financial cyber fraud, dial 1930 or file a report at cybercrime.gov.in. Complaints can be filed anonymously."
    },
    # NGO Information
    {
        "id": 9,
        "title": "Jagori NGO Delhi",
        "category": "NGOs",
        "text": "Jagori is a prominent women's resource group in New Delhi. They provide helpline counseling, safe accommodation referrals, and legal advocacy. Helpline: +91 88267 76878 or +91 11 2669 2700."
    },
    {
        "id": 10,
        "title": "Sheroes Hangout / NGO Support",
        "category": "NGOs",
        "text": "An NGO support initiative focused on rehabilitation, counseling, legal aid, and safe spaces for acid attack survivors and domestic assault victims."
    },
    # Practical Self-Defense
    {
        "id": 11,
        "title": "Vocal deterrent techniques",
        "category": "Self-Defense",
        "text": "In a hostile environment, use a firm, loud, commanding voice. Shout 'NO' or 'STAY BACK' instead of screaming for help. This projects confidence, attracts bystander attention, and startles attackers."
    },
    {
        "id": 12,
        "title": "Physical safety key areas",
        "category": "Self-Defense",
        "text": "If physically cornered, target the attacker's vulnerable areas: eyes (scratch or gouge), nose (heel-palm strike upward), groin (knee strike), or throat. Keep personal alarms or pepper spray in an accessible pocket."
    }
]

def initialize_qdrant(api_key=None):
    """Create collection and seed document vectors in Qdrant."""
    try:
        # Check if collection already exists
        collections = qdrant_client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        
        # Determine embedding dimension. Gemini gemini-embedding-001 uses 3072-dim embeddings.
        vector_dim = 3072
        
        if not exists:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{COLLECTION_NAME}' created.")
            seed_documents(api_key)
        else:
            logger.info("Qdrant collection already exists.")

        # Ingest any custom PDF documents placed in backend/data/documents/
        try:
            from backend.services import pdf_ingest
            pdf_ingest.ingest_custom_pdfs(api_key)
        except Exception as e:
            logger.error(f"Error loading custom PDFs on startup: {e}")
    except Exception as e:
        logger.error(f"Error initializing Qdrant: {e}")

def get_text_embedding(text, api_key=None):
    """Generate embedding vector using Gemini API or OpenAI."""
    from backend.config import GEMINI_API_KEY, OPENAI_API_KEY
    key = api_key or OPENAI_API_KEY or GEMINI_API_KEY or os.getenv("OPENAI_API_KEY", os.getenv("open_ai_key", os.getenv("GEMINI_API_KEY", "")))
    if not key:
        return None
    try:
        if key.startswith("sk-"):
            from openai import OpenAI
            client = OpenAI(api_key=key)
            result = client.embeddings.create(
                model="text-embedding-3-large",
                input=[text]
            )
            return result.data[0].embedding
        else:
            has_key = configure_gemini(api_key)
            if not has_key:
                return None
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            # Handle padding / truncation to match 3072 dimensions
            emb = result['embedding']
            if len(emb) < 3072:
                emb = emb + [0.0] * (3072 - len(emb))
            elif len(emb) > 3072:
                emb = emb[:3072]
            return emb
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def seed_documents(api_key=None):
    """Seed documents into the vector database using vector points (or fallback IDs)."""
    points = []
    has_key = configure_gemini(api_key)
    
    logger.info("Seeding Qdrant database...")
    for doc in SEED_DOCUMENTS:
        vector = None
        if has_key:
            vector = get_text_embedding(doc["text"], api_key)
            
        # Fallback dummy vector if no API key
        if not vector:
            # 3072-dim dummy vector for offline compatibility
            vector = [0.1 * (doc["id"] % 5)] * 3072
            
        points.append(
            PointStruct(
                id=doc["id"],
                vector=vector,
                payload={
                    "title": doc["title"],
                    "category": doc["category"],
                    "text": doc["text"]
                }
            )
        )
    
    try:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points
        )
        logger.info(f"Successfully seeded {len(points)} documents to Qdrant.")
    except Exception as e:
        logger.error(f"Failed to seed Qdrant: {e}")

def search_safety_kb(query, limit=3, api_key=None):
    """Search for relevant documents in vector store. Falls back to text search if no API key."""
    has_key = configure_gemini(api_key)
    
    if not has_key:
        logger.info("No Gemini Key. Running keyword search fallback over RAG documents.")
        return keyword_search_fallback(query, limit)
        
    query_vector = get_text_embedding(query, api_key)
    if not query_vector:
        return keyword_search_fallback(query, limit)
        
    try:
        search_results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit
        ).points
        
        formatted_results = []
        for res in search_results:
            formatted_results.append({
                "title": res.payload.get("title"),
                "category": res.payload.get("category"),
                "text": res.payload.get("text"),
                "score": res.score
            })
        return formatted_results
    except Exception as e:
        logger.error(f"Qdrant search error: {e}. Falling back to keywords.")
        return keyword_search_fallback(query, limit)

def keyword_search_fallback(query, limit):
    """Fallback text match router when offline."""
    query_words = set(query.lower().split())
    scored_docs = []
    
    for doc in SEED_DOCUMENTS:
        score = 0
        doc_text = (doc["title"] + " " + doc["text"]).lower()
        for word in query_words:
            if word in doc_text:
                score += 1
                if word in doc["title"].lower():
                    score += 2 # Boost title matches
        if score > 0:
            scored_docs.append((doc, score))
            
    # Sort by score descending
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    # Return formatted payload list
    results = []
    for doc, score in scored_docs[:limit]:
        results.append({
            "title": doc["title"],
            "category": doc["category"],
            "text": doc["text"],
            "score": float(score) / 10.0 # Standardize metric format
        })
        
    # If no matches, return generic first items
    if not results:
        for doc in SEED_DOCUMENTS[:limit]:
            results.append({
                "title": doc["title"],
                "category": doc["category"],
                "text": doc["text"],
                "score": 0.0
            })
            
    return results

# Initialize collection immediately
initialize_qdrant()
