import os
from datetime import datetime, timedelta

import joblib
from airflow.operators.python import PythonOperator
from src.monitor import load_current_data, load_reference_data, run_monitoring

from airflow import DAG

default_args = {
    "owner": "you",
    "depends_on_past": False,
    "start_date": datetime(2025, 7, 13),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "yt_engagement_monitoring",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
) as dag:

    def monitor_wrapper():
        run_monitoring(
            reference=load_reference_data(),
            current=load_current_data(),
            model=joblib.load(os.getenv("MODEL_PATH", "models/model.pkl")),
        )

    monitor_task = PythonOperator(
        task_id="run_monitoring",
        python_callable=monitor_wrapper,
    )
