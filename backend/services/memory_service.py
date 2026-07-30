import logging
from datetime import datetime
from bson import ObjectId
from backend.database import get_safety_memories_col
from backend.services import gemini_service

logger = logging.getLogger("nari.memory")

def get_all_memories(user_id="priya_sharma"):
    """Fetch all memories for a user from MongoDB."""
    col = get_safety_memories_col()
    cursor = col.find({"user_id": user_id})
    memories = []
    for doc in cursor:
        memories.append({
            "id": str(doc.get("_id")),
            "memory_type": doc.get("memory_type", "preference"),
            "content": doc.get("content"),
            "updated_at": doc.get("updated_at")
        })
    return memories

def get_memories_as_text(user_id="priya_sharma"):
    """Retrieve memories formatted as bullet points for LLM context injection."""
    memories = get_all_memories(user_id)
    if not memories:
        return "No safety habits or preferences recorded yet."
    
    bullets = []
    for mem in memories:
        bullets.append(f"- [{mem['memory_type'].upper()}] {mem['content']}")
    return "\n".join(bullets)

def add_memory(content, memory_type="preference", user_id="priya_sharma"):
    """Explicitly add a memory to MongoDB."""
    col = get_safety_memories_col()
    doc = {
        "user_id": user_id,
        "memory_type": memory_type,
        "content": content,
        "updated_at": datetime.utcnow()
    }
    result = col.insert_one(doc)
    logger.info(f"Added memory: '{content}'")
    return str(result.inserted_id)

def delete_memory(memory_id):
    """Delete a memory by its ID."""
    col = get_safety_memories_col()
    # Handle string IDs from JSON fallback or ObjectId
    try:
        oid = ObjectId(memory_id)
        result = col.delete_one({"_id": oid})
    except Exception:
        result = col.delete_one({"_id": str(memory_id)})
        
    return result.deleted_count > 0

def update_memory_content(memory_id, new_content):
    """Update a memory text block."""
    col = get_safety_memories_col()
    try:
        oid = ObjectId(memory_id)
        result = col.update_one({"_id": oid}, {"$set": {"content": new_content, "updated_at": datetime.utcnow()}})
    except Exception:
        result = col.update_one({"_id": str(memory_id)}, {"$set": {"content": new_content, "updated_at": datetime.utcnow()}})
    return result.modified_count > 0

def process_and_extract_memory(user_message, user_id="priya_sharma", api_key=None):
    """Analyze a user message to extract facts and update memories in MongoDB."""
    # Get current memories
    current_memories = get_all_memories(user_id)
    
    # Format for LLM prompt
    memories_for_gemini = [{"id": str(m["id"]), "content": m["content"]} for m in current_memories]
    
    # Run Gemini parser
    operations = gemini_service.extract_memory_facts(user_message, memories_for_gemini, api_key)
    
    if not operations:
        return
        
    logger.info(f"Memory extraction operations extracted: {operations}")
    for op in operations:
        action = op.get("action")
        m_type = op.get("memory_type", "preference")
        content = op.get("content")
        m_id = op.get("existing_memory_id")
        
        if action == "add":
            add_memory(content, m_type, user_id)
        elif action == "update" and m_id:
            update_memory_content(m_id, content)
            logger.info(f"Updated memory {m_id} to '{content}'")
        elif action == "delete" and m_id:
            delete_memory(m_id)
            logger.info(f"Deleted memory {m_id}")
            
# Seed initial memories if database is empty
def seed_default_memories():
    col = get_safety_memories_col()
    if col.find_one() is None:
        add_memory("User preferred language is English (US).", "preference")
        add_memory("User travels daily commute route.", "route")
        add_memory("User commutes late on Fridays around 8:00 PM.", "habit")
        add_memory("User safe word triggers is configured as 'Blue Moon'.", "preference")
        add_memory("Emergency contacts set are Aarav (Husband) and Neha (Sister).", "contact")
        logger.info("Default memories seeded.")

# Run seeding immediately
seed_default_memories()
