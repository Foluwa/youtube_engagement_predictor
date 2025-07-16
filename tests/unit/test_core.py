import os
import sys
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from plugins.src.monitor import prepare_features, send_telegram_message
from plugins.src.preprocess import engineer_features, load_category_map
from plugins.src.train import train_model

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestPreprocessing:
    """Test data preprocessing functionality"""

    def test_engineer_features(self):
        """Test feature engineering with sample data"""
        # Sample data
        data = {
            "title": ["Amazing Video Title", "Short"],
            "tags": ["tag1|tag2|tag3", "single"],
            "publish_time": ["2025-07-14 10:30:00", "2025-07-14 15:45:00"],
            "category_id": ["10", "15"],
            "views": [1000, 2000],
            "likes": [100, 150],
        }
        df = pd.DataFrame(data)

        category_map = {"10": "Music", "15": "Pets & Animals"}

        result = engineer_features(df, category_map)

        # Check new columns exist
        assert "title_len" in result.columns
        assert "tag_count" in result.columns
        assert "hour" in result.columns
        assert "weekday" in result.columns
        assert "like_ratio" in result.columns
        assert "category_name" in result.columns

        # Check values
        assert result["title_len"].iloc[0] == len("Amazing Video Title")
        assert result["tag_count"].iloc[0] == 3  # tag1|tag2|tag3
        assert result["tag_count"].iloc[1] == 1  # single
        assert result["hour"].iloc[0] == 10
        assert result["hour"].iloc[1] == 15
        assert result["like_ratio"].iloc[0] == 0.1  # 100/1000
        assert result["category_name"].iloc[0] == "Music"

    def test_load_category_map(self):
        """Test category map loading with mock JSON data"""
        mock_json_data = {
            "items": [
                {"id": "10", "snippet": {"title": "Music"}},
                {"id": "15", "snippet": {"title": "Pets & Animals"}},
            ]
        }

        with patch("glob.glob", return_value=["test_category_id.json"]):
            with patch("json.load", return_value=mock_json_data):
                with patch("builtins.open", MagicMock()):
                    result = load_category_map("test_dir")

        expected = {"10": "Music", "15": "Pets & Animals"}
        assert result == expected


class TestModelTraining:
    """Test model training functionality"""

    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metric")
    @patch("mlflow.log_artifact")
    @patch("mlflow.set_experiment")
    @patch("os.makedirs")
    @patch("joblib.dump")
    def test_train_model(
        self,
        mock_dump,
        mock_makedirs,
        mock_experiment,
        mock_artifact,
        mock_metric,
        mock_params,
        mock_run,
    ):
        """Test model training with mock data"""

        # Create mock data
        data = {
            "title_len": [10, 15, 8, 12],
            "tag_count": [3, 2, 1, 4],
            "hour": [10, 14, 8, 16],
            "weekday": [1, 2, 3, 4],
            "category_name_Music": [1, 0, 1, 0],
            "category_name_Education": [0, 1, 0, 1],
            "like_ratio": [0.05, 0.08, 0.03, 0.07],
        }
        mock_df = pd.DataFrame(data)

        with patch("pandas.read_csv", return_value=mock_df):
            # Run training
            train_model("fake_path.csv", "fake_model_dir")

        # Verify MLflow calls
        mock_experiment.assert_called_once()
        mock_run.assert_called_once()
        mock_params.assert_called_once()
        mock_metric.assert_called_once()
        mock_dump.assert_called_once()


class TestMonitoring:
    """Test monitoring functionality"""

    def test_prepare_features(self):
        """Test feature preparation for monitoring"""
        # Sample data
        data = {
            "title_len": [10, 15],
            "tag_count": [3, 2],
            "hour": [10, 14],
            "weekday": [1, 2],
            "category_name": ["Music", "Education"],
        }
        df = pd.DataFrame(data)

        feature_names = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Music",
            "category_name_Education",
        ]

        result = prepare_features(df, feature_names)

        # Check shape and columns
        assert result.shape[0] == 2
        assert list(result.columns) == feature_names

        # Check one-hot encoding
        assert result["category_name_Music"].iloc[0] == 1
        assert result["category_name_Music"].iloc[1] == 0
        assert result["category_name_Education"].iloc[0] == 0
        assert result["category_name_Education"].iloc[1] == 1

    @patch("requests.get")
    def test_send_telegram_message_success(self, mock_get):
        """Test successful Telegram message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"ok": true}'
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {"TELEGRAM_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat_id"},
        ):
            # Should not raise an exception
            send_telegram_message("Test message")
            mock_get.assert_called_once()

    def test_send_telegram_message_no_config(self):
        """Test Telegram message with missing configuration"""
        with patch.dict(os.environ, {}, clear=True):
            # Should handle missing config gracefully
            send_telegram_message("Test message")
            # No exception should be raised


class TestUtilities:
    """Test utility functions"""

    def test_feature_consistency(self):
        """Test that features are consistent across preprocessing and monitoring"""
        # This ensures the same features are used in training and serving
        from plugins.src.monitor import prepare_features
        from plugins.src.preprocess import engineer_features

        # Sample data for preprocessing
        prep_data = {
            "title": ["Test Video"],
            "tags": ["tag1|tag2"],
            "publish_time": ["2025-07-14 10:00:00"],
            "category_id": ["10"],
            "views": [1000],
            "likes": [50],
        }
        prep_df = pd.DataFrame(prep_data)
        category_map = {"10": "Music"}

        processed = engineer_features(prep_df, category_map)

        # Sample data for monitoring (similar structure)
        monitor_data = {
            "title_len": [processed["title_len"].iloc[0]],
            "tag_count": [processed["tag_count"].iloc[0]],
            "hour": [processed["hour"].iloc[0]],
            "weekday": [processed["weekday"].iloc[0]],
            "category_name": [processed["category_name"].iloc[0]],
        }
        monitor_df = pd.DataFrame(monitor_data)

        # Mock feature names (simulating model features)
        feature_names = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Music",
        ]

        monitored = prepare_features(monitor_df, feature_names)

        # Verify feature alignment
        assert monitored["title_len"].iloc[0] == processed["title_len"].iloc[0]
        assert monitored["tag_count"].iloc[0] == processed["tag_count"].iloc[0]
        assert monitored["hour"].iloc[0] == processed["hour"].iloc[0]


# Fixtures for testing
@pytest.fixture
def sample_dataframe():
    """Fixture providing sample YouTube data"""
    return pd.DataFrame(
        {
            "title": ["Amazing Tutorial", "Quick Tips", "Deep Dive Analysis"],
            "tags": ["tutorial|python|coding", "tips|quick", "analysis|data|science"],
            "publish_time": [
                "2025-07-14 10:00:00",
                "2025-07-14 14:30:00",
                "2025-07-14 18:15:00",
            ],
            "category_id": ["27", "27", "28"],
            "views": [10000, 5000, 15000],
            "likes": [800, 300, 1200],
        }
    )


@pytest.fixture
def sample_category_map():
    """Fixture providing sample category mapping"""
    return {"27": "Education", "28": "Science & Technology"}


@pytest.fixture
def mock_model():
    """Fixture providing a mock ML model"""
    model = Mock()
    model.predict.return_value = np.array([0.05, 0.08, 0.06])
    model.booster_.feature_name.return_value = [
        "title_len",
        "tag_count",
        "hour",
        "weekday",
        "category_name_Education",
        "category_name_Science & Technology",
    ]
    return model
