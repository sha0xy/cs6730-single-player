"""Clean the Steam AI disclosure dataset (games released Jan 2024 to Nov 2026).

Usage: python3 scripts/clean_ai.py
Reads  data/raw/steam_games_ai_tagged.csv
Writes data/clean/steam_ai_clean.csv and data/clean/ai_cleanup_report.txt
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "steam_games_ai_tagged.csv"
OUT = ROOT / "data" / "clean"

report = []
def log(msg):
    print(msg)
    report.append(msg)

df = pd.read_csv(RAW, low_memory=False)
log(f"Raw games: {len(df):,}")

df = df.rename(columns={"appid": "app_id", "base_price_usd": "price",
                        "review_count": "total_reviews"})

# Dates.
df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce")
bad = df["release_date"].isna().sum()
df = df[df["release_date"].notna()]
log(f"Dates that could not be parsed (dropped): {bad:,}")

# Unreleased games: release date after the day the game was collected.
future = (df["release_date"] > df["collected_at"]).sum()
df = df[df["release_date"] <= df["collected_at"]]
log(f"Unreleased games dropped: {future:,}")

dupes = df["app_id"].duplicated().sum()
df = df.drop_duplicates("app_id")
log(f"Duplicate app IDs dropped: {dupes:,}")

# Missing prices.
noprice = df["price"].isna().sum()
log(f"Games with no price (kept, price blank): {noprice:,}")
df["is_free"] = (df["price"] == 0).where(df["price"].notna())

# Steam only shows a rating score at 10 or more reviews. Below that the score
# is stored as 0, so make it blank to leave it out of rating calculations.
no_score = df["review_desc"].str.contains("user review", na=False)
df["review_score"] = df["review_score"].where(~no_score)
log(f"Games with too few reviews for a Steam rating (score blank): {no_score.sum():,}")
df["has_reviews"] = df["total_reviews"] > 0
log(f"Games with zero reviews (kept): {(~df['has_reviews']).sum():,}")

# Tags use | as a separator. Switch to commas to match the main dataset.
df["tags"] = df["tags"].fillna("").str.replace("|", ",", regex=False)
df["has_tags"] = df["tags"] != ""
log(f"Games with no tags (kept, left out of tag analysis): {(~df['has_tags']).sum():,}")

df["release_year"] = df["release_date"].dt.year
df["ai_tags"] = df["ai_tags"].fillna("").str.replace("|", ",", regex=False)
log(f"Games with Steam AI disclosure: {df['has_ai_disclosure'].sum():,}")

cols = ["app_id", "name", "release_date", "release_year", "price", "is_free",
        "total_reviews", "has_reviews", "review_score", "review_desc", "tags",
        "has_tags", "has_ai_disclosure", "ai_tags", "ai_used", "ai_disclosure",
        "mature_content", "required_age", "collected_at"]
df = df[cols].sort_values(["release_date", "app_id"])
OUT.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT / "steam_ai_clean.csv", index=False)
log(f"Clean games written: {len(df):,} rows, {df.shape[1]} columns")
(OUT / "ai_cleanup_report.txt").write_text("\n".join(report) + "\n")
