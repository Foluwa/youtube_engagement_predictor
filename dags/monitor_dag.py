from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

import sys
sys.path.append("../src")
from monitor import run_monitoring, load_reference_data, load_current_data

default_args = {
    'owner': 'you',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='yt_engagement_monitoring',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
) as dag:

    monitor_task = PythonOperator(
        task_id='run_monitoring',
        python_callable=run_monitoring,
        op_kwargs={
            'reference': load_reference_data(),
            'current': load_current_data(),
            'model': None 
        },
    )
