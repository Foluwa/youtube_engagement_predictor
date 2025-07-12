from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pathlib
import joblib
import pandas as pd
import numpy as np
import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# Load model
MODEL_PATH = os.getenv("MODEL_PATH", str(pathlib.Path(__file__).parents[1] / "models" / "model.pkl"))
model = joblib.load(MODEL_PATH)

# YouTube API setup
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
if YT_API_KEY:
    yt = build("youtube", "v3", developerKey=YT_API_KEY)
else:
    yt = None

# Category mapping (you'll need to define this based on your model)
category_map = {'1': 'Film & Animation', '2': 'Autos & Vehicles', '10': 'Music', '15': 'Pets & Animals', '17': 'Sports', '18': 'Short Movies', '19': 'Travel & Events', '20': 'Gaming', '21': 'Videoblogging', '22': 'People & Blogs', '23': 'Comedy', '24': 'Entertainment', '25': 'News & Politics', '26': 'Howto & Style', '27': 'Education', '28': 'Science & Technology', '30': 'Movies', '31': 'Anime/Animation', '32': 'Action/Adventure', '33': 'Classics', '34': 'Comedy', '35': 'Documentary', '36': 'Drama', '37': 'Family', '38': 'Foreign', '39': 'Horror', '40': 'Sci-Fi/Fantasy', '41': 'Thriller', '42': 'Shorts', '43': 'Shows', '44': 'Trailers', '29': 'Nonprofits & Activism'}

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
    return {"status": "healthy", "model_loaded": model is not None}

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
    if not yt:
        raise HTTPException(status_code=500, detail="YouTube API not configured")
    
    try:
        # Fetch metadata
        resp = yt.videos().list(part="snippet,statistics,contentDetails", id=data.video_id).execute()
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
            "category_name": category_map.get(snip["categoryId"], "Unknown")
        }

        # Local predict reuse
        df = pd.DataFrame([{
            "title_len": len(payload["title"]),
            "tag_count": len(payload["tags"]),
            "hour": pd.to_datetime(payload["publish_time"]).hour,
            "weekday": pd.to_datetime(payload["publish_time"]).weekday()
        }])
        
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
            pass  # Transcript not available

        # Thumbnail
        thumb_url = snip.get("thumbnails", {}).get("medium", {}).get("url", "")

        return {
            "payload": payload,
            "predicted_like_percent": round(pred * 100, 2),
            "actual_like_percent": round(actual_ratio, 2),
            "thumbnail_url": thumb_url,
            "transcript": transcript[:10],  # first 10 segments
            "stats": {
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": int(stats.get("commentCount", 0))
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)