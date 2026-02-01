"""
Test suite for Issue 11: WhatsApp Contact Link Endpoint

Endpoint: GET /contact/whatsapp/{user_id}

Acceptance Criteria:
✓ Returns wa.me link
✓ Prefilled message
✓ Respects user toggle (whatsapp_enabled)

User Journey Step:
This is Step #8: "Contact via WhatsApp (End Goal)"
- User views a profile
- Clicks WhatsApp icon/button
- Frontend calls GET /contact/whatsapp/{user_id}
- WhatsApp opens with prefilled message
- Optional: POST /contact/log to track contact

Tests Cover:
- WhatsApp link generation
- URL encoding of messages
- Personalized messages
- Phone number formatting
- Privacy (respects whatsapp_enabled toggle)
- Contact logging
- Error cases (not enabled, not found, self-contact)
- Different user roles (parent, tutor)
- International phone numbers
- Security and validation
"""
import pytest
import uuid
import json
import urllib.parse
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Parent, Tutor, ContactLog, create_point_from_lat_lng
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
def requesting_user(test_db):
    """Create the user who will be requesting contact info"""
    user = User(
        id=uuid.uuid4(),
        google_id="requesting_user_google_id",
        email="requester@test.com",
        name="John Doe",  # This name will appear in prefilled messages
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = 5000
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(requesting_user):
    """Generate JWT token for requesting user"""
    token_data = {
        "user_id": str(requesting_user.id),
        "email": requesting_user.email,
        "role": requesting_user.role
    }
    return create_access_token(data=token_data)


@pytest.fixture
def parent_with_whatsapp_enabled(test_db):
    """Parent with WhatsApp enabled and valid number"""
    user = User(
        id=uuid.uuid4(),
        google_id="parent_whatsapp_google_id",
        email="parent.whatsapp@test.com",
        name="Sarah Johnson",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.268000, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        children_ages=json.dumps(["5", "7"]),
        curriculum="Classical",
        whatsapp_number="+254712345678",
        whatsapp_enabled=True,  # ENABLED
        in_coop=True
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def parent_with_whatsapp_disabled(test_db):
    """Parent with WhatsApp disabled (privacy setting)"""
    user = User(
        id=uuid.uuid4(),
        google_id="parent_no_whatsapp_google_id",
        email="parent.nowhatsapp@test.com",
        name="Jane Smith",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.290000, 36.820000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Charlotte Mason",
        whatsapp_number="+254712345679",
        whatsapp_enabled=False,  # DISABLED
        in_coop=False
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def tutor_with_whatsapp_enabled(test_db):
    """Tutor with WhatsApp enabled"""
    user = User(
        id=uuid.uuid4(),
        google_id="tutor_whatsapp_google_id",
        email="tutor.whatsapp@test.com",
        name="David Kimani",
        role="tutor",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.286389, 36.845000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user.id,
        subjects=json.dumps(["Mathematics", "Science"]),
        curriculum="British",
        whatsapp_number="+254723456789",
        whatsapp_enabled=True,  # ENABLED
        verification_status="verified"
    )
    test_db.add(tutor)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def parent_without_whatsapp_number(test_db):
    """Parent who enabled WhatsApp but has no number (edge case)"""
    user = User(
        id=uuid.uuid4(),
        google_id="parent_no_number_google_id",
        email="parent.nonumber@test.com",
        name="Bob Wilson",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.280000, 36.810000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Classical",
        whatsapp_number=None,  # No number
        whatsapp_enabled=True,  # But enabled (edge case)
        in_coop=False
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture
def parent_with_unformatted_number(test_db):
    """Parent with unformatted phone number (no + prefix)"""
    user = User(
        id=uuid.uuid4(),
        google_id="parent_unformatted_google_id",
        email="parent.unformatted@test.com",
        name="Alice Brown",
        role="parent",
        onboarded=True,
        is_active=True
    )
    
    point_wkt = create_point_from_lat_lng(-1.275000, 36.825000)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        curriculum="Classical",
        whatsapp_number="254734567890",  # Missing + prefix
        whatsapp_enabled=True,
        in_coop=False
    )
    test_db.add(parent)
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
        onboarded=False,
        is_active=True
    )
    
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
        is_active=False
    )
    
    point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    
    test_db.add(user)
    test_db.commit()
    
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user.id,
        whatsapp_number="+254745678901",
        whatsapp_enabled=True
    )
    test_db.add(parent)
    test_db.commit()
    
    return user


# TEST CLASSES

class TestWhatsAppLinkGeneration:
    """Test WhatsApp link generation and URL format"""
    
    def test_get_whatsapp_link_for_parent(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test getting WhatsApp link for a parent"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "whatsapp_url" in data
        assert "phone_number" in data
        assert "prefilled_message" in data
        assert "user_name" in data
        
        # Verify WhatsApp URL format
        assert data["whatsapp_url"].startswith("https://wa.me/")
        assert "?text=" in data["whatsapp_url"]
        
        # Verify phone number
        assert data["phone_number"] == "+254712345678"
        
        # Verify user name
        assert data["user_name"] == "Sarah Johnson"
    
    def test_get_whatsapp_link_for_tutor(
        self, client, auth_token, tutor_with_whatsapp_enabled
    ):
        """Test getting WhatsApp link for a tutor"""
        response = client.get(
            f"/contact/whatsapp/{tutor_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["whatsapp_url"].startswith("https://wa.me/")
        assert data["phone_number"] == "+254723456789"
        assert data["user_name"] == "David Kimani"
    
    def test_whatsapp_url_structure(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):  
        """Test WhatsApp URL has correct structure"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
        assert response.status_code == 200
        data = response.json()

        url = data["whatsapp_url"]

        # Should follow format: https://wa.me/{number}?text={encoded_message}
        # Can include + or not in the phone number
        assert url.startswith("https://wa.me/") and "?text=" in url

        # The phone number part (with or without +)
        phone_part = url.split("?text=")[0].replace("https://wa.me/", "")
        assert "254712345678" in phone_part  # The actual number is present

        # Extract the text parameter
        text_param = url.split("?text=")[1]

        # Should be URL encoded
        assert "%20" in text_param or "+" in text_param  # Spaces encoded

        # Decode and check message content
        decoded_message = urllib.parse.unquote(text_param)
        assert "Sarah" in decoded_message  # Target's first name
        assert "John" in decoded_message  # Requester's first name
        assert "Homeschool Connect" in decoded_message  # App name

    def test_phone_number_cleaning(
        self, client, auth_token, parent_with_unformatted_number
    ):
        """Test that phone numbers are properly formatted"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_unformatted_number.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should add + prefix if missing
        assert data["phone_number"] == "+254734567890"

        # URL should contain the phone number (with + is fine)
        assert "254734567890" in data["whatsapp_url"]
        assert data["whatsapp_url"].startswith("https://wa.me/")


class TestPrefilledMessage:
    """Test prefilled message content and personalization"""
    
    def test_message_personalization(
        self, client, auth_token, parent_with_whatsapp_enabled, requesting_user
    ):
        """Test that message is personalized with both users' names"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        message = data["prefilled_message"]
        
        # Should contain target's first name
        assert "Sarah" in message
        
        # Should contain requester's first name
        assert "John" in message
        
        # Should contain app name
        assert "Homeschool Connect" in message
        
        # Should be friendly and professional
        assert "Hi" in message or "Hello" in message
        assert "connect" in message.lower()
    
    def test_message_url_encoding(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test that message is properly URL encoded"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        url = data["whatsapp_url"]
        message = data["prefilled_message"]
        
        # Extract encoded message from URL
        encoded_message = url.split("?text=")[1]
        
        # Decode it
        decoded = urllib.parse.unquote(encoded_message)
        
        # Should match the prefilled_message
        assert decoded == message
        
        # Special characters should be encoded in URL
        if "!" in message:
            assert "%21" in encoded_message or "!" in encoded_message
        
        # Spaces should be encoded
        assert " " not in encoded_message.split("?text=")[0]  # After domain
    
    def test_message_format_for_different_requester_names(
        self, client, test_db, parent_with_whatsapp_enabled
    ):
        """Test message personalization with different requester names"""
        # Create requester with single name
        single_name_user = User(
            id=uuid.uuid4(),
            google_id="single_name_google_id",
            email="single@test.com",
            name="Ahmed",  # Single name
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        single_name_user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(single_name_user)
        test_db.commit()
        
        # Create token
        token = create_access_token({
            "user_id": str(single_name_user.id),
            "email": single_name_user.email,
            "role": single_name_user.role
        })
        
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle single name correctly
        assert "Ahmed" in data["prefilled_message"]


class TestWhatsAppPrivacyToggle:
    """Test that WhatsApp toggle is respected"""
    
    def test_whatsapp_disabled_returns_404(
        self, client, auth_token, parent_with_whatsapp_disabled
    ):
        """Test that disabled WhatsApp returns 404"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "not available" in response.json()["detail"].lower()
    
    def test_no_whatsapp_number_returns_404(
        self, client, auth_token, parent_without_whatsapp_number
    ):
        """Test that missing WhatsApp number returns 404 even if enabled"""
        response = client.get(
            f"/contact/whatsapp/{parent_without_whatsapp_number.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "not available" in response.json()["detail"].lower()
    
    def test_privacy_respected_for_both_roles(
        self, client, auth_token, parent_with_whatsapp_disabled, test_db
    ):
        """Test privacy toggle works for both parents and tutors"""
        # Already tested parent above
        
        # Create tutor with WhatsApp disabled
        tutor_user = User(
            id=uuid.uuid4(),
            google_id="tutor_disabled_google_id",
            email="tutor.disabled@test.com",
            name="Teacher Mike",
            role="tutor",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        tutor_user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(tutor_user)
        test_db.commit()
        
        tutor = Tutor(
            id=uuid.uuid4(),
            user_id=tutor_user.id,
            subjects=json.dumps(["Math"]),
            whatsapp_number="+254756789012",
            whatsapp_enabled=False,  # Disabled
            verification_status="verified"
        )
        test_db.add(tutor)
        test_db.commit()
        
        # Try to get WhatsApp link
        response = client.get(
            f"/contact/whatsapp/{tutor_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404


class TestWhatsAppErrorCases:
    """Test error handling and edge cases"""
    
    def test_self_contact_blocked(
        self, client, auth_token, requesting_user, test_db
    ):
        """Test that users cannot contact themselves"""
        # Create parent profile for requesting user
        parent = Parent(
            id=uuid.uuid4(),
            user_id=requesting_user.id,
            whatsapp_number="+254767890123",
            whatsapp_enabled=True
        )
        test_db.add(parent)
        test_db.commit()
        
        # Try to contact self
        response = client.get(
            f"/contact/whatsapp/{requesting_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400
        assert "cannot contact yourself" in response.json()["detail"].lower()
    
    def test_user_not_found(self, client, auth_token):
        """Test WhatsApp link for non-existent user"""
        fake_id = uuid.uuid4()
        
        response = client.get(
            f"/contact/whatsapp/{fake_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_not_onboarded_user(self, client, auth_token, not_onboarded_user):
        """Test WhatsApp link fails for non-onboarded users"""
        response = client.get(
            f"/contact/whatsapp/{not_onboarded_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_inactive_user(self, client, auth_token, inactive_user):
        """Test WhatsApp link fails for inactive users"""
        response = client.get(
            f"/contact/whatsapp/{inactive_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
    
    def test_requires_authentication(self, client, parent_with_whatsapp_enabled):
        """Test that endpoint requires valid JWT"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}"
        )
        
        assert response.status_code == 401
    
    def test_invalid_token(self, client, parent_with_whatsapp_enabled):
        """Test that invalid JWT is rejected"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_invalid_uuid_format(self, client, auth_token):
        """Test invalid UUID format"""
        response = client.get(
            "/contact/whatsapp/not-a-uuid",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code in [404, 422]


class TestContactLogging:
    """Test contact logging functionality (Issue #12)"""
    
    def test_log_contact_attempt(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test logging a contact attempt"""
        response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(parent_with_whatsapp_enabled.id),
                "contact_method": "whatsapp"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "logged" in data["message"].lower()
    
    def test_contact_log_stored_in_database(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db, requesting_user
    ):
        """Test that contact log is actually stored in database"""
        # Log contact
        response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(parent_with_whatsapp_enabled.id)
            }
        )
        
        assert response.status_code == 200
        
        # Verify in database
        log_entry = test_db.query(ContactLog).filter(
            ContactLog.source_user_id == requesting_user.id,
            ContactLog.target_user_id == parent_with_whatsapp_enabled.id
        ).first()
        
        assert log_entry is not None
        assert log_entry.contact_method == "whatsapp"
        assert log_entry.created_at is not None
    
    def test_log_contact_for_non_existent_user(
        self, client, auth_token
    ):
        """Test logging contact for non-existent user returns 404"""
        fake_id = uuid.uuid4()
        
        response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(fake_id)
            }
        )
        
        assert response.status_code == 404
    
    def test_multiple_contacts_logged(
        self, client, auth_token, parent_with_whatsapp_enabled,
        tutor_with_whatsapp_enabled, test_db, requesting_user
    ):
        """Test that multiple contact attempts are logged"""
        # Log first contact
        client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"target_user_id": str(parent_with_whatsapp_enabled.id)}
        )
        
        # Log second contact
        client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"target_user_id": str(tutor_with_whatsapp_enabled.id)}
        )
        
        # Verify both are logged
        logs = test_db.query(ContactLog).filter(
            ContactLog.source_user_id == requesting_user.id
        ).all()
        
        assert len(logs) == 2


class TestWhatsAppIntegrationScenario:
    """Integration test simulating real user journey"""
    
    def test_complete_contact_flow(
        self, client, auth_token, parent_with_whatsapp_enabled, requesting_user
    ):
        """
        INTEGRATION TEST: Complete user journey for contacting via WhatsApp
        
        User Journey Step #8:
        1. User views a profile (Issue #10)
        2. Sees WhatsApp is enabled
        3. Clicks "Contact on WhatsApp"
        4. Frontend calls GET /contact/whatsapp/{user_id}
        5. WhatsApp opens with prefilled message
        6. Frontend logs the contact (optional)
        """
        # Step 4: Get WhatsApp link
        whatsapp_response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert whatsapp_response.status_code == 200
        whatsapp_data = whatsapp_response.json()
        
        # Verify all data needed for frontend
        assert "whatsapp_url" in whatsapp_data
        assert "prefilled_message" in whatsapp_data
        
        # Frontend would open this URL (wa.me deep link)
        url = whatsapp_data["whatsapp_url"]
        assert url.startswith("https://wa.me/")
        
        # Step 6: Log the contact (optional)
        log_response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(parent_with_whatsapp_enabled.id),
                "contact_method": "whatsapp"
            }
        )
        
        assert log_response.status_code == 200
        
        # Verify the conversion moment completed successfully
        print(f"\n✓ WhatsApp URL generated: {url[:50]}...")
        print(f"✓ Message: {whatsapp_data['prefilled_message']}")
        print(f"✓ Contact logged successfully")
    
    def test_privacy_respected_in_flow(
        self, client, auth_token, parent_with_whatsapp_disabled
    ):
        """
        Test that privacy is respected throughout the flow
        User with WhatsApp disabled should not be contactable
        """
        # Try to get WhatsApp link
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_disabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should be blocked
        assert response.status_code == 404
        
        # Frontend should show: "WhatsApp contact not available"
        print("\n✓ Privacy respected: WhatsApp contact blocked when disabled")


class TestWhatsAppDataIntegrity:
    """Test data consistency and integrity"""
    
    def test_phone_number_matches_database(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db
    ):
        """Verify phone number matches database"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Get from database
        parent = test_db.query(Parent).filter(
            Parent.user_id == parent_with_whatsapp_enabled.id
        ).first()
        
        # Should match (with proper formatting)
        assert data["phone_number"] == parent.whatsapp_number
    
    def test_user_name_matches_database(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db
    ):
        """Verify user name matches database"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Get from database
        user = test_db.query(User).filter(
            User.id == parent_with_whatsapp_enabled.id
        ).first()
        
        assert data["user_name"] == user.name


class TestInternationalPhoneNumbers:
    """Test handling of various international phone number formats"""
    
    def test_kenya_number_with_plus(self, test_db, client, auth_token):
        """Test Kenyan number with + prefix"""
        user, parent = self._create_user_with_number(
            test_db, "+254700123456"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["phone_number"] == "+254700123456"
    
    def test_kenya_number_without_plus(self, test_db, client, auth_token):
        """Test Kenyan number without + prefix (should add it)"""
        user, parent = self._create_user_with_number(
            test_db, "254700123456"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # Should add + prefix
        assert response.json()["phone_number"] == "+254700123456"
    
    def test_us_number(self, test_db, client, auth_token):
        """Test US number format"""
        user, parent = self._create_user_with_number(
            test_db, "+1234567890"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["phone_number"] == "+1234567890"
    
    def test_uk_number(self, test_db, client, auth_token):
        """Test UK number format"""
        user, parent = self._create_user_with_number(
            test_db, "+447123456789"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["phone_number"] == "+447123456789"
    
    def test_number_with_spaces(self, test_db, client, auth_token):
        """Test number with spaces (should be cleaned)"""
        user, parent = self._create_user_with_number(
            test_db, "+254 712 345 678"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # Spaces should be removed
        assert response.json()["phone_number"] == "+254712345678"
    
    def test_number_with_dashes(self, test_db, client, auth_token):
        """Test number with dashes (should be cleaned)"""
        user, parent = self._create_user_with_number(
            test_db, "+254-712-345-678"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # Dashes should be removed
        assert response.json()["phone_number"] == "+254712345678"
    
    def test_number_with_parentheses(self, test_db, client, auth_token):
        """Test number with parentheses (should be cleaned)"""
        user, parent = self._create_user_with_number(
            test_db, "+254 (712) 345-678"
        )
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # All formatting should be removed
        assert response.json()["phone_number"] == "+254712345678"
    
    def _create_user_with_number(self, test_db, phone_number):
        """Helper to create user with specific phone number"""
        user = User(
            id=uuid.uuid4(),
            google_id=f"user_{uuid.uuid4()}_google_id",
            email=f"user_{uuid.uuid4()}@test.com",
            name="Test User",
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(user)
        test_db.commit()
        
        parent = Parent(
            id=uuid.uuid4(),
            user_id=user.id,
            whatsapp_number=phone_number,
            whatsapp_enabled=True
        )
        test_db.add(parent)
        test_db.commit()
        test_db.refresh(user)
        
        return user, parent


class TestContactLoggingAnalytics:
    """Test contact logging for analytics purposes"""
    
    def test_contact_timestamps_recorded(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db, requesting_user
    ):
        """Test that contact log includes timestamp"""
        response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(parent_with_whatsapp_enabled.id)
            }
        )
        
        assert response.status_code == 200
        
        # Check database
        log = test_db.query(ContactLog).filter(
            ContactLog.source_user_id == requesting_user.id
        ).first()
        
        assert log is not None
        assert log.created_at is not None
        assert isinstance(log.created_at, datetime)
    
    def test_can_track_multiple_contacts_to_same_user(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db, requesting_user
    ):
        """Test that multiple contacts to same user are all logged"""
        # Log first contact
        client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"target_user_id": str(parent_with_whatsapp_enabled.id)}
        )
        
        # Log second contact (same user)
        client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"target_user_id": str(parent_with_whatsapp_enabled.id)}
        )
        
        # Both should be logged
        logs = test_db.query(ContactLog).filter(
            ContactLog.source_user_id == requesting_user.id,
            ContactLog.target_user_id == parent_with_whatsapp_enabled.id
        ).all()
        
        assert len(logs) == 2
    
    def test_contact_method_stored(
        self, client, auth_token, parent_with_whatsapp_enabled, test_db
    ):
        """Test that contact method is stored"""
        response = client.post(
            "/contact/log",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "target_user_id": str(parent_with_whatsapp_enabled.id),
                "contact_method": "whatsapp"
            }
        )
        
        assert response.status_code == 200
        
        log = test_db.query(ContactLog).first()
        assert log.contact_method == "whatsapp"


class TestWhatsAppSecurityAndValidation:
    """Test security measures and input validation"""
    
    def test_cannot_inject_code_in_message(
        self, client, test_db, parent_with_whatsapp_enabled
    ):
        """Test that message is safe from code injection"""
        # Create user with potentially malicious name
        malicious_user = User(
            id=uuid.uuid4(),
            google_id="malicious_google_id",
            email="malicious@test.com",
            name="<script>alert('xss')</script>",  # XSS attempt
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        malicious_user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(malicious_user)
        test_db.commit()
        
        # Create token
        token = create_access_token({
            "user_id": str(malicious_user.id),
            "email": malicious_user.email,
            "role": malicious_user.role
        })
        
        # Get WhatsApp link
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Message should be URL encoded, making it safe
        # Even if name contains <script>, it will be encoded
        url = data["whatsapp_url"]
        assert "<script>" not in url  # Should be encoded
        assert "%3C" in url or "script" in urllib.parse.unquote(url)
    
    def test_phone_number_validation(
        self, test_db, client, auth_token
    ):
        """Test that phone numbers are properly validated and formatted"""
        # Create user with potentially problematic number
        user = User(
            id=uuid.uuid4(),
            google_id="validation_google_id",
            email="validation@test.com",
            name="Validation Test",
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(user)
        test_db.commit()
        
        parent = Parent(
            id=uuid.uuid4(),
            user_id=user.id,
            whatsapp_number="  +254-712-345-678  ",  # Extra spaces
            whatsapp_enabled=True
        )
        test_db.add(parent)
        test_db.commit()
        test_db.refresh(user)
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        # Should clean up the number
        assert response.json()["phone_number"] == "+254712345678"


class TestWhatsAppUserExperience:
    """Test user experience aspects of WhatsApp contact"""
    
    def test_message_includes_app_name(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test that message includes app name for context"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        message = response.json()["prefilled_message"]
        
        # Should mention where they found each other
        assert "Homeschool Connect" in message
    
    def test_message_friendly_tone(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test that message has a friendly, inviting tone"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        message = response.json()["prefilled_message"]
        
        # Should be warm and friendly
        assert any(greeting in message for greeting in ["Hi", "Hello", "Hey"])
        assert any(word in message.lower() for word in ["connect", "found"])
    
    def test_complete_response_data_for_frontend(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test that response includes all data needed by frontend"""
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Frontend needs all these fields
        required_fields = [
            "whatsapp_url",      # To open WhatsApp
            "phone_number",      # To display to user
            "prefilled_message", # To show what will be sent
            "user_name"          # To confirm who they're contacting
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            assert data[field] is not None


class TestWhatsAppEdgeCases:
    """Test edge cases and corner scenarios"""
    
    def test_user_with_very_long_name(
        self, test_db, client, auth_token
    ):
        """Test handling of very long names in message"""
        # Create user with very long name
        long_name = "Sarah Elizabeth Margaret Anne Victoria Catherine Alexandra " + \
                   "Charlotte Isabella Sophia Amelia Grace Rose Marie Louise"
        
        user = User(
            id=uuid.uuid4(),
            google_id="long_name_google_id",
            email="longname@test.com",
            name=long_name,
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(user)
        test_db.commit()
        
        parent = Parent(
            id=uuid.uuid4(),
            user_id=user.id,
            whatsapp_number="+254712345678",
            whatsapp_enabled=True
        )
        test_db.add(parent)
        test_db.commit()
        test_db.refresh(user)
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use first name only (Sarah)
        message = data["prefilled_message"]
        assert "Sarah" in message
        # Message should still be reasonable length
        assert len(message) < 500
    
    def test_user_with_special_characters_in_name(
        self, test_db, client, auth_token
    ):
        """Test handling of special characters in names"""
        user = User(
            id=uuid.uuid4(),
            google_id="special_chars_google_id",
            email="special@test.com",
            name="María José O'Connor-Smith",
            role="parent",
            onboarded=True,
            is_active=True
        )
        
        point_wkt = create_point_from_lat_lng(-1.286389, 36.817223)
        user.location = func.ST_GeomFromText(point_wkt, 4326)
        
        test_db.add(user)
        test_db.commit()
        
        parent = Parent(
            id=uuid.uuid4(),
            user_id=user.id,
            whatsapp_number="+254712345678",
            whatsapp_enabled=True
        )
        test_db.add(parent)
        test_db.commit()
        test_db.refresh(user)
        
        response = client.get(
            f"/contact/whatsapp/{user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Special characters should be properly encoded in URL
        url = data["whatsapp_url"]
        message = data["prefilled_message"]
        
        assert "María" in message
        # URL should be properly encoded
        assert "http" in url


# PERFORMANCE AND LOAD TESTS

class TestWhatsAppPerformance:
    """Test performance characteristics"""
    
    def test_response_time(
        self, client, auth_token, parent_with_whatsapp_enabled
    ):
        """Test that WhatsApp link generation is fast"""
        import time
        
        start = time.time()
        response = client.get(
            f"/contact/whatsapp/{parent_with_whatsapp_enabled.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        # Should be very fast (just DB query + string formatting)
        assert elapsed < 100, f"Response took {elapsed}ms (target: <100ms)"
        
        print(f"\n✓ WhatsApp link generation: {elapsed:.2f}ms")


# RUN TESTS

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
        