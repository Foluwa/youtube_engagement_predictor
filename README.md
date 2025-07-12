# YouTube Engagement Predictor



                +----------------------------+
                |   Airflow or CLI Script    |
                |   (Training Pipeline)      |
                +----------------------------+
                           |
                           v
               +-------------------------+
               | YouTube Data API        |
               | (Fetch real videos)     |
               +-------------------------+
                           |
                           v
               +--------------------------+
               | Feature Engineering      |
               | (title, tags, duration)  |
               +--------------------------+
                           |
                           v
               +------------------------+
               | Model Training         |
               | (scikit-learn, LGBM)   |
               +------------------------+
                           |
                           v
               +--------------------------+
               | MLflow Model Registry    |
               +--------------------------+

                         ||  (serving)

                         \/

           +--------------------------------------+
           | FastAPI App (api/main.py)            |
           | Input: Raw metadata from any user    |
           | Output: Predicted views/like_ratio   |
           +--------------------------------------+
