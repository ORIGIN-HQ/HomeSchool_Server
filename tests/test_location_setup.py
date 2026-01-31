"""
Test suite for Issue 5: Location Setup (Pin + Radius)

Tests:
- Parent profile creation with location
- Tutor profile creation with location
- Location validation
- Geo index verification
- Privacy defaults
- Error cases
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Parent, Tutor
from app.core.security import create_access_token

# use a test database
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
def parent_user(test_db):
    """Create a test parent user"""
    user = User(
        id=uuid.uuid4(),
        google_id="test_parent_google_id",
        email="parent@test.com",
        name="Test Parent",
        picture="https://example.com/pic.jpg",
        role="parent",
        onboarded=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def tutor_user(test_db):
    """Create a test tutor user"""
    user = User(
        id=uuid.uuid4(),
        google_id="test_tutor_google_id",
        email="tutor@test.com",
        name="Test Tutor",
        picture="https://example.com/pic.jpg",
        role="tutor",
        onboarded=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def parent_auth_token(parent_user):
    """Generate JWT token for parent user"""
    token_data = {
        "user_id": str(parent_user.id),
        "email": parent_user.email,
        "role": parent_user.role
    }
    return create_access_token(data=token_data)


@pytest.fixture
def tutor_auth_token(tutor_user):
    """Generate JWT token for tutor user"""
    token_data = {
        "user_id": str(tutor_user.id),
        "email": tutor_user.email,
        "role": tutor_user.role
    }
    return create_access_token(data=token_data)


# Test Cases
class TestParentProfileCreation:
    """Test parent profile creation with location"""
    
    def test_create_parent_profile_success(self, client, parent_user, parent_auth_token, test_db):
        """Test successful parent profile creation with valid location"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 5000
            },
            "children_ages": ["5", "7", "10"],
            "curriculum": "Classical",
            "religion": "Christian",
            "whatsapp_number": "+254712345678",
            "whatsapp_enabled": True,
            "in_coop": True,
            "coop_name": "Nairobi Homeschool Coop"
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response
        assert "id" in data
        assert data["user_id"] == str(parent_user.id)
        assert "created successfully" in data["message"]
        
        # Verify database - user location updated
        user = test_db.query(User).filter(User.id == parent_user.id).first()
        assert user.onboarded is True
        assert user.location is not None
        assert user.visibility_radius_meters == 5000
        
        # Verify location coordinates (using PostGIS functions)
        lat = test_db.query(
            func.ST_Y(func.ST_Transform(user.location, 4326))
        ).scalar()
        lng = test_db.query(
            func.ST_X(func.ST_Transform(user.location, 4326))
        ).scalar()
        
        assert round(lat, 6) == -1.286389
        assert round(lng, 6) == 36.817223
        
        # Verify parent profile created
        parent = test_db.query(Parent).filter(Parent.user_id == parent_user.id).first()
        assert parent is not None
        assert parent.curriculum == "Classical"
        assert parent.whatsapp_enabled is True
        assert parent.in_coop is True
    
    def test_create_parent_profile_minimal_data(self, client, parent_user, parent_auth_token, test_db):
        """Test parent profile creation with only required location data"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
        
        # Verify default radius
        user = test_db.query(User).filter(User.id == parent_user.id).first()
        assert user.visibility_radius_meters == 5000  # Default
        assert user.onboarded is True
    
    def test_create_parent_profile_custom_radius(self, client, parent_user, parent_auth_token, test_db):
        """Test parent profile with custom visibility radius"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 10000
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
        
        user = test_db.query(User).filter(User.id == parent_user.id).first()
        assert user.visibility_radius_meters == 10000
    
    def test_create_parent_profile_invalid_latitude(self, client, parent_user, parent_auth_token):
        """Test parent profile with invalid latitude (out of range)"""
        payload = {
            "location": {
                "latitude": 91.0,  # Invalid: must be -90 to 90
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_parent_profile_invalid_longitude(self, client, parent_user, parent_auth_token):
        """Test parent profile with invalid longitude (out of range)"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 181.0  # Invalid: must be -180 to 180
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_parent_profile_radius_too_small(self, client, parent_user, parent_auth_token):
        """Test parent profile with radius below minimum"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 100  # Invalid: minimum is 500
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_parent_profile_radius_too_large(self, client, parent_user, parent_auth_token):
        """Test parent profile with radius above maximum"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 60000  # Invalid: maximum is 50000
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_parent_profile_wrong_role(self, client, tutor_user, tutor_auth_token):
        """Test that tutor user cannot create parent profile"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {tutor_auth_token}"}
        )
        
        assert response.status_code == 400
        assert "role must be 'parent'" in response.json()["detail"]
    
    def test_create_parent_profile_duplicate(self, client, parent_user, parent_auth_token, test_db):
        """Test that duplicate parent profile cannot be created"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        # First creation - should succeed
        response1 = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        assert response1.status_code == 201
        
        # Second creation - should fail
        response2 = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    def test_create_parent_profile_no_auth(self, client):
        """Test that unauthenticated request fails"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        response = client.post("/parents", json=payload)
        assert response.status_code == 401  # No auth header


class TestTutorProfileCreation:
    """Test tutor profile creation with location"""
    
    def test_create_tutor_profile_success(self, client, tutor_user, tutor_auth_token, test_db):
        """Test successful tutor profile creation with valid location"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 10000
            },
            "subjects": ["Mathematics", "Science", "English"],
            "curriculum": "British",
            "certifications": ["B.Ed", "TEFL"],
            "availability": "Weekday mornings",
            "whatsapp_number": "+254712345678",
            "whatsapp_enabled": True
        }

        response = client.post(
            "/tutors",
            json=payload,
            headers={"Authorization": f"Bearer {tutor_auth_token}"}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response
        assert "id" in data
        assert data["user_id"] == str(tutor_user.id)
        assert "created successfully" in data["message"]
        assert "visible on the map" in data["message"]

        # Verify database - user location updated
        user = test_db.query(User).filter(User.id == tutor_user.id).first()
        assert user.onboarded is True
        assert user.location is not None
        assert user.visibility_radius_meters == 10000

        # Verify tutor profile created
        tutor = test_db.query(Tutor).filter(Tutor.user_id == tutor_user.id).first()
        assert tutor is not None
        assert tutor.curriculum == "British"
        assert tutor.whatsapp_enabled is True
        assert tutor.verification_status == "verified"
        assert tutor.verified_at is not None
    
    def test_create_tutor_profile_minimal_data(self, client, tutor_user, tutor_auth_token, test_db):
        """Test tutor profile creation with only required location data"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/tutors",
            json=payload,
            headers={"Authorization": f"Bearer {tutor_auth_token}"}
        )
        
        assert response.status_code == 201
        
        # Verify default radius
        user = test_db.query(User).filter(User.id == tutor_user.id).first()
        assert user.visibility_radius_meters == 5000  # Default
        assert user.onboarded is True
    
    def test_create_tutor_profile_wrong_role(self, client, parent_user, parent_auth_token):
        """Test that parent user cannot create tutor profile"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/tutors",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 400
        assert "role must be 'tutor'" in response.json()["detail"]


class TestGeoIndexVerification:
    """Test that geo indexes are working correctly"""
    
    def test_spatial_index_exists(self, test_db):
        """Verify that spatial index exists on users.location"""
        result = test_db.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'users' 
            AND indexname = 'idx_users_location'
        """))
        
        index = result.fetchone()
        assert index is not None, "Spatial index 'idx_users_location' should exist"
    
    def test_location_queryable(self, client, parent_user, parent_auth_token, test_db):
        """Test that location can be queried using PostGIS functions"""
        # Create profile with location
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
            }
        }
        
        client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        # Query using PostGIS functions
        user = test_db.query(User).filter(User.id == parent_user.id).first()
        
        # Test that we can extract coordinates
        lat = test_db.query(
            func.ST_Y(func.ST_Transform(user.location, 4326))
        ).scalar()
        
        lng = test_db.query(
            func.ST_X(func.ST_Transform(user.location, 4326))
        ).scalar()
        
        assert lat is not None
        assert lng is not None
        assert -90 <= lat <= 90
        assert -180 <= lng <= 180


class TestPrivacyDefaults:
    """Test privacy and default values"""
    
    def test_default_visibility_radius(self, client, parent_user, parent_auth_token, test_db):
        """Test that default visibility radius is 5000m"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 36.817223
                # No visibility_radius_meters provided
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
        
        user = test_db.query(User).filter(User.id == parent_user.id).first()
        assert user.visibility_radius_meters == 5000
    
    def test_user_invisible_without_location(self, test_db):
        """Test that users without location are NULL in database"""
        user = User(
            id=uuid.uuid4(),
            google_id="no_location_user",
            email="nolocation@test.com",
            name="No Location User",
            role="parent",
            onboarded=False
        )
        test_db.add(user)
        test_db.commit()
        
        # Verify location is NULL
        assert user.location is None
        
        # This user should be filtered out of map queries
        users_with_location = test_db.query(User).filter(
            User.location.isnot(None)
        ).all()
        
        assert user not in users_with_location


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_location_at_equator(self, client, parent_user, parent_auth_token, test_db):
        """Test location at equator (0 latitude)"""
        payload = {
            "location": {
                "latitude": 0.0,
                "longitude": 36.817223
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
    
    def test_location_at_prime_meridian(self, client, parent_user, parent_auth_token, test_db):
        """Test location at prime meridian (0 longitude)"""
        payload = {
            "location": {
                "latitude": -1.286389,
                "longitude": 0.0
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
    
    def test_location_at_boundary_latitude(self, client, parent_user, parent_auth_token):
        """Test location at maximum latitude"""
        payload = {
            "location": {
                "latitude": 90.0,  # North pole
                "longitude": 0.0
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201
    
    def test_location_at_boundary_longitude(self, client, parent_user, parent_auth_token):
        """Test location at maximum longitude"""
        payload = {
            "location": {
                "latitude": 0.0,
                "longitude": 180.0  # International date line
            }
        }
        
        response = client.post(
            "/parents",
            json=payload,
            headers={"Authorization": f"Bearer {parent_auth_token}"}
        )
        
        assert response.status_code == 201


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
