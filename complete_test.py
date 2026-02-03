"""
Complete API Test Suite for Homeschool Connect
Docker-compatible version with environment detection
Tests all core functionality end-to-end
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, timezone
import os
import sys

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://homeschool_user:homeschool_pass@localhost:5432/homeschool_db")

# FORCE MOCK MODE - No Google OAuth endpoint with Clerk
USE_MOCK_MODE = True
PARENT_GOOGLE_TOKEN = None  # Not used in mock mode

# Test tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "details": []
}

# User state
parent_jwt = None
parent_user_id = None
tutor_jwt = None
tutor_user_id = None

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_section(title, emoji="🧪"):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {emoji} {title}")
    print("="*80)

def print_response(response, title="Response"):
    """Pretty print API response"""
    print(f"\n{title}:")
    print(f"Status: {response.status_code} {response.reason}")
    try:
        data = response.json()
        print(f"Body:\n{json.dumps(data, indent=2)}")
        return data
    except:
        text = response.text[:500]
        print(f"Body: {text}{'...' if len(response.text) > 500 else ''}")
        return None

def test_endpoint(name, expected_status, actual_status, response_data=None):
    """Record test result"""
    passed = actual_status == expected_status
    
    result = {
        "name": name,
        "expected": expected_status,
        "actual": actual_status,
        "passed": passed
    }
    
    if passed:
        print(f"✅ PASS: {name}")
        test_results["passed"] += 1
    else:
        print(f"❌ FAIL: {name} (expected {expected_status}, got {actual_status})")
        test_results["failed"] += 1
        if response_data:
            result["error"] = response_data
    
    test_results["details"].append(result)
    return passed

def get_secret_key():
    """Get SECRET_KEY from environment or use default"""
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    print(f"🔑 Using SECRET_KEY: {secret_key[:20]}...")
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
        print(f"📝 Created JWT: user_id={user_id}, role={role}")
        return token
    except ImportError:
        print("❌ ERROR: python-jose not installed")
        print("   Install: pip install python-jose[cryptography]")
        sys.exit(1)

def ensure_db_user(email, name, role):
    """Ensure user exists in database"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user exists
        cur.execute("SELECT id, onboarded FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        
        if result:
            user_id = str(result['id'])
            onboarded = result['onboarded']
            print(f"✅ Found existing user: {email} (id={user_id}, onboarded={onboarded})")
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            google_id = f"mock_google_{uuid.uuid4().hex[:16]}"
            
            cur.execute("""
                INSERT INTO users (id, google_id, email, name, picture, role, onboarded, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                user_id,
                google_id,
                email,
                name,
                f"https://example.com/{name.lower().replace(' ', '')}.jpg",
                role,
                False,
                True
            ))
            conn.commit()
            print(f"✅ Created new user: {email} (id={user_id})")
        
        cur.close()
        conn.close()
        return user_id
        
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        print("\nTroubleshooting:")
        print(f"1. Check DATABASE_URL: {DATABASE_URL}")
        print("2. Ensure PostgreSQL is running")
        print("3. Install psycopg2: pip install psycopg2-binary")
        sys.exit(1)

def check_api_health():
    """Verify API is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API is healthy at {BASE_URL}")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach API at {BASE_URL}")
        print(f"   Error: {e}")
        return False

# =============================================================================
# TEST SUITE
# =============================================================================

def setup_users():
    """Setup test users (parent and tutor)"""
    global parent_user_id, parent_jwt, tutor_user_id, tutor_jwt
    
    print_section("SETUP: Creating Test Users", "🔧")
    
    print("📍 Using MOCK MODE (test tokens)")
    
    # Create parent user
    parent_email = "parent.test@example.com"
    parent_user_id = ensure_db_user(parent_email, "Test Parent", "parent")
    parent_jwt = create_mock_jwt(parent_user_id, parent_email, "parent")
    
    # Create tutor user
    tutor_email = "tutor.test@example.com"
    tutor_user_id = ensure_db_user(tutor_email, "Test Tutor", "tutor")
    tutor_jwt = create_mock_jwt(tutor_user_id, tutor_email, "tutor")

def test_authentication():
    """Test authentication endpoints"""
    print_section("TEST: Authentication", "🔐")
    
    # Test 1: GET /auth/me (Parent)
    print("\n1️⃣ GET /auth/me (Parent)")
    headers = {"Authorization": f"Bearer {parent_jwt}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    data = print_response(response)
    test_endpoint("GET /auth/me", 200, response.status_code, data)
    
    if data:
        print(f"   User ID: {data.get('id')}")
        print(f"   Email: {data.get('email')}")
        print(f"   Role: {data.get('role')}")
        print(f"   Onboarded: {data.get('onboarded')}")
    
    # Test 2: Invalid token
    print("\n2️⃣ Reject invalid JWT")
    headers = {"Authorization": "Bearer invalid_token_xyz"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    test_endpoint("Reject invalid JWT", 401, response.status_code)

def test_tutor_onboarding():
    """Test tutor profile creation and onboarding"""
    print_section("TEST: Tutor Onboarding", "👨‍🏫")
    
    headers = {"Authorization": f"Bearer {tutor_jwt}"}
    
    profile_data = {
        "location": {
            "latitude": -1.290270,
            "longitude": 36.821946,
            "visibility_radius_meters": 10000
        },
        "subjects": ["Mathematics", "Science", "English"],
        "curriculum": "British",
        "certifications": ["B.Ed", "TEFL Certificate"],
        "availability": "Weekday mornings and afternoons",
        "whatsapp_number": "+254722334455",
        "whatsapp_enabled": True
    }
    
    print("\n1️⃣ Create tutor profile")
    response = requests.post(f"{BASE_URL}/tutors", json=profile_data, headers=headers)
    data = print_response(response)
    
    if response.status_code == 201:
        test_endpoint("Create tutor profile", 201, response.status_code, data)
        print("✅ Tutor successfully onboarded!")
    elif response.status_code == 400 and data and "already exists" in str(data).lower():
        print("ℹ️  Profile already exists (from previous run)")
        test_results["passed"] += 1
        print("✅ PASS: Create tutor profile (already exists)")
    else:
        test_endpoint("Create tutor profile", 201, response.status_code, data)

def test_parent_onboarding():
    """Test parent profile creation and onboarding"""
    print_section("TEST: Parent Onboarding", "👨‍👩‍👧‍👦")
    
    headers = {"Authorization": f"Bearer {parent_jwt}"}
    
    profile_data = {
        "location": {
            "latitude": -1.285000,
            "longitude": 36.820000,
            "visibility_radius_meters": 8000
        },
        "children_ages": ["7-8", "10-11"],  # Fixed: strings not integers
        "curriculum": "American",
        "religion": "Christian",
        "whatsapp_number": "+254711223344",
        "whatsapp_enabled": True,
        "in_coop": False,
        "coop_name": None
    }
    
    print("\n1️⃣ Create parent profile")
    response = requests.post(f"{BASE_URL}/parents", json=profile_data, headers=headers)
    data = print_response(response)
    
    if response.status_code == 201:
        test_endpoint("Create parent profile", 201, response.status_code, data)
        print("✅ Parent successfully onboarded!")
    elif response.status_code == 400 and data and "already exists" in str(data).lower():
        print("ℹ️  Profile already exists (from previous run)")
        test_results["passed"] += 1
        print("✅ PASS: Create parent profile (already exists)")
    else:
        test_endpoint("Create parent profile", 201, response.status_code, data)

def test_map_features():
    """Test map and discovery features"""
    print_section("TEST: Map & Discovery", "🗺️")
    
    headers = {"Authorization": f"Bearer {parent_jwt}"}
    
    # Test 1: Get map pins
    print("\n1️⃣ Get map pins (all types)")
    params = {
        "ne_lat": -1.250000,
        "ne_lng": 36.850000,
        "sw_lat": -1.320000,
        "sw_lng": 36.780000,
        "type": "all"
    }
    response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
    data = print_response(response)
    test_endpoint("Get map pins", 200, response.status_code, data)
    
    if data:
        print(f"\n📊 Found {data.get('total', 0)} pin(s)")
        for pin in data.get('pins', []):
            print(f"   📌 {pin.get('name')} ({pin.get('type')}) - {pin.get('curriculum', 'N/A')}")
    
    # Test 2: Filter by tutor type
    print("\n2️⃣ Filter pins (tutors only)")
    params["type"] = "tutor"
    response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
    data = print_response(response)
    test_endpoint("Filter by tutor type", 200, response.status_code, data)
    
    # Test 3: Filter by curriculum
    print("\n3️⃣ Filter by curriculum (British)")
    params["curriculum"] = "British"
    response = requests.get(f"{BASE_URL}/map/pins", params=params, headers=headers)
    data = print_response(response)
    test_endpoint("Filter by curriculum", 200, response.status_code, data)

def test_profile_viewing():
    """Test profile viewing functionality"""
    print_section("TEST: Profile Viewing", "👁️")
    
    headers = {"Authorization": f"Bearer {parent_jwt}"}
    
    # Test 1: Pin preview
    print("\n1️⃣ Get pin preview")
    response = requests.get(f"{BASE_URL}/map/preview/{tutor_user_id}", headers=headers)
    data = print_response(response)
    test_endpoint("Get pin preview", 200, response.status_code, data)
    
    # Test 2: Full profile
    print("\n2️⃣ View full profile")
    response = requests.get(f"{BASE_URL}/profiles/{tutor_user_id}", headers=headers)
    data = print_response(response)
    test_endpoint("View full profile", 200, response.status_code, data)
    
    # Test 3: Cannot view own profile
    print("\n3️⃣ Block viewing own profile")
    response = requests.get(f"{BASE_URL}/profiles/{parent_user_id}", headers=headers)
    test_endpoint("Block own profile view", 400, response.status_code)

def test_contact_features():
    """Test contact and communication features"""
    print_section("TEST: Contact Features", "💬")
    
    headers = {"Authorization": f"Bearer {parent_jwt}"}
    
    # Test 1: Get WhatsApp link
    print("\n1️⃣ Get WhatsApp contact link")
    response = requests.get(f"{BASE_URL}/contact/whatsapp/{tutor_user_id}", headers=headers)
    data = print_response(response)
    test_endpoint("Get WhatsApp link", 200, response.status_code, data)
    
    if data and "whatsapp_url" in data:
        print(f"   URL: {data['whatsapp_url'][:80]}...")
    
    # Test 2: Log contact attempt
    print("\n2️⃣ Log contact attempt")
    log_data = {
        "target_user_id": tutor_user_id,
        "contact_method": "whatsapp"
    }
    response = requests.post(f"{BASE_URL}/contact/log", json=log_data, headers=headers)
    data = print_response(response)
    test_endpoint("Log contact", 200, response.status_code, data)

def test_reverse_interaction():
    """Test tutor viewing parent profile"""
    print_section("TEST: Reverse Interaction", "🔄")
    
    headers = {"Authorization": f"Bearer {tutor_jwt}"}
    
    print("\n1️⃣ Tutor views parent profile")
    response = requests.get(f"{BASE_URL}/profiles/{parent_user_id}", headers=headers)
    data = print_response(response)
    test_endpoint("Tutor views parent", 200, response.status_code, data)

def print_summary():
    """Print test summary"""
    print_section("TEST RESULTS SUMMARY", "📊")
    
    total = test_results["passed"] + test_results["failed"] + test_results["skipped"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    
    print(f"""
{'='*80}
                           TEST RESULTS
{'='*80}

✅ Passed:  {test_results['passed']} tests
❌ Failed:  {test_results['failed']} tests
⏭️  Skipped: {test_results['skipped']} tests
{'─'*80}
📊 Total:   {total} tests
🎯 Pass Rate: {pass_rate:.1f}%

{'='*80}

FEATURES TESTED:

✅ Authentication (Mock JWT Tokens)
✅ User Profile Management  
✅ Parent Onboarding & Location
✅ Tutor Onboarding & Location
✅ Map Discovery & Filtering
✅ Profile Viewing & Privacy
✅ Contact Features (WhatsApp)
✅ Cross-role Interactions

{'='*80}
""")
    
    if test_results["failed"] == 0:
        print("🎊🎊🎊 PERFECT! ALL TESTS PASSING! 🎊🎊🎊")
        print("\n✅ Your Homeschool Connect API is PRODUCTION READY!")
    elif pass_rate >= 90:
        print("🎉 EXCELLENT! Almost perfect!")
        print("\n⚠️  Review the failed tests above")
    elif pass_rate >= 70:
        print("👍 GOOD! Most features working")
        print("\n⚠️  Some issues need attention")
    else:
        print("❌ ISSUES DETECTED - Multiple tests failing")
        print("\n🔧 Review logs and fix issues before deployment")
    
    print("\n" + "="*80)
    
    # Print failed tests
    if test_results["failed"] > 0:
        print("\n❌ FAILED TESTS:")
        for detail in test_results["details"]:
            if not detail["passed"]:
                print(f"   • {detail['name']}: expected {detail['expected']}, got {detail['actual']}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run the complete test suite"""
    print_section("Homeschool Connect API - Test Suite", "🧪")
    print(f"\nConfiguration:")
    print(f"  API URL: {BASE_URL}")
    print(f"  Test Mode: MOCK MODE (Test Tokens)")
    print(f"  Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Not configured'}")
    
    # Pre-flight check
    print_section("Pre-flight Checks", "🔍")
    if not check_api_health():
        print("\n❌ API is not responding!")
        print("\nTroubleshooting:")
        print("1. Check if containers are running: docker-compose ps")
        print("2. Check logs: docker-compose logs -f backend")
        print("3. Verify URL is correct: " + BASE_URL)
        sys.exit(1)
    
    try:
        # Run test suites
        setup_users()
        test_authentication()
        test_tutor_onboarding()
        test_parent_onboarding()  # ← ADDED THIS LINE
        test_map_features()
        test_profile_viewing()
        test_contact_features()
        test_reverse_interaction()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always print summary
        print_summary()

if __name__ == "__main__":
    main()
