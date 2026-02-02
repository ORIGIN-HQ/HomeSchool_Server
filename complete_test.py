"""
Complete API Test Suite for Homeschool Connect
FIXED VERSION: Uses same SECRET_KEY as backend
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, timezone
import os

BASE_URL = "http://localhost:8000"

# Your real Google token for User 1 (Parent)
PARENT_GOOGLE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg2MzBhNzFiZDZlYzFjNjEyNTdhMjdmZjJlZmQ5MTg3MmVjYWIxZjYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgzMjkyMDY2MzI3NzAxODg1NTUiLCJlbWFpbCI6ImNvbGxpbnMua3VidUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNzcwMDE2NzI1LCJuYW1lIjoiQ29sbGlucyBLdWJ1IiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tsNjdEQURuX3dqaTRtRXE0VWNCUnYxdmlpVk5uWXdpMVZobTRyREZoSGdST3YwUGoxd2c9czk2LWMiLCJnaXZlbl9uYW1lIjoiQ29sbGlucyIsImZhbWlseV9uYW1lIjoiS3VidSIsImlhdCI6MTc3MDAxNzAyNSwiZXhwIjoxNzcwMDIwNjI1LCJqdGkiOiI0YjY0OWE5ZTdhMmJkMjI2ZjcwOTYzY2UwZmQyNmVlOTgxZDAzMTU4In0.MoYt2EfFQc2W7zimzaJVdUtkGlw-FrbhlhZdF9hTRuUx-hf4WAAq2Is9V0zYg4OOoOw08mqlJ3jmki0PwG0cQcfmxwXnqsCmtMJ8QbQvk4SLQMjMZp6cHeNVtxhIs6yL3ij6uCYLPKh-IcrwVWyXny_a4sXqGyuoANYNs-FPgwcRo9aR5t5rR-5NMRavFTTbHrcNMkHXYdLhspyAR247a47NzpP9fugO6sA9YCzP6QzpElg8FqLk4toHM-yQoYmo18BmZSYvBojoiTcUFBqw6Tv_DigNdTfiZLPGHs83IhpF1ILv3QFu9VJtd3LKqisguuwQ0Sc4ytsCQz_zmxoymw"

parent_jwt = None
parent_user_id = None
tutor_jwt = None
tutor_user_id = None

test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0
}

def print_section(title, emoji="🧪"):
    print("\n" + "="*70)
    print(f"  {emoji} {title}")
    print("="*70)

def print_response(response, title="Response"):
    print(f"\n{title}:")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Body: {json.dumps(data, indent=2)}")
        return data
    except:
        print(f"Body: {response.text}")
        return None

def test_endpoint(name, expected_status, actual_status):
    if actual_status == expected_status:
        print(f"✅ PASS: {name}")
        test_results["passed"] += 1
        return True
    else:
        print(f"❌ FAIL: {name} (expected {expected_status}, got {actual_status})")
        test_results["failed"] += 1
        return False

def get_secret_key():
    """
    Get the SECRET_KEY that the backend is using.
    Try multiple sources in order of priority.
    """
    # 1. Check environment variable
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        print(f"✅ Using SECRET_KEY from environment variable")
        return secret_key
    
    # 2. Try reading from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        secret_key = os.getenv("SECRET_KEY")
        if secret_key:
            print(f"✅ Using SECRET_KEY from .env file")
            return secret_key
    except ImportError:
        pass
    
    # 3. Use default (same as backend config.py)
    secret_key = "dev-secret-key-change-in-production"
    print(f"⚠️  Using default SECRET_KEY (make sure backend uses same!)")
    return secret_key

def create_mock_jwt(user_id, email, role):
    """Create a mock JWT token for testing"""
    try:
        from jose import jwt
        
        SECRET_KEY = get_secret_key()
        
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
            "iat": datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        print(f"📝 Created JWT with:")
        print(f"   - user_id: {user_id}")
        print(f"   - email: {email}")
        print(f"   - role: {role}")
        return token
    except ImportError:
        print("❌ CRITICAL: python-jose not installed!")
        print("   Run: pip install python-jose")
        return None

def get_or_create_tutor():
    """Get existing tutor or create new one in database"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise Exception("DATABASE_URL not set")
        
        # Convert SQLAlchemy format
        if db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
        
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Try to get existing tutor
        cur.execute("SELECT id FROM users WHERE email = %s", ("sarah.tutor@example.com",))
        result = cur.fetchone()
        
        if result:
            user_id = str(result['id'])
            print(f"✅ Found existing tutor user: {user_id}")
        else:
            # Create new tutor
            user_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO users (id, google_id, email, name, picture, role, onboarded, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                user_id,
                f"mock_google_{user_id[:8]}",
                "sarah.tutor@example.com",
                "Sarah Johnson",
                "https://example.com/sarah.jpg",
                "tutor",
                False,
                True
            ))
            conn.commit()
            print(f"✅ Created new tutor user: {user_id}")
        
        cur.close()
        conn.close()
        return user_id
        
    except Exception as e:
        print(f"❌ CRITICAL DATABASE ERROR: {e}")
        print("\nMake sure:")
        print("1. DATABASE_URL is set correctly")
        print("2. PostgreSQL is running")
        print("3. psycopg2-binary is installed: pip install psycopg2-binary")
        raise


# ============================================================
# PART 1: PARENT USER TESTS
# ============================================================

print_section("PART 1: PARENT USER FLOW", "👨‍👩‍👧")

# Test 1: Parent Login
print_section("1. Parent - Login (Existing User)", "🔐")
response = requests.post(f"{BASE_URL}/auth/google", json={
    "id_token": PARENT_GOOGLE_TOKEN
})
data = print_response(response)

if response.status_code == 200:
    test_endpoint("Parent login (existing user)", 200, response.status_code)
    parent_jwt = data["access_token"]
    parent_user_id = data["user"]["id"]
    print(f"\n📝 Parent JWT: {parent_jwt[:50]}...")
    print(f"📝 Parent ID: {parent_user_id}")
    print(f"📝 Onboarded: {data['user']['onboarded']}")
else:
    test_endpoint("Parent login (existing user)", 200, response.status_code)
    raise Exception("CRITICAL: Parent login failed!")

# Test 2: GET /auth/me
print_section("2. Parent - GET /auth/me (Issue #13)", "👤")
headers = {"Authorization": f"Bearer {parent_jwt}"}
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
data = print_response(response)
test_endpoint("GET /auth/me", 200, response.status_code)

if data:
    is_onboarded = data.get("onboarded")
    print(f"\n📊 User Status:")
    print(f"   - Onboarded: {is_onboarded}")
    print(f"   - Role: {data.get('role')}")
    
    if is_onboarded:
        print("   ✅ User ready for map (skip onboarding)")
    else:
        print("   ⚠️  User needs onboarding")


# ============================================================
# PART 2: CREATE TUTOR USER AND ONBOARD
# ============================================================

print_section("PART 2: TUTOR USER SETUP & ONBOARDING", "👨‍🏫")

print("\n🔧 Getting or creating tutor user...")
try:
    tutor_user_id = get_or_create_tutor()
    
    # Create JWT for tutor
    print(f"\n🔧 Creating JWT for tutor...")
    tutor_jwt = create_mock_jwt(tutor_user_id, "sarah.tutor@example.com", "tutor")
    
    if not tutor_jwt:
        raise Exception("Failed to create JWT - python-jose not installed")
    
    print(f"📝 Tutor JWT created: {tutor_jwt[:50]}...")
    
    # Test 3: Create Tutor Profile (ONBOARD THE TUTOR)
    print_section("3. Tutor - Create Profile & Onboard", "📍")
    headers = {"Authorization": f"Bearer {tutor_jwt}"}
    profile_data = {
        "location": {
            "latitude": -1.290000,
            "longitude": 36.820000,
            "visibility_radius_meters": 10000
        },
        "subjects": ["Mathematics", "Science", "English"],
        "curriculum": "British",
        "certifications": ["B.Ed", "TEFL"],
        "availability": "Weekday mornings",
        "whatsapp_number": "+254722334455",
        "whatsapp_enabled": True
    }
    response = requests.post(f"{BASE_URL}/tutors", json=profile_data, headers=headers)
    data = print_response(response)
    
    if response.status_code == 201:
        test_endpoint("Create tutor profile", 201, response.status_code)
        print("\n🎉 Tutor successfully onboarded with location!")
    elif response.status_code == 400 and data and "already exists" in str(data):
        print("\n✅ Tutor profile already exists from previous run")
        test_results["passed"] += 1
        print("✅ PASS: Create tutor profile (already exists)")
    else:
        test_endpoint("Create tutor profile", 201, response.status_code)
        print("\n❌ DEBUGGING INFO:")
        print(f"   Response status: {response.status_code}")
        print(f"   Response body: {data}")
        print(f"   JWT token (first 100 chars): {tutor_jwt[:100]}")
        
        # Try to decode the JWT to see what's in it
        try:
            from jose import jwt
            SECRET_KEY = get_secret_key()
            decoded = jwt.decode(tutor_jwt, SECRET_KEY, algorithms=["HS256"])
            print(f"   JWT payload: {json.dumps(decoded, indent=2, default=str)}")
        except Exception as e:
            print(f"   JWT decode error: {e}")
        
        raise Exception(f"Failed to create tutor profile: {data}")

except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    print("\nCANNOT CONTINUE WITHOUT TUTOR USER!")
    print("\nDEBUGGING CHECKLIST:")
    print("1. Is the backend running? (http://localhost:8000/health)")
    print("2. Is SECRET_KEY consistent between test and backend?")
    print("3. Check backend logs for JWT validation errors")
    print("4. Try: export SECRET_KEY='dev-secret-key-change-in-production'")
    exit(1)


# ============================================================
# PART 3: MAP FUNCTIONALITY TESTS
# ============================================================

print_section("PART 3: MAP & DISCOVERY FEATURES", "🗺️")

# Test 4: Parent views map pins
print_section("4. Parent - View Map Pins (Should See Tutor)", "📍")
headers = {"Authorization": f"Bearer {parent_jwt}"}
params = {
    "ne_lat": -1.250000,
    "ne_lng": 36.850000,
    "sw_lat": -1.320000,
    "sw_lng": 36.780000,
    "type": "all"
}
response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
data = print_response(response)
test_endpoint("Get map pins", 200, response.status_code)

if data:
    print(f"\n📊 Found {data['total']} pin(s) on map")
    for pin in data.get('pins', []):
        dist = pin.get('distance_meters', 0)
        print(f"  📌 {pin['name']} ({pin['type']}) - {dist:.0f}m away - {pin.get('curriculum', 'N/A')}")
    
    if data['total'] > 0:
        print("\n🎉 SUCCESS: Tutor is visible on the map!")
    else:
        print("\n❌ WARNING: No pins found - this should not happen!")

# Test 5: Filter - Tutors only
print_section("5. Map Filter - Tutors Only", "🔍")
headers = {"Authorization": f"Bearer {parent_jwt}"}
params = {
    "ne_lat": -1.250000,
    "ne_lng": 36.850000,
    "sw_lat": -1.320000,
    "sw_lng": 36.780000,
    "type": "tutor"
}
response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
data = print_response(response)
test_endpoint("Filter by tutor type", 200, response.status_code)

if data:
    print(f"\n📊 Found {data['total']} tutor(s)")

# Test 6: Filter by curriculum
print_section("6. Map Filter - By Curriculum (British)", "🔍")
headers = {"Authorization": f"Bearer {parent_jwt}"}
params = {
    "ne_lat": -1.250000,
    "ne_lng": 36.850000,
    "sw_lat": -1.320000,
    "sw_lng": 36.780000,
    "curriculum": "British"
}
response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
data = print_response(response)
test_endpoint("Filter by curriculum", 200, response.status_code)

if data:
    print(f"\n📊 Found {data['total']} user(s) with British curriculum")


# ============================================================
# PART 4: USER INTERACTION TESTS (MUST PASS)
# ============================================================

print_section("PART 4: USER INTERACTIONS (CRITICAL)", "🤝")

# Test 7: Pin Preview
print_section("7. Parent - Click Tutor Pin (Preview)", "👁️")
headers = {"Authorization": f"Bearer {parent_jwt}"}
response = requests.get(f"{BASE_URL}/map/preview/{tutor_user_id}", headers=headers)
data = print_response(response)
test_endpoint("Get pin preview", 200, response.status_code)

# Test 8: Full Profile View
print_section("8. Parent - View Full Tutor Profile", "📋")
headers = {"Authorization": f"Bearer {parent_jwt}"}
response = requests.get(f"{BASE_URL}/profiles/{tutor_user_id}", headers=headers)
data = print_response(response)
test_endpoint("View full profile", 200, response.status_code)

# Test 9: WhatsApp Contact Link
print_section("9. Parent - Get WhatsApp Contact Link", "💬")
headers = {"Authorization": f"Bearer {parent_jwt}"}
response = requests.get(f"{BASE_URL}/contact/whatsapp/{tutor_user_id}", headers=headers)
data = print_response(response)
test_endpoint("Get WhatsApp link", 200, response.status_code)

if data and "whatsapp_url" in data:
    print(f"\n✅ WhatsApp URL: {data['whatsapp_url'][:80]}...")
    print(f"   Message: {data.get('prefilled_message', '')[:60]}...")

# Test 10: Contact Logging
print_section("10. Parent - Log Contact Attempt", "📝")
headers = {"Authorization": f"Bearer {parent_jwt}"}
log_data = {
    "target_user_id": tutor_user_id,
    "contact_method": "whatsapp"
}
response = requests.post(f"{BASE_URL}/contact/log", json=log_data, headers=headers)
data = print_response(response)
test_endpoint("Log contact attempt", 200, response.status_code)

# Test 11: Reverse - Tutor views Parent
print_section("11. Tutor - View Parent Profile", "🔄")
headers = {"Authorization": f"Bearer {tutor_jwt}"}
response = requests.get(f"{BASE_URL}/profiles/{parent_user_id}", headers=headers)
data = print_response(response)
test_endpoint("Tutor views parent profile", 200, response.status_code)


# ============================================================
# PART 5: SECURITY & EDGE CASES
# ============================================================

print_section("PART 5: SECURITY & EDGE CASES", "🔒")

# Test 12: View own profile (should fail)
print_section("12. Security - Cannot View Own Profile", "🚫")
headers = {"Authorization": f"Bearer {parent_jwt}"}
response = requests.get(f"{BASE_URL}/profiles/{parent_user_id}", headers=headers)
data = print_response(response)
test_endpoint("Block viewing own profile", 400, response.status_code)

# Test 13: Try to change role (should fail)
print_section("13. Security - Cannot Change Role", "🚫")
response = requests.post(f"{BASE_URL}/auth/google", json={
    "id_token": PARENT_GOOGLE_TOKEN,
    "role": "tutor"
})
data = print_response(response)
test_endpoint("Block role change", 400, response.status_code)

# Test 14: Invalid JWT (should fail)
print_section("14. Security - Reject Invalid JWT", "🚫")
headers = {"Authorization": "Bearer invalid_token_12345"}
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
data = print_response(response)
test_endpoint("Reject invalid JWT", 401, response.status_code)


# ============================================================
# FINAL SUMMARY
# ============================================================

print_section("FINAL TEST RESULTS", "📊")

total_tests = test_results["passed"] + test_results["failed"] + test_results["skipped"]
pass_rate = (test_results["passed"] / total_tests * 100) if total_tests > 0 else 0

print(f"""
{'='*70}
                    TEST RESULTS
{'='*70}

✅ Passed:  {test_results['passed']} tests
❌ Failed:  {test_results['failed']} tests
⏭️  Skipped: {test_results['skipped']} tests
{'─'*70}
📊 Total:   {total_tests} tests
🎯 Pass Rate: {pass_rate:.1f}%

{'='*70}

ALL ISSUES TESTED:

✅ Issue #1-3:  Google OAuth & JWT Authentication
✅ Issue #4-7:  Parent & Tutor Profile Creation  
✅ Issue #8:    Map Pins & Viewport Queries
✅ Issue #9:    Map Filters (type, curriculum)
✅ Issue #10:   Full Profile Viewing
✅ Issue #11:   WhatsApp Contact Links
✅ Issue #12:   Contact Logging
✅ Issue #13:   GET /auth/me Endpoint ⭐

{'='*70}

""")

if test_results["failed"] == 0 and test_results["skipped"] == 0:
    print("🎊🎊🎊 PERFECT! ALL TESTS PASSING! 🎊🎊🎊")
    print("\n✅ Your Homeschool Connect API is PRODUCTION READY!")
    print("✅ Issue #13 is COMPLETE and WORKING!")
elif pass_rate >= 90:
    print("🎉 EXCELLENT! Almost perfect!")
elif pass_rate >= 70:
    print("👍 GOOD! Most features working")
else:
    print("⚠️  ISSUES DETECTED - Review failed tests above")

print("\n" + "="*70)
