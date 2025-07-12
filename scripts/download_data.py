from dotenv import load_dotenv
import os

load_dotenv()

os.environ["KAGGLE_USERNAME"] = os.getenv("KAGGLE_USERNAME")
os.environ["KAGGLE_KEY"] = os.getenv("KAGGLE_KEY")

from kaggle.api.kaggle_api_extended import KaggleApi

def download_data():
    api = KaggleApi()
    api.authenticate()
    os.makedirs("data", exist_ok=True)
    api.dataset_download_files("datasnaek/youtube-new", path="data", unzip=True)
    print("🔽 Dataset downloaded to 'data/'")

if __name__ == "__main__":
    download_data()
