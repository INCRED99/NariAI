import unittest
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def safe_print(msg):
    sys.stdout.buffer.write((msg + "\n").encode('utf-8', errors='replace'))

class TestNariBackendAPI(unittest.TestCase):
    def test_0_root(self):
        """Test API home root is alive."""
        res = requests.get("http://127.0.0.1:8000/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_1_risk_assessment(self):
        """Test risk assessment evaluator."""
        payload = {
            "location": "Sector 62, Noida",
            "transit_time": "23:45",
            "weather": "Dense Fog / Smog",
            "crime_index": "High",
            "crowd_density": 10,
            "message": "Walking alone. Streetlights are out and someone is following me."
        }
        res = requests.post(f"{BASE_URL}/risk-assessment", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("risk_score", data)
        self.assertIn("risk_category", data)
        self.assertIn("explanation", data)
        safe_print(f"\n[Test Risk Assessment]: Score={data['risk_score']} Category={data['risk_category']}")

    def test_2_sos(self):
        """Test emergency SOS broadcast & report logging."""
        payload = {
            "situation": "Stalking alert reported",
            "location_name": "Sector 62 Noida Metro Corridor",
            "latitude": 28.6273,
            "longitude": 77.3725,
            "battery_level": 80
        }
        res = requests.post(f"{BASE_URL}/sos", json=payload, headers={"Authorization": "Bearer mock_test_token"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("sms_body", data)
        self.assertTrue(len(data.get("contacts")) > 0)
        safe_print(f"\n[Test SOS SMS]: {data['sms_body']}")

    def test_3_safe_routes(self):
        """Test routing safety comparison engine."""
        payload = {
            "origin": "Sector 62 Noida",
            "destination": "Rajiv Chowk CP",
            "time_of_day": "20:30"
        }
        res = requests.post(f"{BASE_URL}/safe-routes", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("origin"), "Sector 62 Noida")
        self.assertTrue(len(data.get("routes")) > 0)
        safe_print(f"\n[Test Safe Routes]: Got {len(data['routes'])} routes.")

    def test_4_nearby_places(self):
        """Test nearby place retrieval sorted by security index."""
        params = {
            "latitude": 28.6273,
            "longitude": 77.3725,
            "category": "Police Station"
        }
        res = requests.get(f"{BASE_URL}/nearby-places", params=params)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) > 0)
        self.assertIn("safety_score", data[0])
        safe_print(f"\n[Test Nearby Safe Places]: Top spot = '{data[0]['name']}' score={data[0]['safety_score']}")

    def test_5_profile_crud(self):
        """Test profile settings updating & memory syncing."""
        payload = {
            "name": "Priya Sharma",
            "phone": "7007914594",
            "preferred_language": "Hindi (हिंदी)",
            "safe_word": "Blue Moon",
            "home_address": "Sector 62 Noida",
            "home_lat": 28.6273,
            "home_lng": 77.3725,
            "office_address": "Sector 18 Noida",
            "office_lat": 28.5730,
            "office_lng": 77.3220,
            "travel_routine": "Commute home via metro line daily at 7:30 PM",
            "emergency_contacts": [
                {"name": "Aarav", "relation": "Husband", "phone": "7007914594"},
                {"name": "Neha", "relation": "Sister", "phone": "+919123456789"},
                {"name": "Siddharth", "relation": "Roommate", "phone": "+919988776655"}
            ]
        }
        res = requests.post(f"{BASE_URL}/profile", json=payload, headers={"Authorization": "Bearer mock_test_token"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))
        
        # Verify GET profile returns details
        get_res = requests.get(f"{BASE_URL}/profile", headers={"Authorization": "Bearer mock_test_token"})
        self.assertEqual(get_res.status_code, 200)
        p_data = get_res.json()
        self.assertEqual(p_data["profile"]["preferred_language"], "Hindi (हिंदी)")
        safe_print(f"\n[Test Profile & Memory]: Saved language Hindi successfully.")

    def test_6_voice_panic(self):
        """Test file uploading voice panic decoder (multipart)."""
        files = {
            "file": ("panic_help.wav", b"simulated audio bytes content")
        }
        res = requests.post(f"{BASE_URL}/voice-panic", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("panic_detected"))
        self.assertIn("help", data.get("triggered_phrases"))
        safe_print(f"\n[Test Voice Panic]: Detected phrases {data['triggered_phrases']}")

    def test_7_conversation_risk(self):
        """Test chat conversation safety state orchestration (safe word trigger)."""
        payload = {
            "history": [
                {"role": "assistant", "content": "Hello! How can I help you?"}
            ],
            "user_message": "Blue Moon", # Safe word trigger phrase
            "user_id": "priya_sharma"
        }
        res = requests.post(f"{BASE_URL}/conversation-risk", json=payload, headers={"Authorization": "Bearer mock_test_token"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("is_emergency"))
        self.assertEqual(data.get("state"), "Emergency")
        safe_print(f"\n[Test Chat Orchestration State]: Active State = {data['state']}")

    def test_8_rag(self):
        """Test RAG collection retrieval."""
        payload = {
            "query": "What are my legal rights against stalking?"
        }
        res = requests.post(f"{BASE_URL}/rag/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) > 0)
        safe_print(f"\n[Test RAG Search]: Top matched law document: '{data[0]['title']}'")

if __name__ == "__main__":
    unittest.main()
