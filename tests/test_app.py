"""
Tests for the Mergington High School API (src/app.py)

Uses AAA (Arrange-Act-Assert) structure and an autouse fixture
to restore the in-memory activities state after each test.
"""

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities_state():
    """
    Snapshot and restore the participants lists after each test.
    
    This prevents signup/unregister mutations from leaking between tests,
    while preserving the activity metadata (description, schedule, max_participants).
    """
    # Snapshot the original participants lists
    original_state = {
        activity_name: activity["participants"].copy()
        for activity_name, activity in activities.items()
    }
    
    yield
    
    # Restore the original participants lists
    for activity_name, original_participants in original_state.items():
        activities[activity_name]["participants"] = original_participants


@pytest.fixture
def client():
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for GET / endpoint."""
    
    def test_root_redirects_to_static_index(self, client):
        """Arrange: GET request to root. Act: Call endpoint. Assert: Verify 307 redirect."""
        # Arrange
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Arrange: Expected activity structure. Act: Fetch activities. Assert: Verify response."""
        # Arrange
        expected_keys = {
            "Chess Club", "Programming Class", "Gym Class", "Soccer Club",
            "Track and Field", "Art Club", "Drama Club", "Debate Club", "Science Club"
        }
        
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert set(result.keys()) == expected_keys
    
    def test_activity_structure_has_required_fields(self, client):
        """Arrange: Known activity. Act: Fetch activities. Assert: Verify structure."""
        # Arrange
        # Act
        response = client.get("/activities")
        activities_data = response.json()
        chess_club = activities_data["Chess Club"]
        
        # Assert
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_activity_participants_are_preserved(self, client):
        """Arrange: Chess Club has known initial participants. Act: Fetch activities. Assert: Verify participants."""
        # Arrange
        expected_participants = {"michael@mergington.edu", "daniel@mergington.edu"}
        
        # Act
        response = client.get("/activities")
        chess_club = response.json()["Chess Club"]
        
        # Assert
        assert set(chess_club["participants"]) == expected_participants


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_successful(self, client):
        """Arrange: New email and valid activity. Act: Sign up. Assert: Verify success response and participant list."""
        # Arrange
        activity = "Soccer Club"
        new_email = "test_user@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": new_email}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == f"Signed up {new_email} for {activity}"
        assert new_email in activities[activity]["participants"]
    
    def test_signup_unknown_activity_returns_404(self, client):
        """Arrange: Non-existent activity name. Act: Try to sign up. Assert: Verify 404 error."""
        # Arrange
        unknown_activity = "Underwater Basket Weaving"
        email = "test@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{unknown_activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        result = response.json()
        assert result["detail"] == "Activity not found"
    
    def test_signup_duplicate_returns_400(self, client):
        """Arrange: Email already signed up. Act: Try to sign up again. Assert: Verify 400 error and no duplicate."""
        # Arrange
        activity = "Chess Club"
        existing_email = "michael@mergington.edu"
        original_participant_count = len(activities[activity]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": existing_email}
        )
        
        # Assert
        assert response.status_code == 400
        result = response.json()
        assert result["detail"] == "Student already signed up for this activity"
        # Verify no duplicate was added
        assert len(activities[activity]["participants"]) == original_participant_count
        assert activities[activity]["participants"].count(existing_email) == 1


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint."""
    
    def test_unregister_successful(self, client):
        """Arrange: Participant in activity. Act: Unregister. Assert: Verify success and participant removed."""
        # Arrange
        activity = "Chess Club"
        email = "michael@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == f"Unregistered {email} from {activity}"
        assert email not in activities[activity]["participants"]
    
    def test_unregister_unknown_activity_returns_404(self, client):
        """Arrange: Non-existent activity name. Act: Try to unregister. Assert: Verify 404 error."""
        # Arrange
        unknown_activity = "Underwater Basket Weaving"
        email = "test@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{unknown_activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        result = response.json()
        assert result["detail"] == "Activity not found"
    
    def test_unregister_non_participant_returns_404(self, client):
        """Arrange: Email not in activity participants. Act: Try to unregister. Assert: Verify 404 error."""
        # Arrange
        activity = "Soccer Club"
        non_participant_email = "nobody@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": non_participant_email}
        )
        
        # Assert
        assert response.status_code == 404
        result = response.json()
        assert result["detail"] == "Student is not signed up for this activity"
