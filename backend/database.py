import os
import json
import logging
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from backend.config import MONGO_URI, MONGO_DB_NAME, FALLBACK_DB_PATH

logger = logging.getLogger("nari.database")
logging.basicConfig(level=logging.INFO)

class JSONFallbackCollection:
    """Mock MongoDB collection using a local JSON file."""
    def __init__(self, db_fallback, collection_name):
        self.db = db_fallback
        self.name = collection_name

    def find_one(self, filter=None, *args, **kwargs):
        data = self.db._read_data()
        docs = data.get(self.name, [])
        if not filter:
            return docs[0] if docs else None
        
        for doc in docs:
            match = True
            for k, v in filter.items():
                if k == "_id" and isinstance(v, (str, ObjectId)):
                    if doc.get("_id") != str(v):
                        match = False
                elif doc.get(k) != v:
                    match = False
            if match:
                # Convert back string _id to ObjectId helper representation if needed
                return doc
        return None

    def find(self, filter=None, *args, **kwargs):
        data = self.db._read_data()
        docs = data.get(self.name, [])
        if not filter:
            return docs
        
        results = []
        for doc in docs:
            match = True
            for k, v in filter.items():
                if k == "_id" and isinstance(v, (str, ObjectId)):
                    if doc.get("_id") != str(v):
                        match = False
                elif doc.get(k) != v:
                    match = False
            if match:
                results.append(doc)
        return results

    def insert_one(self, document):
        data = self.db._read_data()
        if self.name not in data:
            data[self.name] = []
            
        doc_copy = dict(document)
        if "_id" not in doc_copy:
            doc_copy["_id"] = str(ObjectId())
        elif isinstance(doc_copy["_id"], ObjectId):
            doc_copy["_id"] = str(doc_copy["_id"])
            
        # Convert datetimes to strings for JSON
        for k, v in doc_copy.items():
            if isinstance(v, datetime):
                doc_copy[k] = v.isoformat()
                
        data[self.name].append(doc_copy)
        self.db._write_data(data)
        
        class InsertResult:
            inserted_id = doc_copy["_id"]
        return InsertResult()

    def update_one(self, filter, update, upsert=False):
        data = self.db._read_data()
        docs = data.get(self.name, [])
        
        # Check $set operators
        set_data = update.get("$set", {}) if isinstance(update, dict) else update
        
        # Convert datetimes in update
        for k, v in set_data.items():
            if isinstance(v, datetime):
                set_data[k] = v.isoformat()

        found = False
        for idx, doc in enumerate(docs):
            match = True
            for k, v in filter.items():
                if k == "_id" and isinstance(v, (str, ObjectId)):
                    if doc.get("_id") != str(v):
                        match = False
                elif doc.get(k) != v:
                    match = False
            if match:
                docs[idx].update(set_data)
                found = True
                break
                
        if not found and upsert:
            new_doc = dict(filter)
            new_doc.update(set_data)
            if "_id" not in new_doc:
                new_doc["_id"] = str(ObjectId())
            docs.append(new_doc)
            
        data[self.name] = docs
        self.db._write_data(data)
        
        class UpdateResult:
            modified_count = 1 if found else 0
            matched_count = 1 if found else 0
        return UpdateResult()

    def delete_one(self, filter):
        data = self.db._read_data()
        docs = data.get(self.name, [])
        initial_len = len(docs)
        
        docs = [doc for doc in docs if not all(doc.get(k) == v for k, v in filter.items())]
        data[self.name] = docs
        self.db._write_data(data)
        
        class DeleteResult:
            deleted_count = initial_len - len(docs)
        return DeleteResult()

    def delete_many(self, filter):
        data = self.db._read_data()
        docs = data.get(self.name, [])
        initial_len = len(docs)
        
        docs = [doc for doc in docs if not all(doc.get(k) == v for k, v in filter.items())]
        data[self.name] = docs
        self.db._write_data(data)
        
        class DeleteResult:
            deleted_count = initial_len - len(docs)
        return DeleteResult()

class JSONFallbackDatabase:
    """Mock MongoDB database loading/saving to JSON."""
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(file_path):
            self._write_data({})

    def _read_data(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_data(self, data):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error writing to JSON fallback DB: {e}")

    def __getitem__(self, name):
        return JSONFallbackCollection(self, name)


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_fallback = False
        self.connect()

    def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
            try:
                import certifi
                tls_ca = certifi.where()
            except ImportError:
                tls_ca = None
            
            kwargs = {"serverSelectionTimeoutMS": 2000}
            if tls_ca:
                kwargs["tlsCAFile"] = tls_ca
                
            self.client = MongoClient(MONGO_URI, **kwargs)
            # Force server check
            self.client.server_info()
            self.db = self.client[MONGO_DB_NAME]
            self.is_fallback = False
            logger.info("MongoDB connected successfully.")
        except (ServerSelectionTimeoutError, Exception) as e:
            logger.error(f"MongoDB connection failed: {e}. Falling back to local JSON file storage...")
            self.db = JSONFallbackDatabase(FALLBACK_DB_PATH)
            self.is_fallback = True
            logger.info(f"Successfully initialized local fallback database at {FALLBACK_DB_PATH}.")

    def check_connection_and_fallback(self):
        """Verify MongoDB connection and fallback dynamically if disconnected."""
        if self.is_fallback:
            return True, "Connected to local fallback JSON database"
        try:
            if self.client:
                # Force ping
                self.client.admin.command('ping')
                return True, "Connected to MongoDB"
            else:
                raise Exception("Client not initialized")
        except Exception as e:
            logger.error(f"MongoDB connection lost during check: {e}. Switching dynamically to JSON fallback.")
            self.db = JSONFallbackDatabase(FALLBACK_DB_PATH)
            self.is_fallback = True
            return True, f"MongoDB offline (ping failed: {str(e)}). Fell back to local storage."

    def get_collection(self, name):
        return self.db[name]


# Global database manager instance
db_manager = DatabaseManager()

# Helper access collections
def get_user_profiles_col():
    return db_manager.get_collection("user_profiles")

def get_incident_reports_col():
    return db_manager.get_collection("incident_reports")

def get_safety_alerts_col():
    return db_manager.get_collection("safety_alerts")

def get_safety_memories_col():
    return db_manager.get_collection("safety_memories")

# Seed default profile if empty
def seed_default_user():
    col = get_user_profiles_col()
    # Check if the database has any profiles seeded at all
    try:
        count = col.count_documents({})
    except Exception:
        # Fallback for mock/JSON fallback databases that might not support count_documents
        try:
            count = len(col.find({}))
        except Exception:
            count = 0
            
    if count == 0:
        default_profile = {
            "name": "Priya Sharma",
            "phone": "7007914594",
            "preferred_language": "English (US)",
            "safe_word": "Blue Moon",
            "home_address": "Home Address",
            "home_lat": 28.6273,
            "home_lng": 77.3725,
            "office_address": "Office Address",
            "office_lat": 28.5730,
            "office_lng": 77.3220,
            "travel_routine": json.dumps({
                "workdays": "Home to Office commute (Evening commute at 7:30 PM)",
                "weekends": "Home to Shopping Mall commute (Evening commute at 8:00 PM)"
            }),
            "emergency_contacts": [
                {"name": "Aarav Sharma", "relation": "Husband", "phone": "7007914594"},
                {"name": "Neha Verma", "relation": "Sister", "phone": "+91 91234 56789"},
                {"name": "Siddharth", "relation": "Roommate", "phone": "+91 99887 76655"}
            ]
        }
        col.insert_one(default_profile)
        logger.info("Default user profile seeded.")
    else:
        logger.info("User profiles collection already has records. Skipping seeding.")

# Run seeding immediately
seed_default_user()
