"""
Simple test script for Google OAuth endpoint.
This script helps you test the authentication flow.
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"


def test_health():
    """Test the health endpoint"""
    print("\n🏥 Testing health endpoint...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_google_auth(id_token: str, role: str = None):
    """
    Test Google OAuth authentication
    
    Args:
        id_token: Google ID token from OAuth flow
        role: Optional role ('parent' or 'tutor')
    """
    print(f"\n🔐 Testing Google Auth with role={role}...")
    
    payload = {"id_token": id_token}
    if role:
        payload["role"] = role
    
    response = requests.post(
        f"{API_BASE_URL}/auth/google",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Access Token (first 50 chars): {data['access_token'][:50]}...")
        print(f"User ID: {data['user']['id']}")
        print(f"Email: {data['user']['email']}")
        print(f"Name: {data['user']['name']}")
        print(f"Role: {data['user']['role']}")
        print(f"Onboarded: {data['user']['onboarded']}")
        return data
    else:
        print(f"❌ Error: {response.json()}")
        return None


def test_role_change(id_token: str, new_role: str):
    """
    Test that role cannot be changed after being set
    
    Args:
        id_token: Google ID token
        new_role: Role to attempt to change to
    """
    print(f"\n🔒 Testing role change protection (should fail)...")
    
    response = requests.post(
        f"{API_BASE_URL}/auth/google",
        json={"id_token": id_token, "role": new_role}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ Role change correctly rejected!")
        print(f"Error: {response.json()['detail']}")
    else:
        print(f"❌ Unexpected response: {response.json()}")


def main():
    """
    Main test function.
    
    To use this script:
    1. Get a Google ID token (see SETUP_GUIDE.md)
    2. Replace eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg2MzBhNzFiZDZlYzFjNjEyNTdhMjdmZjJlZmQ5MTg3MmVjYWIxZjYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgzMjkyMDY2MzI3NzAxODg1NTUiLCJlbWFpbCI6ImNvbGxpbnMua3VidUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNzY5ODkyNDU5LCJuYW1lIjoiQ29sbGlucyBLdWJ1IiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tsNjdEQURuX3dqaTRtRXE0VWNCUnYxdmlpVk5uWXdpMVZobTRyREZoSGdST3YwUGoxd2c9czk2LWMiLCJnaXZlbl9uYW1lIjoiQ29sbGlucyIsImZhbWlseV9uYW1lIjoiS3VidSIsImlhdCI6MTc2OTg5Mjc1OSwiZXhwIjoxNzY5ODk2MzU5LCJqdGkiOiIxZjY1YmMyMzg0NzVjMmU1NWNhNjRjYTRhNzQ0MGYyYzg4MzcwOTVjIn0.KSZWz81d9QY1c70Y9vA1GT6a_eCDzcD9PmcQ0UedOEbvxpBBWJCmXQ2HyNznOWqF0Xu-QdaPsKvz5WVIyLjMZ5tNiaMOr5UMXfWoat3gmcGpJNuAQftUrJXcHpIvWAp77Se2h2HS4IsTHjgvCwghGQCB6OFhPDBK_xhWDEMQEXtVIUfOWqrfvM140Irg9s5BYHKbR-ixJP86gM8Qb0V0KXrQq2ZX-FcDb-lDlm5jYSupat5mFNAXite5mNn9R00VkwEaBEqiDvjAi_kw6XTXqEz4c056tkPDVDMmjAr_jr-COoMOnX9-Q1B73bkNgb7L6__KexUa7HhUpjx3phs8SA below with your actual token
    3. Run: python test_auth.py
    """
    
    print("=" * 60)
    print("Google OAuth Authentication Test Suite")
    print("=" * 60)
    
    # First test: health check
    if not test_health():
        print("\n Server is not running! Start it with: uvicorn main:app --reload")
        return
    
    # TODO: Replace with your actual Google ID token
    GOOGLE_ID_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg2MzBhNzFiZDZlYzFjNjEyNTdhMjdmZjJlZmQ5MTg3MmVjYWIxZjYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgzMjkyMDY2MzI3NzAxODg1NTUiLCJlbWFpbCI6ImNvbGxpbnMua3VidUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNzY5ODkyNDU5LCJuYW1lIjoiQ29sbGlucyBLdWJ1IiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tsNjdEQURuX3dqaTRtRXE0VWNCUnYxdmlpVk5uWXdpMVZobTRyREZoSGdST3YwUGoxd2c9czk2LWMiLCJnaXZlbl9uYW1lIjoiQ29sbGlucyIsImZhbWlseV9uYW1lIjoiS3VidSIsImlhdCI6MTc2OTg5Mjc1OSwiZXhwIjoxNzY5ODk2MzU5LCJqdGkiOiIxZjY1YmMyMzg0NzVjMmU1NWNhNjRjYTRhNzQ0MGYyYzg4MzcwOTVjIn0.KSZWz81d9QY1c70Y9vA1GT6a_eCDzcD9PmcQ0UedOEbvxpBBWJCmXQ2HyNznOWqF0Xu-QdaPsKvz5WVIyLjMZ5tNiaMOr5UMXfWoat3gmcGpJNuAQftUrJXcHpIvWAp77Se2h2HS4IsTHjgvCwghGQCB6OFhPDBK_xhWDEMQEXtVIUfOWqrfvM140Irg9s5BYHKbR-ixJP86gM8Qb0V0KXrQq2ZX-FcDb-lDlm5jYSupat5mFNAXite5mNn9R00VkwEaBEqiDvjAi_kw6XTXqEz4c056tkPDVDMmjAr_jr-COoMOnX9-Q1B73bkNgb7L6__KexUa7HhUpjx3phs8SA"
    
    if GOOGLE_ID_TOKEN == "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg2MzBhNzFiZDZlYzFjNjEyNTdhMjdmZjJlZmQ5MTg3MmVjYWIxZjYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgzMjkyMDY2MzI3NzAxODg1NTUiLCJlbWFpbCI6ImNvbGxpbnMua3VidUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNzY5ODkyNDU5LCJuYW1lIjoiQ29sbGlucyBLdWJ1IiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tsNjdEQURuX3dqaTRtRXE0VWNCUnYxdmlpVk5uWXdpMVZobTRyREZoSGdST3YwUGoxd2c9czk2LWMiLCJnaXZlbl9uYW1lIjoiQ29sbGlucyIsImZhbWlseV9uYW1lIjoiS3VidSIsImlhdCI6MTc2OTg5Mjc1OSwiZXhwIjoxNzY5ODk2MzU5LCJqdGkiOiIxZjY1YmMyMzg0NzVjMmU1NWNhNjRjYTRhNzQ0MGYyYzg4MzcwOTVjIn0.KSZWz81d9QY1c70Y9vA1GT6a_eCDzcD9PmcQ0UedOEbvxpBBWJCmXQ2HyNznOWqF0Xu-QdaPsKvz5WVIyLjMZ5tNiaMOr5UMXfWoat3gmcGpJNuAQftUrJXcHpIvWAp77Se2h2HS4IsTHjgvCwghGQCB6OFhPDBK_xhWDEMQEXtVIUfOWqrfvM140Irg9s5BYHKbR-ixJP86gM8Qb0V0KXrQq2ZX-FcDb-lDlm5jYSupat5mFNAXite5mNn9R00VkwEaBEqiDvjAi_kw6XTXqEz4c056tkPDVDMmjAr_jr-COoMOnX9-Q1B73bkNgb7L6__KexUa7HhUpjx3phs8SA":
        print("\n Please replace eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg2MzBhNzFiZDZlYzFjNjEyNTdhMjdmZjJlZmQ5MTg3MmVjYWIxZjYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTAxNjI0Mjk0ODYtMnJwdGFmOTNkMWt0YTR0NHQwOHJzdW9vbTdzbHM4djUuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgzMjkyMDY2MzI3NzAxODg1NTUiLCJlbWFpbCI6ImNvbGxpbnMua3VidUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNzY5ODkyNDU5LCJuYW1lIjoiQ29sbGlucyBLdWJ1IiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tsNjdEQURuX3dqaTRtRXE0VWNCUnYxdmlpVk5uWXdpMVZobTRyREZoSGdST3YwUGoxd2c9czk2LWMiLCJnaXZlbl9uYW1lIjoiQ29sbGlucyIsImZhbWlseV9uYW1lIjoiS3VidSIsImlhdCI6MTc2OTg5Mjc1OSwiZXhwIjoxNzY5ODk2MzU5LCJqdGkiOiIxZjY1YmMyMzg0NzVjMmU1NWNhNjRjYTRhNzQ0MGYyYzg4MzcwOTVjIn0.KSZWz81d9QY1c70Y9vA1GT6a_eCDzcD9PmcQ0UedOEbvxpBBWJCmXQ2HyNznOWqF0Xu-QdaPsKvz5WVIyLjMZ5tNiaMOr5UMXfWoat3gmcGpJNuAQftUrJXcHpIvWAp77Se2h2HS4IsTHjgvCwghGQCB6OFhPDBK_xhWDEMQEXtVIUfOWqrfvM140Irg9s5BYHKbR-ixJP86gM8Qb0V0KXrQq2ZX-FcDb-lDlm5jYSupat5mFNAXite5mNn9R00VkwEaBEqiDvjAi_kw6XTXqEz4c056tkPDVDMmjAr_jr-COoMOnX9-Q1B73bkNgb7L6__KexUa7HhUpjx3phs8SA with an actual Google ID token")
        print("See SETUP_GUIDE.md for instructions on getting a token")
        return
    
    # Test 1: First login with parent role
    print("\n" + "=" * 60)
    print("Test 1: First Login (New User)")
    print("=" * 60)
    result = test_google_auth(GOOGLE_ID_TOKEN, role="parent")
    
    if not result:
        print("\nAuthentication failed. Check your token and try again.")
        return
    
    # Test 2: Login again (existing user)
    print("\n" + "=" * 60)
    print("Test 2: Subsequent Login (Existing User)")
    print("=" * 60)
    test_google_auth(GOOGLE_ID_TOKEN)
    
    # Test 3: Try to change role (should fail)
    print("\n" + "=" * 60)
    print("Test 3: Attempt Role Change (Should Fail)")
    print("=" * 60)
    test_role_change(GOOGLE_ID_TOKEN, new_role="tutor")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
