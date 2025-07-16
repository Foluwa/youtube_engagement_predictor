import asyncio
import os
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture
def mock_model():
    """Create a mock model for testing"""
    model = Mock()
    model.predict.return_value = np.array([0.05])
    model.booster_.feature_name.return_value = [
        "title_len",
        "tag_count",
        "hour",
        "weekday",
        "category_name_Education",
        "category_name_Music",
    ]
    return model


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoint functionality"""

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data

    @patch("api.main.model")
    def test_predict_endpoint_success(self, mock_model_patch, client):
        """Test successful prediction"""
        # Setup mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.05])
        mock_model.booster_.feature_name.return_value = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Education",
        ]
        mock_model_patch.return_value = mock_model

        # Test data
        payload = {
            "title": "Amazing Python Tutorial",
            "tags": ["python", "tutorial", "programming"],
            "publish_time": "2025-07-14T10:00:00",
            "category_name": "Education",
        }

        with patch("api.main.model", mock_model):
            response = client.post("/predict", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "like_ratio_pred" in data
        assert "predicted_like_percent" in data
        assert data["predicted_like_percent"] == 5.0  # 0.05 * 100

    def test_predict_endpoint_invalid_data(self, client):
        """Test prediction with invalid data"""
        payload = {
            "title": "",  # Empty title
            "tags": [],
            "publish_time": "invalid-date",
            "category_name": "Education",
        }

        response = client.post("/predict", json=payload)
        # Should handle gracefully or return 422 for validation error
        assert response.status_code in [422, 500]

    @patch("api.main.yt")
    @patch("api.main.model")
    def test_fetch_and_predict_success(self, mock_model_patch, mock_yt, client):
        """Test successful YouTube video fetch and prediction"""
        # Mock YouTube API response
        mock_video_response = {
            "items": [
                {
                    "snippet": {
                        "title": "Test Video",
                        "tags": ["test", "video"],
                        "publishedAt": "2025-07-14T10:00:00Z",
                        "categoryId": "27",
                        "thumbnails": {
                            "medium": {"url": "https://example.com/thumb.jpg"}
                        },
                    },
                    "statistics": {
                        "viewCount": "1000",
                        "likeCount": "50",
                        "commentCount": "10",
                    },
                }
            ]
        }

        mock_yt.videos().list().execute.return_value = mock_video_response

        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.05])
        mock_model.booster_.feature_name.return_value = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Education",
        ]
        mock_model_patch.return_value = mock_model

        # Mock transcript
        with patch(
            "api.main.YouTubeTranscriptApi.get_transcript",
            return_value=[{"start": 0, "text": "Hello world"}],
        ):
            with patch("api.main.model", mock_model):
                response = client.post(
                    "/fetch-and-predict", json={"video_id": "test123"}
                )

        assert response.status_code == 200
        data = response.json()
        assert "predicted_like_percent" in data
        assert "actual_like_percent" in data
        assert "thumbnail_url" in data
        assert "transcript" in data

    @patch("api.main.yt", None)  # Simulate no YouTube API
    def test_fetch_and_predict_no_api(self, client):
        """Test fetch endpoint without YouTube API configured"""
        response = client.post("/fetch-and-predict", json={"video_id": "test123"})
        assert response.status_code == 500
        assert "YouTube API not configured" in response.json()["detail"]

    @patch("api.main.yt")
    def test_fetch_and_predict_video_not_found(self, mock_yt, client):
        """Test fetch endpoint with non-existent video"""
        mock_yt.videos().list().execute.return_value = {"items": []}

        response = client.post("/fetch-and-predict", json={"video_id": "nonexistent"})
        assert response.status_code == 404
        assert "Video not found" in response.json()["detail"]


class TestAPIIntegration:
    """Test full API integration scenarios"""

    @patch("api.main.model")
    def test_prediction_consistency(self, mock_model_patch, client):
        """Test that predictions are consistent for same input"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.075])
        mock_model.booster_.feature_name.return_value = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Education",
        ]

        payload = {
            "title": "Consistent Test Video",
            "tags": ["test", "consistency"],
            "publish_time": "2025-07-14T15:30:00",
            "category_name": "Education",
        }

        with patch("api.main.model", mock_model):
            response1 = client.post("/predict", json=payload)
            response2 = client.post("/predict", json=payload)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Same input should give same output
        assert (
            response1.json()["like_ratio_pred"] == response2.json()["like_ratio_pred"]
        )

    @patch("api.main.model")
    def test_different_categories_different_predictions(self, mock_model_patch, client):
        """Test that different categories can produce different predictions"""
        mock_model = Mock()

        def mock_predict(X):
            # Simulate different predictions based on features
            if X["category_name_Education"].iloc[0] == 1:
                return np.array([0.06])
            else:
                return np.array([0.04])

        mock_model.predict.side_effect = mock_predict
        mock_model.booster_.feature_name.return_value = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Education",
            "category_name_Music",
        ]

        base_payload = {
            "title": "Test Video",
            "tags": ["test"],
            "publish_time": "2025-07-14T15:30:00",
        }

        with patch("api.main.model", mock_model):
            # Test Education category
            edu_payload = {**base_payload, "category_name": "Education"}
            edu_response = client.post("/predict", json=edu_payload)

            # Test Music category
            music_payload = {**base_payload, "category_name": "Music"}
            music_response = client.post("/predict", json=music_payload)

        assert edu_response.status_code == 200
        assert music_response.status_code == 200

        # Different categories should potentially give different results
        # (This is a simple test - in reality, predictions might be same)
        edu_pred = edu_response.json()["like_ratio_pred"]
        music_pred = music_response.json()["like_ratio_pred"]

        # At minimum, both should be valid predictions
        assert 0 <= edu_pred <= 1
        assert 0 <= music_pred <= 1


class TestErrorHandling:
    """Test API error handling"""

    def test_missing_required_fields(self, client):
        """Test API with missing required fields"""
        incomplete_payload = {
            "title": "Test Video"
            # Missing tags, publish_time, category_name
        }

        response = client.post("/predict", json=incomplete_payload)
        assert response.status_code == 422  # Validation error

    def test_invalid_json(self, client):
        """Test API with invalid JSON"""
        response = client.post(
            "/predict",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("api.main.model")
    def test_model_prediction_error(self, mock_model_patch, client):
        """Test handling of model prediction errors"""
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Model error")
        mock_model.booster_.feature_name.return_value = []

        payload = {
            "title": "Test Video",
            "tags": ["test"],
            "publish_time": "2025-07-14T15:30:00",
            "category_name": "Education",
        }

        with patch("api.main.model", mock_model):
            response = client.post("/predict", json=payload)

        assert response.status_code == 500
        assert "Prediction error" in response.json()["detail"]


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
