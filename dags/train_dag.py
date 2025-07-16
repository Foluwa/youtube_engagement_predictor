import os
from datetime import datetime, timedelta

from airflow.decorators import task
from src.preprocess import preprocess
from src.train import train_model

from airflow import DAG

default_args = {
    "owner": "you",
    "start_date": datetime(2025, 7, 13),
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    "yt_engagement_train", default_args=default_args, schedule=None, catchup=False
) as dag:

    @task
    def preprocess_task():
        return preprocess("data/raw", "data/processed.csv")

    @task
    def train(processed_path: str):
        return train_model(processed_path, os.getenv("MODEL_PATH"))

    train(preprocess_task())
