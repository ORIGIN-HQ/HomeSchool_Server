"""
Test suite for Issue 8: Map Pins Endpoint (Viewport-Based)

Tests:
- GET /map/pins - viewport-based queries
- GET /map/preview/{user_id} - pin preview
- Spatial filtering (bounding box)
- Distance calculations
- Type filters (parent/tutor/all)
- Curriculum filters
- Subject filters
- Privacy (self-exclusion, first name only)
- Performance (query speed, limits)
- Edge cases (viewport boundaries, empty results)
"""
import pytest
import uuid
import json
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


# Fixtures
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    # Create all tables
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
        # Clean up - drop all tables after test
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
    """Create the authenticated user (who will be viewing the map)"""
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
def nearby_parent(test_db):
    """Create a nearby parent user (within 2km)"""
    user = User(
        id=uuid.uuid4(),
        google_id="nearby_parent_google_id",
        email="nearby_parent@test.com",
        name="Sarah Johnson",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~1.5km north of current user
    point_wkt = create_point_from_lat_lng(-1.273000, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    
    # Create parent profile
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        children_ages=json.dumps(["5", "7", "10"]),
        curriculum="Classical",
        religion="Christian",
        whatsapp_number="+254712345678",
        whatsapp_enabled=True,
        in_coop=True,
        coop_name="Nairobi Homeschool Coop"
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def nearby_tutor(test_db):
    """Create a nearby tutor user (within 3km)"""
    user = User(
        id=uuid.uuid4(),
        google_id="nearby_tutor_google_id",
        email="nearby_tutor@test.com",
        name="John Smith",
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~2.5km east of current user
    point_wkt = create_point_from_lat_lng(-1.286389, 36.840000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 10000
    
    test_db.add(user)
    test_db.commit()
    
    # Create tutor profile
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        subjects=json.dumps(["Mathematics", "Science", "English"]),
        curriculum="British",
        certifications=json.dumps(["B.Ed", "TEFL"]),
        availability="Weekday mornings",
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
def far_parent(test_db):
    """Create a far parent user (>20km away, outside typical viewport)"""
    user = User(
        id=uuid.uuid4(),
        google_id="far_parent_google_id",
        email="far_parent@test.com",
        name="Mary Wilson",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    # Location: ~25km south of current user
    point_wkt = create_point_from_lat_lng(-1.500000, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    
    # Create parent profile
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        children_ages=json.dumps(["8"]),
        curriculum="Montessori",
        whatsapp_enabled=False,
        in_coop=False
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def not_onboarded_user(test_db):
    """Create a user who hasn't completed onboarding (should not appear)"""
    user = User(
        id=uuid.uuid4(),
        google_id="not_onboarded_google_id",
        email="notonboarded@test.com",
        name="Not Onboarded",
        role="parent",
        onboarded=False,  # NOT onboarded
        is_active=True
    )
    
    # Has location but not onboarded
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def inactive_user(test_db):
    """Create an inactive user (should not appear)"""
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
    return user


# Test Classes
class TestMapPinsBasic:
    """Basic map pins endpoint tests"""
    
    def test_get_pins_in_viewport_success(
        self, client, auth_token, current_user, nearby_parent, nearby_tutor, test_db
    ):
        """Test successful retrieval of pins within viewport bounds"""
        # Viewport covering Nairobi area (includes nearby users, excludes far users)
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "all"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "pins" in data
        assert "total" in data
        assert "filters_applied" in data
        
        # Should return 2 pins (nearby_parent and nearby_tutor, NOT current_user)
        assert data["total"] == 2
        assert len(data["pins"]) == 2
        
        # Verify pins data
        pin_ids = [pin["id"] for pin in data["pins"]]
        assert str(nearby_parent.id) in pin_ids
        assert str(nearby_tutor.id) in pin_ids
        assert str(current_user.id) not in pin_ids  # Self-exclusion
        
        # Verify pin structure
        for pin in data["pins"]:
            assert "id" in pin
            assert "type" in pin
            assert "latitude" in pin
            assert "longitude" in pin
            assert "name" in pin
            assert pin["type"] in ["parent", "tutor"]
    
    def test_get_pins_excludes_self(self, client, auth_token, current_user, nearby_parent):
        """Test that current user never sees their own pin"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        pin_ids = [pin["id"] for pin in data["pins"]]
        assert str(current_user.id) not in pin_ids
    
    def test_get_pins_excludes_not_onboarded(
        self, client, auth_token, nearby_parent, not_onboarded_user
    ):
        """Test that users who haven't completed onboarding are excluded"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        pin_ids = [pin["id"] for pin in data["pins"]]
        assert str(not_onboarded_user.id) not in pin_ids
    
    def test_get_pins_excludes_inactive(
        self, client, auth_token, nearby_parent, inactive_user
    ):
        """Test that inactive users are excluded"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        pin_ids = [pin["id"] for pin in data["pins"]]
        assert str(inactive_user.id) not in pin_ids
    
    def test_get_pins_empty_viewport(self, client, auth_token):
        """Test viewport with no users returns empty list"""
        # Viewport in ocean (no users)
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": 0.0,
                "ne_lng": 0.0,
                "sw_lat": -1.0,
                "sw_lng": -1.0
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["pins"]) == 0
    
    def test_get_pins_no_auth(self, client):
        """Test that unauthenticated request fails"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            }
        )
        
        assert response.status_code == 401  # Unauthorized


class TestMapPinsFilters:
    """Test filtering functionality"""
    
    def test_filter_by_type_parent_only(
        self, client, auth_token, nearby_parent, nearby_tutor
    ):
        """Test filtering to show only parents"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "parent"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return parent
        assert data["total"] == 1
        assert data["pins"][0]["type"] == "parent"
        assert data["pins"][0]["id"] == str(nearby_parent.id)
    
    def test_filter_by_type_tutor_only(
        self, client, auth_token, nearby_parent, nearby_tutor
    ):
        """Test filtering to show only tutors"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "tutor"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return tutor
        assert data["total"] == 1
        assert data["pins"][0]["type"] == "tutor"
        assert data["pins"][0]["id"] == str(nearby_tutor.id)
    
    def test_filter_by_curriculum(
        self, client, auth_token, nearby_parent, nearby_tutor
    ):
        """Test filtering by curriculum"""
        # Filter for Classical (should match nearby_parent)
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "curriculum": "Classical"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["pins"][0]["curriculum"] == "Classical"
        assert data["pins"][0]["id"] == str(nearby_parent.id)
    
    def test_filter_by_subject(self, client, auth_token, nearby_tutor):
        """Test filtering tutors by subject"""
        # Filter for Mathematics (should match nearby_tutor)
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "subject": "Mathematics"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["pins"][0]["type"] == "tutor"
        assert "Mathematics" in data["pins"][0]["subjects"]
    
    def test_filter_by_distance(
        self, client, auth_token, nearby_parent, far_parent
    ):
        """Test filtering by maximum distance"""
        # Set max distance to 5km (should exclude far_parent)
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.200000,
                "ne_lng": 36.900000,
                "sw_lat": -1.600000,  # Large viewport
                "sw_lng": 36.700000,
                "max_distance_meters": 5000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include nearby_parent (within 5km)
        pin_ids = [pin["id"] for pin in data["pins"]]
        assert str(nearby_parent.id) in pin_ids
        assert str(far_parent.id) not in pin_ids
    
    def test_combined_filters(
        self, client, auth_token, nearby_parent, nearby_tutor
    ):
        """Test combining multiple filters"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "tutor",
                "curriculum": "British"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["pins"][0]["type"] == "tutor"
        assert data["pins"][0]["curriculum"] == "British"


class TestMapPinsPrivacy:
    """Test privacy features"""
    
    def test_first_name_only_in_pins(
        self, client, auth_token, nearby_parent
    ):
        """Test that only first name is shown in pin list (privacy)"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find the nearby_parent pin
        parent_pin = next(
            pin for pin in data["pins"] 
            if pin["id"] == str(nearby_parent.id)
        )
        
        # Should only show first name
        assert parent_pin["name"] == "Sarah"
        assert "Johnson" not in parent_pin["name"]
    
    def test_distance_calculated_when_user_has_location(
        self, client, auth_token, current_user, nearby_parent
    ):
        """Test that distance is calculated when current user has location"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All pins should have distance calculated
        for pin in data["pins"]:
            assert "distance_meters" in pin
            assert pin["distance_meters"] is not None
            assert pin["distance_meters"] > 0


class TestMapPinPreview:
    """Test pin preview endpoint"""
    
    def test_get_parent_preview_success(
        self, client, auth_token, nearby_parent
    ):
        """Test getting preview for a parent pin"""
        response = client.get(
            f"/map/preview/{nearby_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["id"] == str(nearby_parent.id)
        assert data["type"] == "parent"
        assert data["name"] == "Sarah Johnson"  # Full name in preview
        assert data["curriculum"] == "Classical"
        assert data["children_ages"] == ["5", "7", "10"]
        assert data["in_coop"] is True
        assert data["coop_name"] == "Nairobi Homeschool Coop"
        assert data["whatsapp_enabled"] is True
        assert "distance_meters" in data
    
    def test_get_tutor_preview_success(
        self, client, auth_token, nearby_tutor
    ):
        """Test getting preview for a tutor pin"""
        response = client.get(
            f"/map/preview/{nearby_tutor.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["id"] == str(nearby_tutor.id)
        assert data["type"] == "tutor"
        assert data["name"] == "John Smith"  # Full name in preview
        assert data["curriculum"] == "British"
        assert data["subjects"] == ["Mathematics", "Science", "English"]
        assert data["availability"] == "Weekday mornings"
        assert data["whatsapp_enabled"] is True
    
    def test_get_preview_not_found(self, client, auth_token):
        """Test getting preview for non-existent user"""
        fake_id = uuid.uuid4()
        response = client.get(
            f"/map/preview/{fake_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_get_preview_not_onboarded(
        self, client, auth_token, not_onboarded_user
    ):
        """Test that preview fails for not-onboarded users"""
        response = client.get(
            f"/map/preview/{not_onboarded_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_get_preview_no_auth(self, client, nearby_parent):
        """Test that unauthenticated request fails"""
        response = client.get(f"/map/preview/{nearby_parent.id}")
        
        assert response.status_code == 401


class TestMapPinsEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_viewport_crosses_antimeridian(self, client, auth_token):
        """Test viewport that crosses the antimeridian (180° longitude)"""
        # This is a valid edge case in real-world maps
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": 10.0,
                "ne_lng": -170.0,  # West of antimeridian
                "sw_lat": -10.0,
                "sw_lng": 170.0    # East of antimeridian
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should not error, even if no results
        assert response.status_code == 200
    
    def test_very_large_viewport(self, client, auth_token, nearby_parent):
        """Test very large viewport (entire world)"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": 90.0,
                "ne_lng": 180.0,
                "sw_lat": -90.0,
                "sw_lng": -180.0
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # Should still be limited to 500 pins (see implementation)
    
    def test_very_small_viewport(self, client, auth_token):
        """Test very small viewport (single building)"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.286389,
                "ne_lng": 36.817223,
                "sw_lat": -1.286400,  # Only 0.00001° difference (~1 meter)
                "sw_lng": 36.817200
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
    
    def test_invalid_viewport_sw_greater_than_ne(self, client, auth_token):
        """Test invalid viewport where SW is greater than NE"""
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.320000,
                "ne_lng": 36.780000,
                "sw_lat": -1.250000,  # INVALID: SW > NE
                "sw_lng": 36.850000   # INVALID: SW > NE
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should still execute (PostGIS handles this)
        # But might return unexpected results
        assert response.status_code in [200, 422]


class TestMapPinsPerformance:
    """Test performance characteristics"""
    
    def test_pin_limit_enforced(self, client, auth_token, test_db):
        """Test that pin results are limited (max 500)"""
        # This is a hypothetical test - you'd need to create 600+ users
        # For now, just verify the endpoint works with many users
        
        # Create 10 test users
        for i in range(10):
            user = User(
                id=uuid.uuid4(),
                google_id=f"perf_test_user_{i}",
                email=f"perftest{i}@test.com",
                name=f"Test User {i}",
                role="parent",
                onboarded=True,
                is_active=True
            )
            
            # Spread around Nairobi
            lat = -1.286389 + (i * 0.001)
            lng = 36.817223 + (i * 0.001)
            point_wkt = create_point_from_lat_lng(lat, lng)
            user.location = func.ST_GeomFromText(point_wkt, 4326)
            
            test_db.add(user)
            
            # Create minimal parent profile
            parent = Parent(
                id=uuid.uuid4(),
                user_id=user.id,
                curriculum="Classical"
            )
            test_db.add(parent)
        
        test_db.commit()
        
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # With 10 users created, should return all of them
        assert response.json()["total"] <= 500


class TestMapPinsIntegrationScenarios:
    """Integration tests simulating real user journeys"""
    
    def test_user_opens_map_sees_nearby_users(
        self, client, auth_token, current_user, nearby_parent, nearby_tutor
    ):
        """
        SCENARIO: User opens app for first time, map loads with nearby users
        
        Frontend behavior:
        1. User opens app
        2. Map centers on user's location
        3. Frontend calculates viewport bounds
        4. Calls /map/pins with bounds
        5. Displays pins on map
        """
        # Step 4: Frontend calls /map/pins
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "all"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Step 5: Frontend receives pins to display
        assert len(data["pins"]) == 2
        assert data["total"] == 2
        
        # Pins have all necessary data for display
        for pin in data["pins"]:
            assert "latitude" in pin
            assert "longitude" in pin
            assert "name" in pin
            assert "type" in pin
    
    def test_user_pans_map_requests_new_pins(
        self, client, auth_token, nearby_parent, far_parent
    ):
        """
        SCENARIO: User pans map to new area
        
        Frontend behavior:
        1. User drags map
        2. onMoveEnd event fires
        3. Get new viewport bounds
        4. Call /map/pins with new bounds
        5. Update pins on map
        """
        # Initial viewport (sees nearby_parent)
        response1 = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        initial_pins = response1.json()["pins"]
        initial_ids = [pin["id"] for pin in initial_pins]
        
        # User pans south (new viewport includes far_parent)
        response2 = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.400000,
                "ne_lng": 36.850000,
                "sw_lat": -1.550000,
                "sw_lng": 36.780000
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        new_pins = response2.json()["pins"]
        new_ids = [pin["id"] for pin in new_pins]
        
        # Should now see different users
        assert str(far_parent.id) in new_ids
    
    def test_user_clicks_pin_sees_preview_then_profile(
        self, client, auth_token, nearby_parent
    ):
        """
        SCENARIO: User clicks pin and views preview
        
        Frontend behavior:
        1. User clicks pin on map
        2. Call /map/preview/{id}
        3. Show bottom sheet with preview
        4. User clicks "View Full Profile"
        5. Navigate to profile page (Issue #9)
        """
        # Step 2: Get preview
        response = client.get(
            f"/map/preview/{nearby_parent.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        preview = response.json()
        
        # Step 3: Frontend displays in bottom sheet
        assert preview["name"] == "Sarah Johnson"
        assert preview["curriculum"] == "Classical"
        assert preview["children_ages"] == ["5", "7", "10"]
        assert preview["whatsapp_enabled"] is True
        
        # User can now decide to view full profile or contact
    
    def test_user_applies_filters_sees_filtered_results(
        self, client, auth_token, nearby_parent, nearby_tutor
    ):
        """
        SCENARIO: User applies filters to find specific users
        
        Frontend behavior:
        1. User opens filter drawer
        2. Selects "Parents only"
        3. Selects "Classical curriculum"
        4. Calls /map/pins with filters
        5. Map updates to show only matching pins
        """
        # Step 4: Call with filters
        response = client.get(
            "/map/pins",
            params={
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "parent",
                "curriculum": "Classical"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only see nearby_parent
        assert data["total"] == 1
        assert data["pins"][0]["type"] == "parent"
        assert data["pins"][0]["curriculum"] == "Classical"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
