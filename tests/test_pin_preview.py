"""
Test suite for Issue 9: Map Pin Preview Endpoint

Endpoint: GET /map/preview/{user_id}

Acceptance Criteria:
✓ Minimal payload - returns only essential preview data
✓ No sensitive data - WhatsApp numbers hidden, only public info
✓ Fast response - simple query, no complex joins

User Journey Step:
This is Step #6: "Clicking a Pin (Preview)"
- User taps a pin on the map
- Bottom sheet shows: name, type, curriculum, distance, basic info
- "View Profile" button to see full details

Tests Cover:
- Parent preview data
- Tutor preview data
- Distance calculation
- Privacy (no sensitive data)
- Not found scenarios
- Not onboarded users
- Inactive users
- Authentication required
- Performance (response time)
- Self-preview (optional blocking)
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


# ============================================================================
# FIXTURES
# ============================================================================

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
    """Create the authenticated user (who will be viewing previews)"""
    user = User(
        id=uuid.uuid4(),
        google_id="current_user_google_id",
        email="current@test.com",
        name="Current User",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Set location for distance calculations
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)  # Nairobi
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
    This tests that all fields are returned correctly
    """
    user = User(
        id=uuid.uuid4(),
        google_id="complete_parent_google_id",
        email="complete.parent@test.com",
        name="Sarah Elizabeth Johnson",  # Full name with middle name
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~2km from current user
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
        whatsapp_number="+254712345678",  # Should NOT appear in preview
        whatsapp_enabled=True,
        in_coop=True,
        coop_name="Nairobi Classical Homeschool Coop"
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def minimal_parent(test_db):
    """
    Create a parent with MINIMAL profile data
    Tests that preview works with missing optional fields
    """
    user = User(
        id=uuid.uuid4(),
        google_id="minimal_parent_google_id",
        email="minimal.parent@test.com",
        name="Jane",  # Single name
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.290000, 36.820000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    # Parent profile with minimal data (only required fields)
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        # No children_ages
        # No curriculum
        # No religion
        # No whatsapp
        whatsapp_enabled=False,
        in_coop=False
        # No coop_name
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
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~3km from current user
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
        whatsapp_number="+254712345679",  # Should NOT appear in preview
        whatsapp_enabled=True,
        verification_status="verified",
        verified_at=datetime.utcnow()
    )
    test_db.add(tutor)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def minimal_tutor(test_db):
    """
    Create a tutor with MINIMAL profile data
    """
    user = User(
        id=uuid.uuid4(),
        google_id="minimal_tutor_google_id",
        email="minimal.tutor@test.com",
        name="Bob",
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.280000, 36.810000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    # Tutor profile with minimal data
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        # No subjects
        # No curriculum
        # No certifications
        # No availability
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
        name="Not Onboarded User",
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
    
    # Create parent profile
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Classical"
    )
    test_db.add(parent)
    test_db.commit()
    
    return user


@pytest.fixture
def user_without_location(test_db):
    """User who is onboarded but has no location (edge case)"""
    user = User(
        id=uuid.uuid4(),
        google_id="no_location_google_id",
        email="nolocation@test.com",
        name="No Location User",
        role="parent",
        onboarded=True,
        is_active=True
        # No location set
    )
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Classical"
    )
    test_db.add(parent)
    test_db.commit()
    
    return user


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestParentPreview:
    """Test parent preview data structure and content"""
    
    def test_complete_parent_preview(self, client, auth_token, complete_parent, test_db):
        """Test preview for parent with all fields populated"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        assert data["id"] == str(complete_parent.id)
        assert data["type"] == "parent"
        assert data["name"] == "Sarah Elizabeth Johnson"  # FULL name (not just first)
        assert data["curriculum"] == "Classical"
        
        # Parent-specific fields
        assert data["children_ages"] == ["3", "5", "7", "10"]
        assert data["in_coop"] is True
        assert data["coop_name"] == "Nairobi Classical Homeschool Coop"
        
        # Contact info
        assert data["whatsapp_enabled"] is True
        assert "whatsapp_number" not in data  # PRIVACY: number NOT exposed
        
        # Distance calculated
        assert "distance_meters" in data
        assert data["distance_meters"] is not None
        assert data["distance_meters"] > 0
        
        # Tutor-specific fields should NOT be present
        assert "subjects" not in data or data["subjects"] is None
        assert "availability" not in data or data["availability"] is None
    
    def test_minimal_parent_preview(self, client, auth_token, minimal_parent):
        """Test preview for parent with minimal data"""
        response = client.get(
            f"/map/preview/{minimal_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic fields still present
        assert data["id"] == str(minimal_parent.id)
        assert data["type"] == "parent"
        assert data["name"] == "Jane"
        
        # Optional fields should be None or absent
        assert data["curriculum"] is None or "curriculum" not in data
        assert data["children_ages"] is None or "children_ages" not in data
        assert data["in_coop"] is False
        assert data["coop_name"] is None or "coop_name" not in data
        assert data["whatsapp_enabled"] is False


class TestTutorPreview:
    """Test tutor preview data structure and content"""
    
    def test_complete_tutor_preview(self, client, auth_token, complete_tutor):
        """Test preview for tutor with all fields populated"""
        response = client.get(
            f"/map/preview/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert data["id"] == str(complete_tutor.id)
        assert data["type"] == "tutor"
        assert data["name"] == "Dr. John Michael Smith"  # FULL name
        assert data["curriculum"] == "British"
        
        # Tutor-specific fields
        assert data["subjects"] == ["Mathematics", "Physics", "Chemistry", "Computer Science"]
        assert data["availability"] == "Weekdays 2pm-6pm, Saturdays 9am-1pm"
        
        # Contact info
        assert data["whatsapp_enabled"] is True
        assert "whatsapp_number" not in data  # PRIVACY: number NOT exposed
        
        # Distance calculated
        assert "distance_meters" in data
        assert data["distance_meters"] is not None
        
        # Parent-specific fields should NOT be present
        assert "children_ages" not in data or data["children_ages"] is None
        assert "in_coop" not in data or data["in_coop"] is None
        assert "coop_name" not in data or data["coop_name"] is None
    
    def test_minimal_tutor_preview(self, client, auth_token, minimal_tutor):
        """Test preview for tutor with minimal data"""
        response = client.get(
            f"/map/preview/{minimal_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic fields present
        assert data["id"] == str(minimal_tutor.id)
        assert data["type"] == "tutor"
        assert data["name"] == "Bob"
        
        # Optional fields should be None or absent
        assert data["subjects"] is None or "subjects" not in data
        assert data["curriculum"] is None or "curriculum" not in data
        assert data["availability"] is None or "availability" not in data
        assert data["whatsapp_enabled"] is False


class TestPreviewPrivacy:
    """Test privacy and security in preview responses"""
    
    def test_no_whatsapp_number_exposed(self, client, auth_token, complete_parent):
        """CRITICAL: WhatsApp number should NEVER be in preview"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # WhatsApp number must NOT be in response
        assert "whatsapp_number" not in data
        
        # Convert to string and check it's not leaked anywhere
        response_str = json.dumps(data)
        assert "+254712345678" not in response_str
        assert "254712345678" not in response_str
    
    def test_full_name_shown_in_preview(self, client, auth_token, complete_parent):
        """
        Preview shows FULL name (unlike pins which show first name only)
        This is intentional - user clicked to see more details
        """
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Full name should be present
        assert data["name"] == "Sarah Elizabeth Johnson"
        assert "Sarah" in data["name"]
        assert "Johnson" in data["name"]
    
    def test_no_google_id_exposed(self, client, auth_token, complete_parent):
        """Google ID should never be exposed"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "google_id" not in data
    
    def test_no_email_exposed(self, client, auth_token, complete_parent):
        """Email should not be in preview (privacy)"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "email" not in data
        
        # Make sure email isn't leaked anywhere
        response_str = json.dumps(data)
        assert "complete.parent@test.com" not in response_str


class TestPreviewDistanceCalculation:
    """Test distance calculation in previews"""
    
    def test_distance_calculated_when_both_have_location(
        self, client, auth_token, current_user, complete_parent
    ):
        """Distance should be calculated when both users have locations"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "distance_meters" in data
        assert data["distance_meters"] is not None
        assert isinstance(data["distance_meters"], (int, float))
        assert data["distance_meters"] > 0
        
        # Should be roughly 2km based on fixture locations
        assert 1500 < data["distance_meters"] < 2500
    
    def test_distance_null_when_current_user_no_location(
        self, client, test_db, complete_parent
    ):
        """
        Distance should be None if current user has no location
        (Edge case - shouldn't happen in prod since onboarding requires location)
        """
        # Create user without location
        user_no_loc = User(
            id=uuid.uuid4(),
            google_id="no_loc_viewer",
            email="noloc@test.com",
            name="No Location",
            role="parent",
            onboarded=True,  # Somehow onboarded without location (edge case)
            is_active=True
            # No location set
        )
        test_db.add(user_no_loc)
        test_db.commit()
        
        # Create token for this user
        token_data = {
            "user_id": str(user_no_loc.id),
            "email": user_no_loc.email,
            "role": user_no_loc.role
        }
        token = create_access_token(data=token_data)
        
        # Try to get preview
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Distance should be None or not calculated
        assert data["distance_meters"] is None


class TestPreviewErrorCases:
    """Test error handling and edge cases"""
    
    def test_preview_not_found(self, client, auth_token):
        """Test preview for non-existent user returns 404"""
        fake_id = uuid.uuid4()
        
        response = client.get(
            f"/map/preview/{fake_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_preview_not_onboarded_user(self, client, auth_token, not_onboarded_user):
        """Test preview fails for users who haven't onboarded"""
        response = client.get(
            f"/map/preview/{not_onboarded_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        # Should not reveal that user exists but isn't onboarded
    
    def test_preview_inactive_user(self, client, auth_token, inactive_user):
        """Test preview fails for inactive users"""
        response = client.get(
            f"/map/preview/{inactive_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_preview_requires_authentication(self, client, complete_parent):
        """Test that preview requires valid JWT"""
        response = client.get(f"/map/preview/{complete_parent.id}")
        
        assert response.status_code == 401
    
    def test_preview_invalid_token(self, client, complete_parent):
        """Test that invalid JWT is rejected"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
    
    def test_preview_invalid_uuid(self, client, auth_token):
        """Test preview with invalid UUID format"""
        response = client.get(
            "/map/preview/not-a-valid-uuid",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 422 (validation error) or 404
        assert response.status_code in [404, 422]


class TestPreviewSelfViewing:
    """Test viewing own profile preview (optional feature)"""
    
    def test_can_view_own_preview(self, client, auth_token, current_user, test_db):
        """
        Test that user CAN view their own preview
        (This is currently ALLOWED in your implementation)
        
        If you want to BLOCK this, you'd need to add a check in the endpoint
        """
        # Create parent profile for current user
        parent = Parent(
            id=uuid.uuid4(),
            user_id=current_user.id,
            children_ages=json.dumps(["5"]),
            curriculum="Classical",
            whatsapp_enabled=True,
            in_coop=False
        )
        test_db.add(parent)
        test_db.commit()
        
        # Try to view own preview
        response = client.get(
            f"/map/preview/{current_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Currently this SUCCEEDS (returns 200)
        # If you want to block it, you'd expect 400
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(current_user.id)
        
        # NOTE: If you want to prevent self-viewing, add this to the endpoint:
        # if user_id == requesting_user_id:
        #     raise HTTPException(status_code=400, detail="Cannot view own preview")


class TestPreviewPerformance:
    """Test performance characteristics"""
    
    def test_preview_response_time(self, client, auth_token, complete_parent):
        """Test that preview responds quickly (target: <100ms)"""
        start_time = time.time()
        
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        
        # Response should be fast (target: <100ms, allow up to 200ms for test environment)
        assert response_time_ms < 200, f"Preview took {response_time_ms}ms (target: <100ms)"
        
        print(f"\n✓ Preview response time: {response_time_ms:.2f}ms")
    
    def test_preview_minimal_payload_size(self, client, auth_token, complete_parent):
        """Test that preview payload is lightweight"""
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        
        # Check payload size
        payload_size = len(response.content)
        
        # Should be under 2KB (typical preview is ~500 bytes)
        assert payload_size < 2048, f"Payload too large: {payload_size} bytes"
        
        print(f"\n✓ Preview payload size: {payload_size} bytes")


class TestPreviewIntegrationScenarios:
    """Integration tests simulating real user flows"""
    
    def test_user_journey_map_to_preview(
        self, client, auth_token, complete_parent
    ):
        """
        INTEGRATION TEST: Full user journey from map to preview
        
        User Journey Step #6:
        1. User sees pin on map (from /map/pins)
        2. User taps pin
        3. Frontend calls /map/preview/{id}
        4. Bottom sheet shows preview data
        5. User decides: "View Full Profile" or contact
        """
        # Step 3: Frontend calls preview
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        preview = response.json()
        
        # Step 4: Frontend displays in bottom sheet
        # Verify all data needed for bottom sheet is present
        assert preview["name"]  # Show name
        assert preview["type"] in ["parent", "tutor"]  # Show badge
        assert preview["curriculum"]  # Show curriculum
        assert preview["distance_meters"]  # Show distance
        
        # Parent-specific info
        if preview["type"] == "parent":
            assert "children_ages" in preview
            assert "in_coop" in preview
        
        # Contact option
        assert "whatsapp_enabled" in preview
        # If whatsapp_enabled, show contact button
        if preview["whatsapp_enabled"]:
            # Frontend would show "Contact on WhatsApp" button
            # (Actual contact happens in Issue #11)
            pass
    
    def test_preview_before_full_profile(
        self, client, auth_token, complete_parent
    ):
        """
        Preview is a lighter query than full profile
        User sees preview first, then decides whether to load full profile
        """
        # Get preview (lightweight)
        preview_response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        
        # Preview should have essential fields
        assert "name" in preview_data
        assert "curriculum" in preview_data
        assert "whatsapp_enabled" in preview_data
        
        # User now decides to view full profile (Issue #10 - not implemented yet)
        # full_profile_response = client.get(
        #     f"/profiles/{complete_parent.id}",
        #     headers={"Authorization": f"Bearer {auth_token}"}
        # )
        # Full profile would have MORE data: bio, detailed info, etc.


class TestPreviewDataIntegrity:
    """Test data consistency and integrity"""
    
    def test_preview_matches_database_data(
        self, client, auth_token, complete_parent, test_db
    ):
        """Verify preview data matches what's in the database"""
        # Get preview from API
        response = client.get(
            f"/map/preview/{complete_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        preview = response.json()
        
        # Get data directly from database
        user = test_db.query(User).filter(User.id == complete_parent.id).first()
        parent = test_db.query(Parent).filter(Parent.user_id == complete_parent.id).first()
        
        # Verify preview matches DB
        assert preview["name"] == user.name
        assert preview["curriculum"] == parent.curriculum
        assert preview["in_coop"] == parent.in_coop
        assert preview["coop_name"] == parent.coop_name
        assert preview["whatsapp_enabled"] == parent.whatsapp_enabled
        
        # Verify children_ages are parsed correctly
        db_children = json.loads(parent.children_ages)
        assert preview["children_ages"] == db_children
    
    def test_preview_json_fields_parsed_correctly(
        self, client, auth_token, complete_tutor, test_db
    ):
        """Test that JSON fields (subjects, children_ages) are parsed correctly"""
        response = client.get(
            f"/map/preview/{complete_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        preview = response.json()
        
        # Get tutor from DB
        tutor = test_db.query(Tutor).filter(Tutor.user_id == complete_tutor.id).first()
        
        # Subjects should be parsed from JSON string to array
        db_subjects = json.loads(tutor.subjects)
        assert preview["subjects"] == db_subjects
        assert isinstance(preview["subjects"], list)
        assert len(preview["subjects"]) > 0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
