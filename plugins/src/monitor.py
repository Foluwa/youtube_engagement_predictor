import os

import joblib
import numpy as np
import pandas as pd
import requests
from evidently import Report
from evidently.presets import DataDriftPreset, RegressionPreset
from sklearn.metrics import mean_squared_error

# --- Telegram Setup ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ALERT_THRESHOLD = float(os.getenv("RMSE_ALERT_THRESHOLD", "0.04"))


def send_telegram_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token or chat ID not set—skipping alert.")
        return
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        f"/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={requests.utils.quote(text)}"
    )
    resp = requests.get(url, timeout=10)
    print("Telegram response:", resp.status_code, resp.text)


# --- Monitoring Pipeline (same as before) ---
def load_reference_data(path="data/processed.csv"):
    df = pd.read_csv(path)
    return df.sample(20000, random_state=42)


def load_current_data(path="data/processed.csv", days=7):
    df = pd.read_csv(path)
    df["trending_date"] = pd.to_datetime(
        df["trending_date"], format="%y.%d.%m", errors="coerce"
    )
    cutoff = df["trending_date"].max() - pd.Timedelta(days=days)
    return df[df["trending_date"] >= cutoff]


def prepare_features(df, feature_names):
    X = pd.DataFrame(
        {
            "title_len": df["title_len"],
            "tag_count": df["tag_count"],
            "hour": df["hour"],
            "weekday": df["weekday"],
        }
    )
    for feat in feature_names:
        if feat.startswith("category_name_"):
            category = feat.replace("category_name_", "")
            X[feat] = (df["category_name"] == category).astype(int)
    return X[feature_names]


def run_monitoring(reference, current, model):
    feature_names = model.booster_.feature_name()
    ref_X = prepare_features(reference, feature_names)
    curr_X = prepare_features(current, feature_names)

    ref_preds = model.predict(ref_X)
    curr_preds = model.predict(curr_X)

    rmse = np.sqrt(mean_squared_error(current["like_ratio"], curr_preds))

    # Build Evidently report
    ref_df = ref_X.copy()
    ref_df["target"], ref_df["prediction"] = (
        reference["like_ratio"].values[: len(ref_df)],
        ref_preds,
    )
    curr_df = curr_X.copy()
    curr_df["target"], curr_df["prediction"] = (
        current["like_ratio"].values[: len(curr_df)],
        curr_preds,
    )

    report = Report(metrics=[DataDriftPreset(), RegressionPreset()])
    report.run(reference_data=ref_df, current_data=curr_df)

    os.makedirs("monitoring", exist_ok=True)
    report.save_html("monitoring/drift_report.html")
    print("Drift report saved to monitoring/drift_report.html")
    print(f"Current RMSE: {rmse:.5f}")

    # --- Send alert if RMSE exceeds threshold ---
    if rmse > ALERT_THRESHOLD:
        msg = (
            f"⚠️ ALERT: Model RMSE has increased to {rmse:.5f}, "
            f"which is above your threshold of {ALERT_THRESHOLD:.5f}."
        )
        send_telegram_message(msg)
        print("✅ Telegram alert sent.")
    else:
        print("✅ RMSE is within acceptable bounds.")


if __name__ == "__main__":
    reference = load_reference_data()
    current = load_current_data()
    model = joblib.load(os.getenv("MODEL_PATH", "models/model.pkl"))
    run_monitoring(reference, current, model)
