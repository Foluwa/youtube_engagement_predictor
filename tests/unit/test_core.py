import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from plugins.src.monitor import prepare_features, send_telegram_message
from plugins.src.preprocess import engineer_features, load_and_combine_csvs

# Import your modules
from plugins.src.train import train_model


class TestDataProcessing:
    def test_load_and_combine_csvs(self):
        """Test CSV loading functionality"""
        # Create sample data
        sample_data = pd.DataFrame(
            {
                "title": ["Test Video 1", "Test Video 2"],
                "views": [1000, 2000],
                "likes": [50, 100],
            }
        )

        with patch("glob.glob") as mock_glob, patch("pandas.read_csv") as mock_read_csv:

            mock_glob.return_value = ["test1.csv", "test2.csv"]
            mock_read_csv.return_value = sample_data

            result = load_and_combine_csvs("test_dir")

            assert len(result) == 4  # 2 files * 2 rows each
            assert "title" in result.columns

    def test_engineer_features(self):
        """Test feature engineering"""
        # Sample input data
        data = pd.DataFrame(
            {
                "Title": ["Test Video"],
                "Category ID": ["10"],
                "Tags": ["tag1|tag2|tag3"],
                "Publish Time": ["2023-01-01T10:30:00Z"],
                "Views": [1000],
                "Likes": [50],
            }
        )

        category_map = {"10": "Music"}
        result = engineer_features(data, category_map)

        assert "title_len" in result.columns
        assert "tag_count" in result.columns
        assert "like_ratio" in result.columns
        assert result["title_len"].iloc[0] == len("Test Video")
        assert result["tag_count"].iloc[0] == 3


class TestModelTraining:
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

        # Create mock data with the original category_name column
        data = {
            "title_len": [10, 15, 8, 12],
            "tag_count": [3, 2, 1, 4],
            "hour": [10, 14, 8, 16],
            "weekday": [1, 2, 3, 4],
            "category_name": [
                "Music",
                "Education",
                "Music",
                "Education",
            ],  # Original column
            "like_ratio": [0.05, 0.08, 0.03, 0.07],
        }
        mock_df = pd.DataFrame(data)

        # Mock the context manager for mlflow.start_run()
        mock_context = MagicMock()
        mock_run.return_value.__enter__ = Mock(return_value=mock_context)
        mock_run.return_value.__exit__ = Mock(return_value=False)

        with patch("pandas.read_csv", return_value=mock_df):
            # Run training
            train_model("fake_path.csv", "fake_model_dir")

            # Verify calls
            mock_makedirs.assert_called_once()
            mock_experiment.assert_called_once()
            mock_params.assert_called_once()
            mock_metric.assert_called_once()
            mock_artifact.assert_called_once()
            mock_dump.assert_called_once()


class TestMonitoring:
    def test_prepare_features(self):
        """Test feature preparation for monitoring"""
        # Sample data
        df = pd.DataFrame(
            {
                "title_len": [10, 15],
                "tag_count": [3, 2],
                "hour": [10, 14],
                "weekday": [1, 2],
                "category_name": ["Music", "Education"],
            }
        )

        feature_names = [
            "title_len",
            "tag_count",
            "hour",
            "weekday",
            "category_name_Music",
        ]
        result = prepare_features(df, feature_names)

        assert len(result.columns) == len(feature_names)
        assert "category_name_Music" in result.columns

    @patch.dict(os.environ, {}, clear=True)  # Clear environment
    def test_send_telegram_message_no_config(self):
        """Test Telegram message with no configuration"""
        # This should not raise an exception and should skip sending
        send_telegram_message("Test message")
        # If we get here without exception, the test passes

    @patch("requests.get")
    @patch("plugins.src.monitor.TELEGRAM_TOKEN", "test_token")
    @patch("plugins.src.monitor.TELEGRAM_CHAT_ID", "test_chat_id")
    def test_send_telegram_message_success(self, mock_get):
        """Test successful Telegram message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"ok": true}'
        mock_get.return_value = mock_response

        # Should not raise an exception
        send_telegram_message("Test message")
        mock_get.assert_called_once()

    @patch("requests.get")
    @patch("plugins.src.monitor.TELEGRAM_TOKEN", "test_token")
    @patch("plugins.src.monitor.TELEGRAM_CHAT_ID", "test_chat_id")
    def test_send_telegram_message_failure(self, mock_get):
        """Test Telegram message sending failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"ok": false}'
        mock_get.return_value = mock_response

        # Should not raise an exception even on HTTP error
        send_telegram_message("Test message")
        mock_get.assert_called_once()


class TestAPIEndpoints:
    def test_video_meta_schema(self):
        """Test VideoMeta Pydantic model"""
        from api.main import VideoMeta

        data = {
            "title": "Test Video",
            "tags": ["tag1", "tag2"],
            "publish_time": "2023-01-01T10:00:00",
            "category_name": "Education",
        }

        video_meta = VideoMeta(**data)
        assert video_meta.title == "Test Video"
        assert len(video_meta.tags) == 2
        assert video_meta.category_name == "Education"
