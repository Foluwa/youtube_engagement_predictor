import glob
import json

import pandas as pd


def load_and_combine_csvs(data_dir="data"):
    paths = glob.glob(f"{data_dir}/*videos.csv")
    dfs = []
    for p in paths:
        try:
            df = pd.read_csv(p, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding="latin1", engine="python")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def load_category_map(data_dir="data"):
    category_map = {}
    for path in glob.glob(f"{data_dir}/*_category_id.json"):
        j = json.load(open(path))
        for item in j["items"]:
            category_map[item["id"]] = item["snippet"]["title"]
    return category_map


def engineer_features(df, category_map):
    # Clean column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    # Map categories
    df["category_name"] = df["category_id"].astype(str).map(category_map)

    # Feature engineering
    df["title_len"] = df["title"].astype(str).str.len()
    df["tag_count"] = df["tags"].astype(str).apply(lambda t: len(t.split("|")))
    df["publish_time"] = pd.to_datetime(df["publish_time"])
    df["hour"] = df["publish_time"].dt.hour
    df["weekday"] = df["publish_time"].dt.weekday

    # Engagement target
    df = df[df["views"] > 0]
    df["like_ratio"] = df["likes"] / df["views"]

    return df


def preprocess(data_dir="data", out_path="data/processed.csv"):
    print("Loading CSVs...")
    df = load_and_combine_csvs(data_dir)
    print(f"Loaded {len(df)} rows")

    print("Loading category mappings...")
    cat_map = load_category_map(data_dir)

    print("Engineering features...")
    df2 = engineer_features(df, cat_map)

    print(f"Saving processed data to {out_path}...")
    df2.to_csv(out_path, index=False)
    print("Done.")


if __name__ == "__main__":
    preprocess()
