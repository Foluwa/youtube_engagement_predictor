import logging
import os
import pathlib

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import YouTube API components
try:
    from googleapiclient.discovery import build
    from youtube_transcript_api import YouTubeTranscriptApi

    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# Load model
MODEL_PATH = os.getenv(
    "MODEL_PATH", str(pathlib.Path(__file__).parents[1] / "models" / "model.pkl")
)
try:
    model = joblib.load(MODEL_PATH)
    logger.info(f"Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    logger.error(f"Failed to load model from {MODEL_PATH}: {e}")
    model = None

# YouTube API setup
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")

if YT_API_KEY and YOUTUBE_AVAILABLE:
    try:
        yt = build("youtube", "v3", developerKey=YT_API_KEY)
        logger.info("YouTube API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize YouTube API: {e}")
        yt = None
else:
    yt = None

# Category mapping
category_map = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "18": "Short Movies",
    "19": "Travel & Events",
    "20": "Gaming",
    "21": "Videoblogging",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "30": "Movies",
    "31": "Anime/Animation",
    "32": "Action/Adventure",
    "33": "Classics",
    "34": "Comedy",
    "35": "Documentary",
    "36": "Drama",
    "37": "Family",
    "38": "Foreign",
    "39": "Horror",
    "40": "Sci-Fi/Fantasy",
    "41": "Thriller",
    "42": "Shorts",
    "43": "Shows",
    "44": "Trailers",
    "29": "Nonprofits & Activism",
}


# Schema
class VideoMeta(BaseModel):
    title: str
    tags: list[str]
    publish_time: str
    category_name: str


class VideoID(BaseModel):
    video_id: str


app = FastAPI(title="YouTube Engagement Predictor")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "youtube_api_available": yt is not None,
        "youtube_api_key_configured": bool(YT_API_KEY),
    }


@app.post("/predict")
def predict(meta: VideoMeta):
    try:
        title_len = len(meta.title)
        tag_count = len(meta.tags)
        dt = pd.to_datetime(meta.publish_time)
        hour = dt.hour
        weekday = dt.weekday()

        data = {
            "title_len": [title_len],
            "tag_count": [tag_count],
            "hour": [hour],
            "weekday": [weekday],
        }
        df = pd.DataFrame(data)

        # Add one-hot for category_name
        for col in model.booster_.feature_name():
            if col.startswith("category_name_"):
                df[col] = 1 if col == f"category_name_{meta.category_name}" else 0

        # Predict
        pred = model.predict(df)[0]
        return {
            "like_ratio_pred": float(pred),
            "predicted_like_percent": round(pred * 100, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/fetch-and-predict")
def fetch_and_predict(data: VideoID):
    logger.info(f"Fetch-and-predict request for video_id: {data.video_id}")

    # If YouTube API is available and configured, use it
    if yt and YOUTUBE_AVAILABLE:
        try:
            return fetch_real_youtube_data(data)
        except Exception as e:
            logger.warning(f"YouTube API failed, falling back to demo: {e}")
            return create_demo_response(data.video_id)
    else:
        # Fall back to demo data instead of raising an error
        logger.info("YouTube API not configured, returning demo data")
        return create_demo_response(data.video_id)


def fetch_real_youtube_data(data: VideoID):
    """Fetch real data from YouTube API"""
    # Fetch metadata
    resp = (
        yt.videos()
        .list(part="snippet,statistics,contentDetails", id=data.video_id)
        .execute()
    )
    items = resp.get("items")
    if not items:
        raise HTTPException(status_code=404, detail="Video not found")

    info = items[0]
    snip = info["snippet"]
    stats = info["statistics"]

    # Build feature payload
    payload = {
        "title": snip["title"],
        "tags": snip.get("tags", []),
        "publish_time": snip["publishedAt"],
        "category_name": category_map.get(snip["categoryId"], "Unknown"),
    }

    # Local predict reuse
    df = pd.DataFrame(
        [
            {
                "title_len": len(payload["title"]),
                "tag_count": len(payload["tags"]),
                "hour": pd.to_datetime(payload["publish_time"]).hour,
                "weekday": pd.to_datetime(payload["publish_time"]).weekday(),
            }
        ]
    )

    # Add category features
    for feat in model.booster_.feature_name():
        if feat.startswith("category_name_"):
            cat = feat.replace("category_name_", "")
            df[feat] = int(payload["category_name"] == cat)

    pred = model.predict(df)[0]

    # Actual like percent
    like_count = int(stats.get("likeCount", 0))
    view_count = int(stats.get("viewCount", 1))
    actual_ratio = (like_count / view_count) * 100 if view_count > 0 else 0

    # Transcript (optional)
    transcript = []
    try:
        transcript = YouTubeTranscriptApi.get_transcript(data.video_id)
    except Exception:
        pass

    # Thumbnail
    thumb_url = snip.get("thumbnails", {}).get("medium", {}).get("url", "")

    return {
        "payload": payload,
        "predicted_like_percent": round(pred * 100, 2),
        "actual_like_percent": round(actual_ratio, 2),
        "thumbnail_url": thumb_url,
        "transcript": transcript[:10],
        "stats": {
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": int(stats.get("commentCount", 0)),
        },
    }


def create_demo_response(video_id: str):
    """Create a demo response when YouTube API is not available"""

    # Demo data based on popular video IDs
    demo_data = {
        "dQw4w9WgXcQ": {
            "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
            "tags": ["rick astley", "never gonna give you up", "music", "80s"],
            "category": "Music",
        },
        "9bZkp7q19f0": {
            "title": "PSY - GANGNAM STYLE(강남스타일) M/V",
            "tags": ["psy", "gangnam style", "kpop", "music"],
            "category": "Music",
        },
    }

    # Get demo data or create generic
    if video_id in demo_data:
        demo = demo_data[video_id]
        demo_title = demo["title"]
        demo_tags = demo["tags"]
        demo_category = demo["category"]
    else:
        demo_title = f"Demo Video - {video_id}"
        demo_tags = ["demo", "test", "youtube"]
        demo_category = "Entertainment"

    # Create prediction for demo data
    demo_payload = {
        "title": demo_title,
        "tags": demo_tags,
        "publish_time": "2025-07-15T12:00:00Z",
        "category_name": demo_category,
    }

    df = pd.DataFrame(
        [
            {
                "title_len": len(demo_payload["title"]),
                "tag_count": len(demo_payload["tags"]),
                "hour": 12,
                "weekday": 0,
            }
        ]
    )

    # Add category features
    for feat in model.booster_.feature_name():
        if feat.startswith("category_name_"):
            cat = feat.replace("category_name_", "")
            df[feat] = int(demo_payload["category_name"] == cat)

    pred = model.predict(df)[0]
    predicted_like_percent = round(pred * 100, 2)

    return {
        "payload": demo_payload,
        "predicted_like_percent": predicted_like_percent,
        "actual_like_percent": round(predicted_like_percent * 0.9, 2),
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        "transcript": [
            {"start": 0.0, "text": "This is demo data for testing"},
            {"start": 3.0, "text": "YouTube API key not configured"},
            {"start": 6.0, "text": "Add YOUTUBE_API_KEY to .env for real data"},
            {"start": 9.0, "text": "The prediction model is still working"},
            {"start": 12.0, "text": "Using simulated video metadata"},
        ],
        "stats": {
            "view_count": np.random.randint(100000, 10000000),
            "like_count": np.random.randint(1000, 500000),
            "comment_count": np.random.randint(100, 50000),
        },
        "demo_mode": True,
        "note": "This is demo data. Configure YOUTUBE_API_KEY in .env for real YouTube data.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
