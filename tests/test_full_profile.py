"""
Test suite for Issue 10: Full Profile View Endpoint

Endpoint: GET /profiles/{user_id}

Acceptance Criteria:
✓ Role-specific data returned - Different fields for parent vs tutor
✓ WhatsApp shown only if enabled - Privacy protection
✓ Public-safe fields only - No sensitive data leaked

User Journey Step:
This is Step #7: "Viewing Full Profile"
- User clicks "View Profile" from the preview bottom sheet
- Full profile page loads with comprehensive information
- Bio, subjects/children, curriculum, map snippet
- WhatsApp icon (if enabled) for direct contact

Tests Cover:
- Complete parent profile data
- Complete tutor profile data
- Minimal profile data (optional fields)
- WhatsApp privacy (only shown if enabled)
- Distance calculation
- Location data (lat/lng shown in full profile)
- Profile picture included
- Cannot view own profile (use /auth/me instead)
- Not found scenarios
- Not onboarded users
- Inactive users
- Authentication required
- Integration with frontend
- Data integrity
- Response structure validation
"""
import pytest
import uuid
import json
import time
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Parent, Tutor, create_point_from_lat_lng
from app.core.security import create_access_token

# Use a test database
TEST_DATABASE_URL = "postgresql://homeschool_user:homeschool_pass@localhost:5432/homeschool_test"

# Create test engine
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# FIXTURES

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    
    # Enable PostGIS
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def current_user(test_db):
    """Create the authenticated user (who will be viewing profiles)"""
    user = User(
        id=uuid.uuid4(),
        google_id="current_user_google_id",
        email="current@test.com",
        name="Current User",
        picture="https://lh3.googleusercontent.com/current-user-pic",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Set location for distance calculations (Nairobi CBD)
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(current_user):
    """Generate JWT token for current user"""
    token_data = {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role
    }
    return create_access_token(data=token_data)


@pytest.fixture
def complete_parent(test_db):
    """
    Create a parent with COMPLETE profile data
    This tests that ALL fields are returned correctly in full profile view
    """
    user = User(
        id=uuid.uuid4(),
        google_id="complete_parent_google_id",
        email="complete.parent@test.com",
        name="Sarah Elizabeth Johnson",
        picture="https://lh3.googleusercontent.com/parent-pic-123",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~2km from current user (Westlands area)
    point_wkt = create_point_from_lat_lng(-1.268000, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 7500
    
    test_db.add(user)
    test_db.commit()
    
    # Create parent profile with ALL fields populated
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        children_ages=json.dumps(["3", "5", "7", "10"]),  # 4 children
        curriculum="Classical",
        religion="Christian",
        whatsapp_number="+254712345678",
        whatsapp_enabled=True,
        in_coop=True,
        coop_name="Nairobi Classical Homeschool Coop"
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def parent_whatsapp_disabled(test_db):
    """Parent who has WhatsApp number but disabled sharing"""
    user = User(
        id=uuid.uuid4(),
        google_id="parent_whatsapp_disabled_google_id",
        email="private.parent@test.com",
        name="Private Parent",
        picture="https://lh3.googleusercontent.com/private-pic",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.275000, 36.820000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    
    # Has WhatsApp BUT disabled sharing
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        children_ages=json.dumps(["6", "8"]),
        curriculum="Montessori",
        whatsapp_number="+254722222222",  # Should NOT appear in response
        whatsapp_enabled=False,  # DISABLED
        in_coop=False
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def minimal_parent(test_db):
    """Parent with minimal profile data (only required fields)"""
    user = User(
        id=uuid.uuid4(),
        google_id="minimal_parent_google_id",
        email="minimal.parent@test.com",
        name="Jane Doe",
        picture=None,  # No picture
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.290000, 36.825000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    
    # Minimal parent profile
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        # No children_ages
        # No curriculum
        # No religion
        # No whatsapp
        whatsapp_enabled=False,
        in_coop=False
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def complete_tutor(test_db):
    """
    Create a tutor with COMPLETE profile data
    """
    user = User(
        id=uuid.uuid4(),
        google_id="complete_tutor_google_id",
        email="complete.tutor@test.com",
        name="Dr. John Michael Smith",
        picture="https://lh3.googleusercontent.com/tutor-pic-456",
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~3km from current user (Karen area)
    point_wkt = create_point_from_lat_lng(-1.286389, 36.845000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 15000
    
    test_db.add(user)
    test_db.commit()
    
    # Create tutor profile with ALL fields
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        subjects=json.dumps(["Mathematics", "Physics", "Chemistry", "Computer Science"]),
        curriculum="British",
        certifications=json.dumps(["Ph.D. Mathematics", "B.Ed", "TEFL", "CIE Examiner"]),
        availability="Weekdays 2pm-6pm, Saturdays 9am-1pm",
        whatsapp_number="+254712345679",
        whatsapp_enabled=True,
        verification_status="verified",
        verified_at=datetime.utcnow()
    )
    test_db.add(tutor)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def tutor_whatsapp_disabled(test_db):
    """Tutor who has WhatsApp but disabled sharing"""
    user = User(
        id=uuid.uuid4(),
        google_id="tutor_whatsapp_disabled_google_id",
        email="private.tutor@test.com",
        name="Private Tutor",
        picture="https://lh3.googleusercontent.com/tutor-private",
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.280000, 36.810000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 10000
    
    test_db.add(user)
    test_db.commit()
    
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        subjects=json.dumps(["English", "Literature"]),
        curriculum="American",
        whatsapp_number="+254733333333",  # Should NOT appear
        whatsapp_enabled=False,  # DISABLED
        verification_status="verified"
    )
    test_db.add(tutor)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def minimal_tutor(test_db):
    """Tutor with minimal profile data"""
    user = User(
        id=uuid.uuid4(),
        google_id="minimal_tutor_google_id",
        email="minimal.tutor@test.com",
        name="Bob Teacher",
        picture=None,
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.280000, 36.810000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        whatsapp_enabled=False,
        verification_status="verified"
    )
    test_db.add(tutor)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def not_onboarded_user(test_db):
    """User who hasn't completed onboarding"""
    user = User(
        id=uuid.uuid4(),
        google_id="not_onboarded_google_id",
        email="notonboarded@test.com",
        name="Not Onboarded",
        role="parent",
        onboarded=False,  # NOT onboarded
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def inactive_user(test_db):
    """Inactive user (soft deleted)"""
    user = User(
        id=uuid.uuid4(),
        google_id="inactive_google_id",
        email="inactive@test.com",
        name="Inactive User",
        role="parent",
        onboarded=True,
        is_active=False  # INACTIVE
    )
    
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Classical",
        whatsapp_enabled=False
    )
    test_db.add(parent)
    test_db.commit()
    
    return user


# TEST CLASSES

class TestParentFullProfile:
    """Test complete parent profile data and structure"""
    
    def test_complete_parent_profile_structure(
        self, client, auth_token, complete_parent, test_db
    ):
        """Test full parent profile returns all expected fields"""
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "type" in data
        assert "profile" in data
        assert data["type"] == "parent"
        
        profile = data["profile"]
        
        # User data
        assert profile["id"] == str(complete_parent.id)
        assert profile["name"] == "Sarah Elizabeth Johnson"
        assert profile["picture"] == "https://lh3.googleusercontent.com/parent-pic-123"
        
        # Location data (FULL profile shows exact coordinates)
        assert "latitude" in profile
        assert "longitude" in profile
        assert isinstance(profile["latitude"], float)
        assert isinstance(profile["longitude"], float)
        assert -90 <= profile["latitude"] <= 90
        assert -180 <= profile["longitude"] <= 180
        
        # Visibility radius
        assert profile["visibility_radius_meters"] == 7500
        
        # Distance from current user
        assert "distance_meters" in profile
        assert profile["distance_meters"] is not None
        assert profile["distance_meters"] > 0
        
        # Parent-specific data
        assert profile["children_ages"] == ["3", "5", "7", "10"]
        assert profile["curriculum"] == "Classical"
        assert profile["religion"] == "Christian"
        assert profile["in_coop"] is True
        assert profile["coop_name"] == "Nairobi Classical Homeschool Coop"
        
        # Contact info (WhatsApp shown because enabled)
        assert profile["whatsapp_enabled"] is True
        assert profile["whatsapp_number"] == "+254712345678"
        
        # Metadata
        assert "created_at" in profile
        
        print("\n✓ Complete parent profile structure validated")
    
    def test_parent_whatsapp_privacy_disabled(
        self, client, auth_token, parent_whatsapp_disabled
    ):
        """CRITICAL: WhatsApp number NOT shown when whatsapp_enabled=false"""
        response = client.get(
            f"/profiles/{parent_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        profile = data["profile"]
        
        # WhatsApp disabled
        assert profile["whatsapp_enabled"] is False
        
        # Number should be None/null (NOT exposed)
        assert profile["whatsapp_number"] is None
        
        # Verify number is not leaked anywhere
        response_str = json.dumps(data)
        assert "+254722222222" not in response_str
        assert "254722222222" not in response_str
        
        print("\n✓ WhatsApp privacy validated (disabled)")
    
    def test_minimal_parent_profile(self, client, auth_token, minimal_parent):
        """Test parent with minimal data still returns valid profile"""
        response = client.get(
            f"/profiles/{minimal_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        profile = data["profile"]
        
        # Required fields present
        assert profile["id"] == str(minimal_parent.id)
        assert profile["name"] == "Jane Doe"
        assert "latitude" in profile
        assert "longitude" in profile
        
        # Optional fields should be None
        assert profile["picture"] is None
        assert profile["children_ages"] is None
        assert profile["curriculum"] is None
        assert profile["religion"] is None
        assert profile["in_coop"] is False
        assert profile["coop_name"] is None
        assert profile["whatsapp_enabled"] is False
        assert profile["whatsapp_number"] is None
        
        print("\n✓ Minimal parent profile validated")


class TestTutorFullProfile:
    """Test complete tutor profile data and structure"""
    
    def test_complete_tutor_profile_structure(
        self, client, auth_token, complete_tutor, test_db
    ):
        """Test full tutor profile returns all expected fields"""
        response = client.get(
            f"/profiles/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["type"] == "tutor"
        profile = data["profile"]
        
        # User data
        assert profile["id"] == str(complete_tutor.id)
        assert profile["name"] == "Dr. John Michael Smith"
        assert profile["picture"] == "https://lh3.googleusercontent.com/tutor-pic-456"
        
        # Location data
        assert "latitude" in profile
        assert "longitude" in profile
        assert isinstance(profile["latitude"], float)
        assert isinstance(profile["longitude"], float)
        
        # Visibility radius
        assert profile["visibility_radius_meters"] == 15000
        
        # Distance calculation
        assert "distance_meters" in profile
        assert profile["distance_meters"] is not None
        
        # Tutor-specific data
        assert profile["subjects"] == ["Mathematics", "Physics", "Chemistry", "Computer Science"]
        assert profile["curriculum"] == "British"
        assert profile["certifications"] == ["Ph.D. Mathematics", "B.Ed", "TEFL", "CIE Examiner"]
        assert profile["availability"] == "Weekdays 2pm-6pm, Saturdays 9am-1pm"
        
        # Verification status
        assert profile["verification_status"] == "verified"
        assert "verified_at" in profile
        assert profile["verified_at"] is not None
        
        # Contact info
        assert profile["whatsapp_enabled"] is True
        assert profile["whatsapp_number"] == "+254712345679"
        
        # Metadata
        assert "created_at" in profile
        
        print("\n✓ Complete tutor profile structure validated")
    
    def test_tutor_whatsapp_privacy_disabled(
        self, client, auth_token, tutor_whatsapp_disabled
    ):
        """CRITICAL: Tutor WhatsApp number NOT shown when disabled"""
        response = client.get(
            f"/profiles/{tutor_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        profile = data["profile"]
        
        # WhatsApp disabled
        assert profile["whatsapp_enabled"] is False
        assert profile["whatsapp_number"] is None
        
        # Verify not leaked
        response_str = json.dumps(data)
        assert "+254733333333" not in response_str
        
        print("\n✓ Tutor WhatsApp privacy validated (disabled)")
    
    def test_minimal_tutor_profile(self, client, auth_token, minimal_tutor):
        """Test tutor with minimal data still returns valid profile"""
        response = client.get(
            f"/profiles/{minimal_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        profile = data["profile"]
        
        # Required fields
        assert profile["id"] == str(minimal_tutor.id)
        assert profile["name"] == "Bob Teacher"
        assert "latitude" in profile
        assert "longitude" in profile
        
        # Optional fields None
        assert profile["picture"] is None
        assert profile["subjects"] is None
        assert profile["curriculum"] is None
        assert profile["certifications"] is None
        assert profile["availability"] is None
        assert profile["whatsapp_enabled"] is False
        assert profile["whatsapp_number"] is None
        
        print("\n✓ Minimal tutor profile validated")


class TestProfilePrivacyAndSecurity:
    """Test privacy and security requirements"""
    
    def test_no_sensitive_data_exposed(self, client, auth_token, complete_parent):
        """Ensure no sensitive data is in response"""
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        profile = data["profile"]
        
        # These should NEVER be in the response
        assert "google_id" not in profile
        assert "email" not in profile
        assert "is_active" not in profile
        
        # Verify not leaked anywhere
        response_str = json.dumps(data)
        assert "complete_parent_google_id" not in response_str
        assert "complete.parent@test.com" not in response_str
        
        print("\n✓ No sensitive data exposed")
    
    def test_cannot_view_own_profile(self, client, current_user, auth_token, test_db):
        """CRITICAL: User cannot view their own profile (should use /auth/me)"""
        # Create parent profile for current user
        parent = Parent(
            id=uuid.uuid4(),
            user_id=current_user.id,
            children_ages=json.dumps(["5", "7"]),
            curriculum="Classical",
            whatsapp_enabled=False
        )
        test_db.add(parent)
        test_db.commit()
        
        # Try to view own profile
        response = client.get(
            f"/profiles/{current_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 400 error
        assert response.status_code == 400
        assert "own profile" in response.json()["detail"].lower()
        
        print("\n✓ Cannot view own profile (as expected)")
    
    def test_whatsapp_only_shown_when_enabled(
        self, client, auth_token, complete_parent, parent_whatsapp_disabled
    ):
        """WhatsApp number visibility controlled by whatsapp_enabled flag"""
        # Profile with WhatsApp enabled
        response1 = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data1 = response1.json()["profile"]
        
        assert data1["whatsapp_enabled"] is True
        assert data1["whatsapp_number"] == "+254712345678"
        
        # Profile with WhatsApp disabled
        response2 = client.get(
            f"/profiles/{parent_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data2 = response2.json()["profile"]
        
        assert data2["whatsapp_enabled"] is False
        assert data2["whatsapp_number"] is None
        
        print("\n✓ WhatsApp privacy working correctly")


class TestProfileErrorCases:
    """Test error handling and edge cases"""
    
    def test_profile_not_found(self, client, auth_token):
        """Test viewing non-existent user returns 404"""
        fake_id = uuid.uuid4()
        
        response = client.get(
            f"/profiles/{fake_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_profile_not_onboarded_user(self, client, auth_token, not_onboarded_user):
        """Users who haven't onboarded should not be viewable"""
        response = client.get(
            f"/profiles/{not_onboarded_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_profile_inactive_user(self, client, auth_token, inactive_user):
        """Inactive users should not be viewable"""
        response = client.get(
            f"/profiles/{inactive_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_profile_requires_authentication(self, client, complete_parent):
        """Profile endpoint requires valid JWT"""
        response = client.get(f"/profiles/{complete_parent.id}")
        
        assert response.status_code == 401
    
    def test_profile_invalid_token(self, client, complete_parent):
        """Invalid JWT is rejected"""
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_profile_invalid_uuid(self, client, auth_token):
        """Invalid UUID format handled gracefully"""
        response = client.get(
            "/profiles/not-a-valid-uuid",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code in [404, 422]


class TestProfileDistanceCalculation:
    """Test distance calculation in profiles"""
    
    def test_distance_calculated_accurately(
        self, client, auth_token, complete_parent, current_user, test_db
    ):
        """Distance should be calculated between users"""
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        profile = response.json()["profile"]
        
        assert "distance_meters" in profile
        assert profile["distance_meters"] is not None
        assert isinstance(profile["distance_meters"], (int, float))
        assert profile["distance_meters"] > 0
        
        # Should be roughly 2km based on fixture locations
        assert 1500 < profile["distance_meters"] < 2500
        
        print(f"\n✓ Distance: {profile['distance_meters']:.0f} meters (~2km)")
    
    def test_distance_null_when_viewer_no_location(
        self, client, test_db, complete_parent
    ):
        """Distance is None if viewing user has no location"""
        # Create user without location
        user_no_loc = User(
            id=uuid.uuid4(),
            google_id="no_loc_viewer",
            email="noloc@test.com",
            name="No Location Viewer",
            role="parent",
            onboarded=True,
            is_active=True
            # No location set
        )
        test_db.add(user_no_loc)
        test_db.commit()
        
        token_data = {
            "user_id": str(user_no_loc.id),
            "email": user_no_loc.email,
            "role": user_no_loc.role
        }
        token = create_access_token(data=token_data)
        
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        profile = response.json()["profile"]
        
        assert profile["distance_meters"] is None


class TestProfileLocationData:
    """Test that full profile includes location coordinates"""
    
    def test_location_coordinates_included(
        self, client, auth_token, complete_parent
    ):
        """Full profile includes exact lat/lng (user already consented by being on map)"""
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        profile = response.json()["profile"]
        
        # Lat/lng should be present
        assert "latitude" in profile
        assert "longitude" in profile
        
        # Validate coordinates are reasonable (Nairobi area)
        assert -2.0 < profile["latitude"] < -1.0
        assert 36.5 < profile["longitude"] < 37.0
        
        # Should match fixture data (~-1.268, 36.817)
        assert abs(profile["latitude"] - (-1.268000)) < 0.001
        assert abs(profile["longitude"] - 36.817223) < 0.001
        
        print(f"\n✓ Location: ({profile['latitude']:.6f}, {profile['longitude']:.6f})")


class TestProfileIntegrationScenarios:
    """Integration tests simulating real user flows"""
    
    def test_complete_user_journey_preview_to_full_profile(
        self, client, auth_token, complete_parent
    ):
        """
        INTEGRATION TEST: User journey from preview to full profile
        
        Step 6: User clicks pin → sees preview
        Step 7: User clicks "View Profile" → sees full profile
        """
        # Step 6: Get preview first
        preview_response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert preview_response.status_code == 200
        preview = preview_response.json()
        
        # Preview has basic info
        assert "name" in preview
        assert "curriculum" in preview
        
        # Step 7: User clicks "View Profile" button
        profile_response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert profile_response.status_code == 200
        full_profile = profile_response.json()["profile"]
        
        # Full profile has MORE data than preview
        assert "latitude" in full_profile  # Not in preview
        assert "longitude" in full_profile  # Not in preview
        assert "picture" in full_profile  # Not in preview
        assert "religion" in full_profile  # Not in preview (parent-specific)
        assert "created_at" in full_profile  # Not in preview
        
        # Data consistency - same user
        assert preview["id"] == full_profile["id"]
        assert preview["name"] == full_profile["name"]
        assert preview["curriculum"] == full_profile["curriculum"]
        
        print("\n✓ Preview → Full Profile journey validated")
    
    def test_full_profile_before_whatsapp_contact(
        self, client, auth_token, complete_parent
    ):
        """
        Full profile is viewed before WhatsApp contact (Issue #11)
        This test verifies the data needed for contact flow
        """
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        profile = response.json()["profile"]
        
        # Check WhatsApp contact availability
        if profile["whatsapp_enabled"]:
            # Frontend would show "Contact on WhatsApp" button
            # Next step: GET /contact/whatsapp/{user_id} (Issue #11)
            assert profile["whatsapp_number"] is not None
            assert profile["whatsapp_number"].startswith("+254")
            
            print(f"\n✓ WhatsApp contact available: {profile['whatsapp_number']}")
        else:
            # No WhatsApp contact option
            assert profile["whatsapp_number"] is None
            
            print("\n✓ WhatsApp contact not available")


class TestProfileDataIntegrity:
    """Test data consistency and integrity"""
    
    def test_profile_matches_database(
        self, client, auth_token, complete_parent, test_db
    ):
        """Verify profile data matches database"""
        # Get from API
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        profile = response.json()["profile"]
        
        # Get from DB
        user = test_db.query(User).filter(User.id == complete_parent.id).first()
        parent = test_db.query(Parent).filter(Parent.user_id == complete_parent.id).first()
        
        # Verify match
        assert profile["name"] == user.name
        assert profile["picture"] == user.picture
        assert profile["curriculum"] == parent.curriculum
        assert profile["religion"] == parent.religion
        assert profile["in_coop"] == parent.in_coop
        assert profile["coop_name"] == parent.coop_name
        assert profile["whatsapp_enabled"] == parent.whatsapp_enabled
        
        if parent.whatsapp_enabled:
            assert profile["whatsapp_number"] == parent.whatsapp_number
        
        # Verify JSON parsing
        db_children = json.loads(parent.children_ages)
        assert profile["children_ages"] == db_children
        
        print("\n✓ Profile data matches database")
    
    def test_tutor_json_fields_parsed_correctly(
        self, client, auth_token, complete_tutor, test_db
    ):
        """Test JSON arrays are parsed correctly for tutors"""
        response = client.get(
            f"/profiles/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        profile = response.json()["profile"]
        
        # Get from DB
        tutor = test_db.query(Tutor).filter(Tutor.user_id == complete_tutor.id).first()
        
        # Verify JSON parsing
        db_subjects = json.loads(tutor.subjects)
        db_certs = json.loads(tutor.certifications)
        
        assert profile["subjects"] == db_subjects
        assert profile["certifications"] == db_certs
        assert isinstance(profile["subjects"], list)
        assert isinstance(profile["certifications"], list)
        
        print("\n✓ Tutor JSON fields parsed correctly")


class TestProfilePerformance:
    """Test performance characteristics"""
    
    def test_profile_response_time(self, client, auth_token, complete_parent):
        """Profile should load quickly (target: <200ms)"""
        start_time = time.time()
        
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        
        # Should be reasonably fast
        assert response_time_ms < 300, f"Profile took {response_time_ms}ms (target: <300ms)"
        
        print(f"\n✓ Profile response time: {response_time_ms:.2f}ms")


class TestProfileResponseStructure:
    """Test response structure for frontend integration"""
    
    def test_parent_response_structure_for_frontend(
        self, client, auth_token, complete_parent
    ):
        """
        Test response structure matches frontend expectations
        Frontend needs: type + profile object
        """
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Top-level structure
        assert "type" in data
        assert "profile" in data
        assert data["type"] == "parent"
        assert isinstance(data["profile"], dict)
        
        # Frontend can do: if (data.type === 'parent') { ... }
        profile = data["profile"]
        
        # All required fields for frontend rendering
        required_fields = [
            "id", "name", "latitude", "longitude",
            "visibility_radius_meters", "whatsapp_enabled", "created_at"
        ]
        
        for field in required_fields:
            assert field in profile, f"Missing required field: {field}"
        
        print("\n✓ Response structure valid for frontend")
    
    def test_tutor_response_structure_for_frontend(
        self, client, auth_token, complete_tutor
    ):
        """Test tutor response structure for frontend"""
        response = client.get(
            f"/profiles/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["type"] == "tutor"
        profile = data["profile"]
        
        # Tutor-specific fields
        tutor_fields = [
            "subjects", "curriculum", "certifications",
            "availability", "verification_status"
        ]
        
        for field in tutor_fields:
            assert field in profile, f"Missing tutor field: {field}"
        
        print("\n✓ Tutor response structure valid")


class TestFrontendIntegration:
    """Tests simulating frontend usage patterns"""
    
    def test_frontend_can_determine_contact_method(
        self, client, auth_token, complete_parent, parent_whatsapp_disabled
    ):
        """
        Frontend needs to determine if user can be contacted via WhatsApp
        Based on whatsapp_enabled flag
        """
        # User with WhatsApp enabled
        response1 = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        profile1 = response1.json()["profile"]
        
        # Frontend logic:
        if profile1["whatsapp_enabled"]:
            # Show WhatsApp button with profile1["whatsapp_number"]
            assert profile1["whatsapp_number"] is not None
            contact_available = True
        else:
            contact_available = False
        
        assert contact_available is True
        
        # User with WhatsApp disabled
        response2 = client.get(
            f"/profiles/{parent_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        profile2 = response2.json()["profile"]
        
        if profile2["whatsapp_enabled"]:
            contact_available = True
        else:
            # Don't show WhatsApp button
            assert profile2["whatsapp_number"] is None
            contact_available = False
        
        assert contact_available is False
        
        print("\n✓ Frontend can determine contact availability")
    
    def test_frontend_can_display_location_on_map(
        self, client, auth_token, complete_parent
    ):
        """
        Frontend can display user's location on a map snippet
        Using latitude and longitude from full profile
        """
        response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        profile = response.json()["profile"]
        
        # Frontend can create map marker:
        # new google.maps.Marker({
        #   position: { lat: profile.latitude, lng: profile.longitude },
        #   ...
        # })
        
        assert "latitude" in profile
        assert "longitude" in profile
        
        # Valid coordinates
        assert isinstance(profile["latitude"], (int, float))
        assert isinstance(profile["longitude"], (int, float))
        
        print(f"\n✓ Frontend can display map at: ({profile['latitude']}, {profile['longitude']})")
    
    def test_frontend_role_specific_rendering(
        self, client, auth_token, complete_parent, complete_tutor
    ):
        """
        Frontend renders different UI based on type (parent vs tutor)
        """
        # Get parent profile
        parent_response = client.get(
            f"/profiles/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        parent_data = parent_response.json()
        
        # Get tutor profile
        tutor_response = client.get(
            f"/profiles/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        tutor_data = tutor_response.json()
        
        # Frontend logic:
        if parent_data["type"] == "parent":
            # Show children, curriculum, coop info
            profile = parent_data["profile"]
            assert "children_ages" in profile
            assert "in_coop" in profile
            print("\n✓ Frontend renders parent UI")
        
        if tutor_data["type"] == "tutor":
            # Show subjects, certifications, availability
            profile = tutor_data["profile"]
            assert "subjects" in profile
            assert "certifications" in profile
            assert "availability" in profile
            print("\n✓ Frontend renders tutor UI")


# RUN TESTS

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
