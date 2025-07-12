from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'you',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

with DAG('yt_engagement_retrain',
         default_args=default_args,
         schedule='@weekly',
         catchup=False,
         params={'trigger_retrain': False},
         render_template_as_native_obj=True) as dag:

    check_trigger = PythonOperator(
        task_id='check_trigger',
        python_callable=lambda params: params['trigger_retrain'],
        op_kwargs={'params': "{{ params }}"},
    )

    retrain = TriggerDagRunOperator(
        task_id='trigger_train_dag',
        trigger_dag_id='yt_engagement_train',
        wait_for_completion=True,
    )

    check_trigger >> retrain
