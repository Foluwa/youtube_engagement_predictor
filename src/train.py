import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error
import joblib
import mlflow
import os

def train_model(data_path="./data/processed.csv", model_dir="models"):
    os.makedirs(model_dir, exist_ok=True)
    
    df = pd.read_csv(data_path)
    # Select features
    features = ["title_len", "tag_count", "hour", "weekday"]
    # One-hot encode category_name
    df = pd.get_dummies(df, columns=["category_name"], drop_first=True)
    features += [c for c in df.columns if c.startswith("category_name_")]

    X = df[features]
    y = df["like_ratio"]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Start MLflow run
    mlflow.set_experiment("yt_engagement_predictor")
    with mlflow.start_run():
        params = {
            "objective": "regression",
            "metric": "rmse",
            "random_state": 42,
            "num_leaves": 31,
            "learning_rate": 0.1,
            "n_estimators": 100,
        }
        mlflow.log_params(params)

        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=10)],
        )


        preds = model.predict(X_val)
        rmse = root_mean_squared_error(y_val, preds)
        mlflow.log_metric("rmse", rmse)

        # Log model
        model_path = os.path.join(model_dir, "model.pkl")
        joblib.dump(model, model_path)
        mlflow.log_artifact(model_path)

        print(f"Validation RMSE: {rmse:.5f}")

if __name__ == "__main__":
    train_model()
