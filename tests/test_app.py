"""
Tests for the Mergington High School Activities API
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Import app module to access activities
    from app import activities
    
    # Store original state
    original = {k: {"participants": list(v["participants"])} for k, v in activities.items()}
    
    yield
    
    # Restore original state
    for activity_name, data in original.items():
        activities[activity_name]["participants"] = data["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Basketball" in data
        assert "Tennis Club" in data

    def test_get_activities_contains_required_fields(self, client):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_participants_are_strings(self, client):
        """Test that participants in activities are email strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup?email=neustudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "neustudent@mergington.edu" in data["message"]
        assert "Basketball" in data["message"]

    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds the participant to the activity"""
        from app import activities
        
        initial_count = len(activities["Basketball"]["participants"])
        response = client.post(
            "/activities/Basketball/signup?email=newperson@mergington.edu"
        )
        assert response.status_code == 200
        assert len(activities["Basketball"]["participants"]) == initial_count + 1
        assert "newperson@mergington.edu" in activities["Basketball"]["participants"]

    def test_signup_for_nonexistent_activity_returns_404(self, client):
        """Test that signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonexistentClub/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_already_registered_returns_400(self, client, reset_activities):
        """Test that signing up twice returns 400 error"""
        email = "alex@mergington.edu"
        
        # First signup should succeed
        response = client.post(
            f"/activities/Basketball/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_with_different_activities(self, client, reset_activities):
        """Test signup for multiple different activities"""
        email = "student@mergington.edu"
        
        response1 = client.post(
            f"/activities/Basketball/signup?email={email}"
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            f"/activities/Tennis%20Club/signup?email={email}"
        )
        assert response2.status_code == 200


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_from_activity_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        from app import activities
        
        # Use an existing participant
        email = activities["Basketball"]["participants"][0]
        
        response = client.post(
            f"/activities/Basketball/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        from app import activities
        
        email = activities["Basketball"]["participants"][0]
        initial_count = len(activities["Basketball"]["participants"])
        
        response = client.post(
            f"/activities/Basketball/unregister?email={email}"
        )
        assert response.status_code == 200
        assert len(activities["Basketball"]["participants"]) == initial_count - 1
        assert email not in activities["Basketball"]["participants"]

    def test_unregister_nonexistent_activity_returns_404(self, client):
        """Test that unregistering from non-existent activity returns 404"""
        response = client.post(
            "/activities/NonexistentClub/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_not_signed_up_returns_400(self, client, reset_activities):
        """Test that unregistering when not signed up returns 400"""
        response = client.post(
            "/activities/Basketball/unregister?email=notsignedupstudent@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]

    def test_signup_then_unregister_cycle(self, client, reset_activities):
        """Test signup followed by unregister"""
        from app import activities
        
        email = "cyclestudent@mergington.edu"
        initial_count = len(activities["Tennis Club"]["participants"])
        
        # Sign up
        response1 = client.post(
            f"/activities/Tennis%20Club/signup?email={email}"
        )
        assert response1.status_code == 200
        assert len(activities["Tennis Club"]["participants"]) == initial_count + 1
        
        # Unregister
        response2 = client.post(
            f"/activities/Tennis%20Club/unregister?email={email}"
        )
        assert response2.status_code == 200
        assert len(activities["Tennis Club"]["participants"]) == initial_count


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
