import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

BACKEND_URL = "http://backend:80"

st.set_page_config(page_title="YouTube Engagement Predictor", layout="wide")
st.title("📊 YouTube Engagement Predictor")

mode = st.radio("Input Mode:", ("Manual Entry", "Fetch from YouTube"))

if "history" not in st.session_state:
    st.session_state.history = []


def process_prediction(payload, endpoint):
    try:
        r = requests.post(f"{BACKEND_URL}/{endpoint}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        return None


if mode == "Fetch from YouTube":
    video_url = st.text_input("🔗 YouTube URL")
    if st.button("Fetch & Predict"):
        if not video_url:
            st.error("Please enter a YouTube URL")
        else:
            try:
                # Extract video ID from URL
                if "v=" in video_url:
                    video_id = video_url.split("v=")[-1].split("&")[0]
                elif "youtu.be/" in video_url:
                    video_id = video_url.split("youtu.be/")[-1].split("?")[0]
                else:
                    st.error("Invalid YouTube URL format")
                    video_id = None

                if video_id:
                    res = process_prediction(
                        {"video_id": video_id}, "fetch-and-predict"
                    )

                    if res:
                        # Display video
                        st.video(video_url)

                        # Display thumbnail if available
                        if res.get("thumbnail_url"):
                            st.image(
                                res["thumbnail_url"],
                                caption="Video Thumbnail",
                                use_column_width=True,
                            )

                        # Display metrics
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "🔮 Predicted Like %",
                                f"{res['predicted_like_percent']}%",
                            )
                        with col2:
                            st.metric(
                                "✅ Actual Like %", f"{res['actual_like_percent']}%"
                            )

                        # Display error/accuracy
                        error = abs(
                            res["predicted_like_percent"] - res["actual_like_percent"]
                        )
                        st.metric("📊 Prediction Error", f"{error:.2f}%")

                        # Display transcript preview
                        if res.get("transcript"):
                            st.subheader("📝 Transcript Preview")
                            for seg in res.get("transcript", []):
                                st.write(
                                    f"{seg.get('start', 0):.1f}s: {seg.get('text', '')}"
                                )

                        # Add to history
                        st.session_state.history.append(
                            {
                                "publish_time": res["payload"]["publish_time"],
                                "pred": float(res["predicted_like_percent"]),
                                "actual": float(res["actual_like_percent"]),
                                "error": float(
                                    res["predicted_like_percent"]
                                    - res["actual_like_percent"]
                                ),
                                "title": res["payload"]["title"],
                            }
                        )

            except Exception as e:
                st.error(f"Error processing video: {e}")

else:
    st.header("Manual Input")

    with st.form("prediction_form"):
        title = st.text_input("🎬 Title")
        tags_input = st.text_input("🏷️ Tags (comma-separated)")
        publish_date = st.date_input("📅 Publish Date", value=datetime.date.today())
        publish_time_input = st.time_input(
            "🕒 Publish Time", value=datetime.time(12, 0)
        )
        category_name = st.selectbox(
            "📚 Category",
            [
                "Education",
                "Entertainment",
                "Music",
                "Gaming",
                "Science & Technology",
                "News & Politics",
                "Sports",
                "Comedy",
                "Film & Animation",
                "People & Blogs",
                "Howto & Style",
                "Travel & Events",
                "Pets & Animals",
                "Autos & Vehicles",
            ],
        )

        submitted = st.form_submit_button("Predict")

        if submitted:
            if not title:
                st.error("Please enter a title")
            else:
                try:
                    # Combine date and time
                    publish_datetime = datetime.datetime.combine(
                        publish_date, publish_time_input
                    )
                    publish_time = publish_datetime.isoformat()

                    tags = (
                        [t.strip() for t in tags_input.split(",") if t.strip()]
                        if tags_input
                        else []
                    )
                    payload = {
                        "title": title,
                        "tags": tags,
                        "publish_time": publish_time,
                        "category_name": category_name,
                    }

                    res = process_prediction(payload, "predict")

                    if res:
                        st.success("Prediction completed!")
                        st.metric(
                            "🔮 Predicted Like %", f"{res['predicted_like_percent']}%"
                        )

                        # Show detailed results
                        with st.expander("Detailed Results"):
                            st.json(res)

                        # Add to history
                        st.session_state.history.append(
                            {
                                "publish_time": publish_time,
                                "pred": float(res["predicted_like_percent"]),
                                "actual": None,
                                "error": None,
                                "title": title,
                            }
                        )

                except Exception as e:
                    st.error(f"Error making prediction: {e}")

# Display history and analytics
if st.session_state.history:
    st.header("📈 Analytics Dashboard")

    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.history)
    df["publish_time"] = pd.to_datetime(df["publish_time"])

    # Ensure numeric columns
    df["pred"] = pd.to_numeric(df["pred"], errors="coerce")
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")

    # Display summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Predictions", len(df))
    with col2:
        avg_pred = df["pred"].mean()
        st.metric("Avg Predicted Like %", f"{avg_pred:.2f}%")
    with col3:
        if df["actual"].notna().any():
            avg_actual = df["actual"].mean()
            st.metric("Avg Actual Like %", f"{avg_actual:.2f}%")

    # Performance over time chart
    st.subheader("📈 Performance Over Time")

    # Create separate traces for better control
    fig_time = go.Figure()

    # Add prediction line
    fig_time.add_trace(
        go.Scatter(
            x=df["publish_time"],
            y=df["pred"],
            mode="lines+markers",
            name="Predicted",
            line=dict(color="blue"),
            hovertemplate="%{y:.2f}%<extra></extra>",
        )
    )

    # Add actual line only for non-null values
    actual_data = df[df["actual"].notna()]
    if not actual_data.empty:
        fig_time.add_trace(
            go.Scatter(
                x=actual_data["publish_time"],
                y=actual_data["actual"],
                mode="lines+markers",
                name="Actual",
                line=dict(color="red"),
                hovertemplate="%{y:.2f}%<extra></extra>",
            )
        )

    fig_time.update_layout(
        title="Predicted vs Actual Like Percentages",
        xaxis_title="Publish Time",
        yaxis_title="Like %",
        hovermode="x unified",
    )

    st.plotly_chart(fig_time, use_container_width=True)

    # Error distribution (only for entries with actual values)
    error_data = df[df["error"].notna()]
    if not error_data.empty:
        st.subheader("📊 Prediction Error Distribution")
        fig_hist = px.histogram(
            error_data,
            x="error",
            nbins=20,
            title="Distribution of Prediction Errors",
            labels={"error": "Prediction Error (%)", "count": "Frequency"},
        )
        fig_hist.update_layout(
            xaxis_title="Prediction Error (%)", yaxis_title="Frequency"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Error statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            mae = error_data["error"].abs().mean()
            st.metric("Mean Absolute Error", f"{mae:.2f}%")
        with col2:
            rmse = (error_data["error"] ** 2).mean() ** 0.5
            st.metric("RMSE", f"{rmse:.2f}%")
        with col3:
            accuracy = (error_data["error"].abs() < 1.0).mean() * 100
            st.metric("±1% Accuracy", f"{accuracy:.1f}%")

    # Recent predictions table
    st.subheader("📋 Recent Predictions")
    display_df = df.copy()
    display_df["publish_time"] = display_df["publish_time"].dt.strftime(
        "%Y-%m-%d %H:%M"
    )
    display_df = display_df[["title", "pred", "actual", "error", "publish_time"]].round(
        2
    )
    display_df.columns = ["Title", "Predicted %", "Actual %", "Error %", "Publish Time"]
    st.dataframe(display_df.tail(10), use_container_width=True)

    # Clear history button
    if st.button("🗑️ Clear History"):
        st.session_state.history = []
        st.rerun()

# Sidebar with app info
with st.sidebar:
    st.header("ℹ️ About")
    st.write(
        """
    This app predicts YouTube video engagement rates based on metadata like:
    - Video title
    - Tags
    - Publishing time
    - Category

    The prediction model uses LightGBM trained on YouTube trending data.
    """
    )

    st.header("🔗 API Endpoints")
    st.code(f"{BACKEND_URL}/docs", language="text")

    # Backend health check
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if health.status_code == 200:
            st.success("✅ Backend is healthy")
        else:
            st.error("❌ Backend is unhealthy")
    except:
        st.error("❌ Cannot connect to backend")
