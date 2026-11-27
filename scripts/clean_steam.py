"""Clean the FronkonGames Steam CSV (main dataset).

Usage: python3 scripts/clean_steam.py
Reads  data/raw/games.csv
Writes data/clean/steam_games_clean.csv and data/clean/cleanup_report.txt
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "games.csv"
OUT = ROOT / "data" / "clean"
TODAY = pd.Timestamp("2026-11-26")  # snapshot cutoff: later dates are unreleased

report = []
def log(msg):
    print(msg)
    report.append(msg)

# 1. Read the raw CSV. The header merges "Discount" and "DLC count" into one
#    name, so the data has one more column than the header. Split it.
header = pd.read_csv(RAW, nrows=0).columns.tolist()
i = header.index("DiscountDLC count")
names = header[:i] + ["Discount", "DLC count"] + header[i + 1:]
df = pd.read_csv(RAW, header=None, skiprows=1, names=names, low_memory=False)
log(f"Raw games: {len(df):,}")

# 2. Keep only the columns used in the analysis (drops long text columns).
keep = {
    "AppID": "app_id", "Name": "name", "Release date": "release_date",
    "Price": "price", "Positive": "positive", "Negative": "negative",
    "Estimated owners": "estimated_owners", "Peak CCU": "peak_ccu",
    "Median playtime forever": "median_playtime_min",
    "Developers": "developers", "Publishers": "publishers",
    "Genres": "genres", "Categories": "categories", "Tags": "tags",
}
df = df[list(keep)].rename(columns=keep)

# 3. Turn text dates like "Jul 29, 2016" into real dates.
df["release_date"] = pd.to_datetime(df["release_date"], format="mixed", errors="coerce")
bad = df["release_date"].isna().sum()
log(f"Dates that could not be parsed (dropped): {bad:,}")
df = df[df["release_date"].notna()]

# 4. Drop games that are not released yet.
future = (df["release_date"] > TODAY).sum()
df = df[df["release_date"] <= TODAY]
log(f"Unreleased games dropped (after {TODAY.date()}): {future:,}")

# 5. Drop exact duplicate app IDs, if any.
dupes = df["app_id"].duplicated().sum()
df = df.drop_duplicates("app_id")
log(f"Duplicate app IDs dropped: {dupes:,}")

# 6. Created columns.
df["release_year"] = df["release_date"].dt.year
df["total_reviews"] = df["positive"] + df["negative"]
# Blank for zero-review games so they are left out of rating calculations.
df["positive_share"] = (df["positive"] / df["total_reviews"]).where(df["total_reviews"] > 0)
df["is_free"] = df["price"] == 0

# 7. List columns: fill blanks, add flags. Untagged games stay in the file
#    and are left out of the tag analysis using has_tags.
for c in ["tags", "genres", "categories", "developers", "publishers"]:
    df[c] = df[c].fillna("").astype(str).str.strip()
df["has_tags"] = df["tags"] != ""
df["has_reviews"] = df["total_reviews"] > 0
log(f"Games with zero reviews (kept, no positive_share): {(~df['has_reviews']).sum():,}")
log(f"Games with no tags (kept, left out of tag analysis): {(~df['has_tags']).sum():,}")

# 8. Make publisher and developer names consistent. Names that differ only in
#    spacing or capitals become the most common spelling.
def normalize_names(col):
    def split(s):
        return [re.sub(r"\s+", " ", p).strip() for p in s.split(",") if p.strip()]
    lists = df[col].map(split)
    counts = pd.Series([n for l in lists for n in l]).value_counts()
    # Most common spelling wins. Ties go to the alphabetically first spelling,
    # so the result is the same on every machine.
    order = sorted(counts.index, key=lambda n: (-counts[n], n))
    canon = {}
    for name in order:
        canon.setdefault(name.casefold(), name)
    changed = sum(1 for n in counts.index if canon[n.casefold()] != n)
    df[col] = lists.map(lambda l: ",".join(dict.fromkeys(canon[n.casefold()] for n in l)))
    log(f"{col}: {changed:,} spelling variants merged")
normalize_names("publishers")
normalize_names("developers")

df = df.sort_values(["release_date", "app_id"])
OUT.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT / "steam_games_clean.csv", index=False)
log(f"Clean games written: {len(df):,} rows, {df.shape[1]} columns")
(OUT / "cleanup_report.txt").write_text("\n".join(report) + "\n")
