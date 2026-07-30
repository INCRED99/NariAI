import os
import json
import logging
from qdrant_client.models import PointStruct


logger = logging.getLogger("nari.pdf_ingest")

DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "documents")
STATE_FILE = os.path.join(DOCUMENTS_DIR, "ingestion_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ingested_files": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save ingestion state: {e}")

def get_file_mtime(filepath):
    try:
        return os.path.getmtime(filepath)
    except Exception:
        return 0

def chunk_text(text, chunk_size=800, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def ingest_custom_pdfs(api_key=None):
    """Scan custom documents folder, parse PDFs, and upload embeddings to Qdrant collection."""
    from backend.services import qdrant_service
    if not os.path.exists(DOCUMENTS_DIR):
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)
        return

    # Find all PDFs
    pdf_files = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        logger.info("No custom PDF documents found in backend/data/documents/.")
        return

    try:
        import pypdf
    except ImportError:
        logger.error("pypdf package is missing. Cannot parse PDF documents. Run 'pip install pypdf'.")
        return

    state = load_state()
    ingested_files = state.setdefault("ingested_files", {})
    
    points_to_upload = []
    # Start point IDs from a safe range that won't collide with default seed documents (IDs 1-12)
    current_point_id = 10000 + len(ingested_files) * 1000
    
    files_processed = 0

    for filename in pdf_files:
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        mtime = get_file_mtime(filepath)
        
        # Skip if already ingested and not modified
        if filename in ingested_files and ingested_files[filename] == mtime:
            continue
            
        logger.info(f"Ingesting new or modified PDF: {filename} (mtime: {mtime})")
        
        try:
            reader = pypdf.PdfReader(filepath)
            full_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                    
            if not full_text.strip():
                logger.warning(f"No text extracted from PDF: {filename}")
                continue
                
            chunks = chunk_text(full_text.strip())
            logger.info(f"Split {filename} into {len(chunks)} text chunks.")
            
            for chunk_idx, chunk in enumerate(chunks):
                # Generate embedding
                vector = qdrant_service.get_text_embedding(chunk, api_key)
                if not vector:
                    # Deterministic offline mock vector (3072-dim)
                    vector = [0.123 * ((current_point_id + chunk_idx) % 7)] * 3072
                    
                points_to_upload.append(
                    PointStruct(
                        id=current_point_id,
                        vector=vector,
                        payload={
                            "title": filename,
                            "category": "Custom Safety PDF",
                            "text": chunk
                        }
                    )
                )
                current_point_id += 1
                
            ingested_files[filename] = mtime
            files_processed += 1
        except Exception as e:
            logger.error(f"Error parsing PDF {filename}: {e}")

    if points_to_upload:
        try:
            qdrant_service.qdrant_client.upsert(
                collection_name=qdrant_service.COLLECTION_NAME,
                wait=True,
                points=points_to_upload
            )
            logger.info(f"Successfully ingested {files_processed} PDFs, uploaded {len(points_to_upload)} new vector points to Qdrant.")
            save_state(state)
        except Exception as e:
            logger.error(f"Failed to upsert PDF points to Qdrant: {e}")
