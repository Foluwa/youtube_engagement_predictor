import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BACKEND_URL = "http://backend:80"

st.set_page_config(page_title="YouTube Engagement Predictor", layout="wide")
st.title("📊 YouTube Engagement Predictor")

mode = st.radio("Input Mode:", ("Manual Entry", "Fetch from YouTube"))

if "history" not in st.session_state:
    st.session_state.history = []


def process_prediction(payload, endpoint):
    r = requests.post(f"{BACKEND_URL}/{endpoint}", json=payload)
    r.raise_for_status()
    return r.json()


if mode == "Fetch from YouTube":
    video_url = st.text_input("🔗 YouTube URL")
    if st.button("Fetch & Predict"):
        try:
            video_id = video_url.split("v=")[-1].split("&")[0]
            res = process_prediction({"video_id": video_id}, "fetch-and-predict")

            st.video(video_url)
            st.image(
                res["thumbnail_url"], caption="Video Thumbnail", use_column_width=True
            )
            st.metric("🔮 Predicted Like %", f"{res['predicted_like_percent']}%")
            st.metric("✅ Actual Like %", f"{res['actual_like_percent']}%")

            st.subheader("📝 Transcript Preview")
            for seg in res.get("transcript", []):
                st.write(f"{seg['start']:.1f}s: {seg['text']}")

            st.session_state.history.append(
                {
                    "publish_time": res["payload"]["publish_time"],
                    "pred": res["predicted_like_percent"],
                    "actual": res["actual_like_percent"],
                    "error": res["predicted_like_percent"] - res["actual_like_percent"],
                    "title": res["payload"]["title"],
                }
            )
        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.header("Manual Input")
    title = st.text_input("🎬 Title")
    tags_input = st.text_input("🏷️ Tags (comma-separated)")
    publish_date = st.date_input("📅 Publish Date", value=datetime.date.today())
    publish_time = publish_date.isoformat() + "T00:00:00"
    category_name = st.text_input("📚 Category")

    if st.button("Predict"):
        try:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            payload = {
                "title": title,
                "tags": tags,
                "publish_time": publish_time,
                "category_name": category_name,
            }
            res = process_prediction(payload, "predict")

            st.metric("🔮 Predicted Like %", f"{res['predicted_like_percent']}%")
            st.json(res)

            st.session_state.history.append(
                {
                    "publish_time": publish_time,
                    "pred": res["predicted_like_percent"],
                    "actual": None,
                    "error": None,
                    "title": title,
                }
            )
        except Exception as e:
            st.error(f"Error: {e}")

if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    df["publish_time"] = pd.to_datetime(df["publish_time"])

    st.subheader("📈 Performance Over Time")
    fig_time = px.line(
        df,
        x="publish_time",
        y=["pred", "actual"],
        labels={"value": "Like %", "variable": "Metric"},
    )
    st.plotly_chart(fig_time, use_container_width=True)

    st.subheader("📊 Error Distribution")
    df_err = df.dropna(subset=["error"])
    fig_hist = px.histogram(
        df_err, x="error", nbins=20, labels={"error": "Prediction Error (%)"}
    )
    st.plotly_chart(fig_hist, use_container_width=True)
