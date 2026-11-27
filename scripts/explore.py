"""Exploration charts for the process book (section 2.6).

Usage: python3 scripts/explore.py
Reads  data/clean/steam_games_clean.csv and data/clean/steam_ai_clean.csv
Writes exploration/*.png and exploration/numbers.txt

These are rough charts for exploring the questions, not final designs.
Attention is measured by total reviews. Medians are used because review
counts are very skewed.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from adjustText import adjust_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "exploration"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE, GRAY, INK, INK2 = "#257de0", "#f47230", "#b5b5b5", "#191919", "#666666"
plt.rcParams.update({
    "figure.dpi": 150, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.edgecolor": "#cccccc", "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#ececec", "grid.linewidth": 0.6,
    "axes.axisbelow": True, "text.color": INK,
})

numbers = []
def note(msg):
    numbers.append(msg)

def save(fig, name, source):
    fig.text(0.01, 0.005, source, fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)

SUFFIXES = {"inc", "inc.", "ltd", "ltd.", "llc", "llc.", "co.", "co", "corp", "corp.",
            "s.a.", "s.l.", "gmbh", "pty", "pty.", "plc", "l.l.c.", "co., ltd."}

def split_names(s):
    """Split a comma list, keeping company suffixes like ', Inc.' with the name."""
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if out and part.casefold() in SUFFIXES:
            out[-1] = f"{out[-1]}, {part}"
        else:
            out.append(part)
    return out

def explode(df, col):
    s = df[col].fillna("").astype(str)
    out = df.assign(**{col: s.map(split_names)}).explode(col)
    return out[out[col].notna() & (out[col] != "")]

def label_points(ax, xs, ys, names):
    texts = [ax.text(x, y, n, fontsize=7, color=INK2) for x, y, n in zip(xs, ys, names)]
    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.5))

g = pd.read_csv(ROOT / "data/clean/steam_games_clean.csv", low_memory=False,
                parse_dates=["release_date"])
ai = pd.read_csv(ROOT / "data/clean/steam_ai_clean.csv", low_memory=False,
                 parse_dates=["release_date"])

# Older games have had more time to collect reviews, so attention comparisons
# use full release years 2014 to 2025 (2026 is a partial year).
COH = g[(g.release_year >= 2014) & (g.release_year <= 2025)]
SRC = "Source: FronkonGames Steam Games Dataset. Games released 2014 to 2025."
note(f"Games in 2014 to 2025 cohort: {len(COH):,}")

# 1. Release year (Q1)
yr = g[g.release_year >= 2006].groupby("release_year").agg(
    games=("app_id", "size"), median_reviews=("total_reviews", "median"))
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
a.bar(yr.index, yr.games, color=BLUE, width=0.75)
a.set_title("Games released per year")
a.set_ylabel("Games")
b.plot(yr.index, yr.median_reviews, color=BLUE, lw=2, marker="o", ms=4)
b.set_title("Median reviews per game, by release year")
b.set_ylabel("Median total reviews (log scale)")
b.set_yscale("symlog", linthresh=1)
for ax in (a, b):
    ax.axvspan(2025.5, 2026.5, color="#f3f3f3", zorder=0)
a.text(2026, 4500, "partial\nyear", ha="center", va="bottom", fontsize=7, color=INK2)
save(fig, "01_release_year.png", "Source: FronkonGames Steam Games Dataset. 2026 is a partial year.")
note("Q1 games per year:\n" + yr.to_string())

# 2. Price (Q2, Q3)
bins = [-0.01, 0, 4.99, 9.99, 19.99, 29.99, 59.99, 10_000]
labels = ["Free", "$0.01-4.99", "$5-9.99", "$10-19.99", "$20-29.99", "$30-59.99", "$60+"]
COH = COH.assign(price_band=pd.cut(COH.price, bins=bins, labels=labels))
pb = COH.groupby("price_band", observed=True).agg(
    games=("app_id", "size"), median_reviews=("total_reviews", "median"),
    share_zero=("has_reviews", lambda s: 1 - s.mean()))
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
colors = [ORANGE] + [BLUE] * (len(pb) - 1)
a.bar(pb.index.astype(str), pb.median_reviews, color=colors)
for i, v in enumerate(pb.median_reviews):
    a.text(i, v + 0.3, f"{v:g}", ha="center", fontsize=7, color=INK2)
a.set_title("Median reviews per game, by price")
a.set_ylabel("Median total reviews")
b.bar(pb.index.astype(str), pb.share_zero * 100, color=colors)
b.set_title("Share of games with zero reviews, by price")
b.set_ylabel("Percent of games")
for ax in (a, b):
    ax.tick_params(axis="x", rotation=30)
save(fig, "02_price.png", SRC)
note("Q2/Q3 by price band:\n" + pb.round(3).to_string())

# 3. Genres: crowded vs attention (Q4, Q5)
ge = explode(COH, "genres")
gs = ge.groupby("genres").agg(games=("app_id", "size"),
                              median_reviews=("total_reviews", "median"),
                              total_reviews=("total_reviews", "sum"))
gs = gs[gs.games >= 200].sort_values("games", ascending=False)
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(gs.games, gs.median_reviews, s=40, color=BLUE, edgecolor="white", lw=1.5, zorder=3)
ax.set_xscale("log")
label_points(ax, gs.games, gs.median_reviews, gs.index)
ax.set_xlabel("Number of games with this genre (log scale)")
ax.set_ylabel("Median total reviews per game")
ax.set_title("Genres: how crowded vs how much attention each game gets")
save(fig, "03_genres_crowded_vs_attention.png", SRC + " Genres with 200+ games.")
note("Q4/Q5 genres:\n" + gs.sort_values("median_reviews", ascending=False).to_string())

# 4. Genres of the top games over time (Q14)
g2 = g[(g.release_year >= 2010) & (g.release_year <= 2025)].copy()
cut = g2.groupby("release_year").total_reviews.transform(lambda s: s.quantile(0.9))
top = g2[g2.total_reviews >= cut]
te = explode(top, "genres")
share = (te.groupby(["release_year", "genres"]).app_id.nunique()
         / top.groupby("release_year").app_id.nunique()).unstack(fill_value=0) * 100
main = share.mean().sort_values(ascending=False).index[:6]
fig, axes = plt.subplots(2, 3, figsize=(10, 5), sharex=True, sharey=True)
for ax, name in zip(axes.flat, main):
    ax.plot(share.index, share[name], color=BLUE, lw=2)
    ax.set_title(name)
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
for ax in axes[:, 0]:
    ax.set_ylabel("% of top 10% games")
fig.suptitle("Genres among each year's top 10% games by reviews", fontweight="bold", fontsize=10)
save(fig, "04_top_game_genres_over_time.png",
     "Source: FronkonGames Steam Games Dataset. Games released 2010 to 2025.")
note("Q14 genre share of top 10% games (%):\n" + share[main].round(1).to_string())

# 5. Rating vs attention (Q6, Q7, Q9)
rated = COH[COH.total_reviews >= 10].copy()
rated["rating_band"] = pd.cut(rated.positive_share * 100, bins=range(0, 101, 10),
                              include_lowest=True)
rb = rated.groupby("rating_band", observed=True).agg(
    games=("app_id", "size"), median_reviews=("total_reviews", "median"))
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
lab = [f"{int(i.left) if i.left > 0 else 0}-{int(i.right)}%" for i in rb.index]
a.bar(lab, rb.games, color=BLUE)
a.set_title("Games by positive review share")
a.set_ylabel("Games")
b.bar(lab, rb.median_reviews, color=BLUE)
b.set_title("Median reviews per game, by positive review share")
b.set_ylabel("Median total reviews")
for ax in (a, b):
    ax.tick_params(axis="x", rotation=40)
save(fig, "05_rating_vs_attention.png", SRC + " Games with 10+ reviews.")
note("Q6/Q7/Q9 by rating band (10+ reviews):\n" + rb.to_string())

# Playtime (Q8): numbers only, most values are 0.
pt = COH.median_playtime_min
note(f"Q8 playtime: {(pt == 0).mean():.1%} of games have median playtime 0. "
     f"Among games with 1,000+ reviews: {(COH[COH.total_reviews >= 1000].median_playtime_min == 0).mean():.1%} are 0.")

# 6. Tags: crowded vs attention, and tags over-represented in top games (Q11, Q12)
tagged = COH[COH.has_tags]
te = explode(tagged, "tags")
ts = te.groupby("tags").agg(games=("app_id", "size"), median_reviews=("total_reviews", "median"))
ts = ts[ts.games >= 300]
cut1 = tagged.total_reviews.quantile(0.99)
topg = tagged[tagged.total_reviews >= cut1]
tt = explode(topg, "tags").groupby("tags").app_id.nunique() / len(topg)
base = te.groupby("tags").app_id.nunique() / len(tagged)
lift = (tt / base).dropna()
lift = lift[base[lift.index] * len(tagged) >= 300].sort_values(ascending=False)
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.3, 1]})
a.scatter(ts.games, ts.median_reviews, s=18, color=BLUE, edgecolor="white", lw=1, zorder=3)
show = pd.concat([ts.nlargest(5, "games"), ts.nlargest(8, "median_reviews")]).index.unique()
a.set_xscale("log")
label_points(a, ts.loc[show, "games"], ts.loc[show, "median_reviews"], show)
a.set_xlabel("Number of games with this tag (log scale)")
a.set_ylabel("Median total reviews per game")
a.set_title("Tags: how crowded vs attention per game")
top15 = lift.head(15)[::-1]
b.barh(top15.index, top15.values, color=BLUE)
b.axvline(1, color=INK2, lw=1)
b.set_xlabel("Times more common in top 1% games than in all games")
b.set_title("Tags most over-represented in the top 1%")
save(fig, "06_tags.png", SRC + " Tagged games. Tags on 300+ games.")
note(f"Q11/Q12 top 1% review cutoff: {cut1:,.0f} reviews ({len(topg):,} games)")
note("Q12 tags by median reviews (top 20):\n" + ts.sort_values("median_reviews", ascending=False).head(20).to_string())
note("Q12 tags by median reviews (bottom 20):\n" + ts.sort_values("median_reviews").head(20).to_string())
note("Q11 tag lift (top 20):\n" + lift.head(20).round(2).to_string())

# 7. Concentration of attention and publishers (Q13)
r = np.sort(COH.total_reviews.values)[::-1]
cum = np.cumsum(r) / r.sum() * 100
pct = np.arange(1, len(r) + 1) / len(r) * 100
pe = explode(COH, "publishers")
pubs = pe.groupby("publishers").agg(games=("app_id", "size"), reviews=("total_reviews", "sum"))
pubs = pubs.sort_values("reviews", ascending=False)
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
a.plot(pct, cum, color=BLUE, lw=2)
a.set_xscale("log")
a.set_xlim(0.01, 100)
a.set_xlabel("Top % of games by reviews (log scale)")
a.set_ylabel("% of all reviews")
a.set_title("How much of all attention the top games hold")
for p in (1, 10):
    v = cum[int(len(r) * p / 100) - 1]
    a.scatter([p], [v], s=30, color=BLUE, edgecolor="white", lw=1.5, zorder=3)
    a.annotate(f"top {p}% hold {v:.0f}%", (p, v), xytext=(-8, 8), ha="right",
               textcoords="offset points", fontsize=8, color=INK)
    note(f"Top {p}% of games hold {v:.1f}% of reviews")
top10 = pubs.head(12)[::-1]
b.barh(top10.index, top10.reviews / pubs.reviews.sum() * 100, color=BLUE)
b.set_xlabel("% of all reviews")
b.set_title("Publishers with the most total reviews")
save(fig, "07_attention_concentration.png", SRC)
note(f"Q13 publishers: {len(pubs):,}. Top 10 hold {pubs.reviews.head(10).sum() / pubs.reviews.sum():.1%} of reviews.")
note("Q13 top publishers:\n" + pubs.head(15).to_string())

# 8. AI disclosure (Q10, Q15) from the AI dataset only
ai["month"] = ai.release_date.dt.to_period("M").dt.to_timestamp()
m = ai.groupby("month").has_ai_disclosure.mean() * 100
by = ai.groupby(["release_year", "has_ai_disclosure"]).total_reviews.median().unstack()
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
a.plot(m.index, m.values, color=BLUE, lw=2)
a.set_ylim(0, 100)
a.set_ylabel("% of new games")
a.set_title("Share of new games with an AI disclosure, by month")
a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
x = np.arange(len(by))
w = 0.38
b.bar(x - w / 2 - 0.01, by[False], w, color=GRAY, label="No AI disclosure")
b.bar(x + w / 2 + 0.01, by[True], w, color=BLUE, label="AI disclosure")
b.set_xticks(x, by.index.astype(str))
b.set_ylabel("Median total reviews")
b.set_title("Median reviews per game, AI vs no AI")
b.legend(frameon=False, fontsize=8)
save(fig, "08_ai_disclosure.png",
     "Source: Steam Games from Jan2024 to Nov2026 (Kaggle). Newer games have had less time to collect reviews.")
note("Q15 AI share by year:\n" + (ai.groupby("release_year").has_ai_disclosure.mean() * 100).round(1).to_string())
note("Q10 median reviews by year and AI:\n" + by.to_string())
note("Q10 share with zero reviews by AI:\n" + ai.groupby("has_ai_disclosure").has_reviews.apply(lambda s: 1 - s.mean()).round(3).to_string())

(OUT / "numbers.txt").write_text("\n\n".join(numbers) + "\n")
print("wrote numbers.txt")
