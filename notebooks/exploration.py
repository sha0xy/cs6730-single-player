# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "pandas",
#     "altair",
# ]
# ///
"""Exploration charts for process book section 2.6.

Open in molab, or run locally with: marimo edit notebooks/exploration.py
Attention is measured by total reviews. Medians are used because review counts
are very skewed.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import altair as alt
    from pathlib import Path
    return Path, alt, mo, pd


@app.cell
def _(Path, pd):
    # Use the repo copy when it is there (local or a molab GitHub mirror),
    # otherwise read from GitHub.
    RAW = "https://raw.githubusercontent.com/sha0xy/cs6730-single-player/main/data/clean/"

    def load(name, **kw):
        for base in (Path("data/clean"), Path("../data/clean")):
            if (base / name).exists():
                return pd.read_csv(base / name, low_memory=False, **kw)
        return pd.read_csv(RAW + name, low_memory=False, **kw)

    games = load("steam_games_clean.csv", parse_dates=["release_date"])
    ai = load("steam_ai_clean.csv", parse_dates=["release_date"])
    return ai, games


@app.cell
def _(alt):
    BLUE, ORANGE, GRAY = "#257de0", "#f47230", "#b5b5b5"
    SIX = ["#257de0", "#f47230", "#17a589", "#8e44ad", "#d4ac0d", "#c0392b"]

    @alt.theme.register("steam", enable=True)
    def theme():
        return alt.theme.ThemeConfig({"config": {
            "font": "Inter, Helvetica, Arial, sans-serif",
            "view": {"stroke": None},
            "axis": {"labelColor": "#666", "titleColor": "#666", "gridColor": "#eee",
                     "domainColor": "#ccc", "tickColor": "#ccc", "labelFontSize": 11,
                     "titleFontSize": 11, "titleFontWeight": "normal"},
            "title": {"fontSize": 14, "anchor": "start", "color": "#191919",
                      "subtitleColor": "#666", "subtitleFontSize": 11},
            "legend": {"labelColor": "#444", "titleColor": "#666", "labelFontSize": 11},
        }})
    W, H = 340, 240
    return BLUE, GRAY, H, ORANGE, SIX, W


@app.cell
def _(pd):
    SUFFIXES = {"inc", "inc.", "ltd", "ltd.", "llc", "llc.", "co.", "co", "corp",
                "corp.", "s.a.", "s.l.", "gmbh", "pty", "pty.", "plc", "l.l.c."}

    def split_names(s):
        """Split a comma list, keeping company suffixes like ', Inc.' with the name."""
        out = []
        for part in str(s).split(","):
            part = part.strip()
            if not part:
                continue
            if out and part.casefold() in SUFFIXES:
                out[-1] = f"{out[-1]}, {part}"
            else:
                out.append(part)
        return out

    def explode(df, col):
        out = df.assign(**{col: df[col].fillna("").map(split_names)}).explode(col)
        return out[out[col].notna() & (out[col] != "")]
    return (explode,)


@app.cell
def _(games, mo):
    # Older games have had more time to collect reviews, so attention charts use
    # games released 2014 to 2025.
    coh = games[(games.release_year >= 2014) & (games.release_year <= 2025)].copy()
    mo.md(f"""
    # Exploration

    **{len(games):,}** games in the main dataset. Attention charts use the
    **{len(coh):,}** games released 2014 to 2025, so older games with years of
    reviews do not skew the comparison.
    """)
    return (coh,)


@app.cell
def _(mo):
    mo.md("## Exploration 1. Release year (Q1)")
    return


@app.cell
def _(BLUE, H, W, alt, games, mo):
    _yr = (games[games.release_year >= 2006].groupby("release_year")
          .agg(games=("app_id", "size"), median_reviews=("total_reviews", "median"))
          .reset_index())
    _yr["note"] = _yr.release_year.map(lambda y: "Partial year" if y == 2026 else "")
    _base = alt.Chart(_yr).encode(x=alt.X("release_year:O", title="Release year",
                                        axis=alt.Axis(labelAngle=-45, values=list(range(2006, 2027, 2)))))
    _tip = [alt.Tooltip("release_year:O", title="Year"), alt.Tooltip("games:Q", format=","),
           alt.Tooltip("median_reviews:Q", title="Median reviews"), "note:N"]
    _count = _base.mark_bar(color=BLUE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        y=alt.Y("games:Q", title="Games released"),
        opacity=alt.condition("datum.release_year == 2026", alt.value(0.35), alt.value(1)),
        tooltip=_tip,
    ).properties(width=W, height=H, title=alt.Title("Games released per year",
                                                    subtitle="2026 is a partial year"))
    _med = _base.mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(size=40, filled=True)).encode(
        y=alt.Y("median_reviews:Q", title="Median reviews per game",
                scale=alt.Scale(type="symlog")),
        tooltip=_tip,
    ).properties(width=W, height=H, title=alt.Title("Median reviews per game",
                                                    subtitle="Log scale. Newer games have had less time"))
    (_count | _med)
    return


@app.cell
def _(mo):
    mo.md("## Exploration 2. Price (Q2, Q3)")
    return


@app.cell
def _(BLUE, H, ORANGE, W, alt, coh, mo, pd):
    _bins = [-0.01, 0, 4.99, 9.99, 19.99, 29.99, 59.99, 10_000]
    _labels = ["Free", "$0.01 to 4.99", "$5 to 9.99", "$10 to 19.99", "$20 to 29.99",
              "$30 to 59.99", "$60+"]
    _pb = (coh.assign(price_band=pd.cut(coh.price, bins=_bins, labels=_labels))
          .groupby("price_band", observed=True)
          .agg(games=("app_id", "size"), median_reviews=("total_reviews", "median"),
               zero_share=("has_reviews", lambda s: (1 - s.mean()) * 100))
          .reset_index())
    _pb["is_free"] = _pb.price_band.astype(str) == "Free"
    _pb["price_band"] = _pb.price_band.astype(str)
    _enc = dict(
        x=alt.X("price_band:N", sort=_labels, title=None, axis=alt.Axis(labelAngle=-30)),
        color=alt.Color("is_free:N", scale=alt.Scale(domain=[True, False], range=[ORANGE, BLUE]),
                        legend=None),
        tooltip=[alt.Tooltip("price_band:N", title="Price"), alt.Tooltip("games:Q", format=","),
                 alt.Tooltip("median_reviews:Q", title="Median reviews"),
                 alt.Tooltip("zero_share:Q", title="% with zero reviews", format=".1f")],
    )
    _bar = dict(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    _a = alt.Chart(_pb).mark_bar(**_bar).encode(
        y=alt.Y("median_reviews:Q", title="Median reviews per game"), **_enc
    ).properties(width=W, height=H, title="Median reviews per game, by price")
    _b = alt.Chart(_pb).mark_bar(**_bar).encode(
        y=alt.Y("zero_share:Q", title="% of games"), **_enc
    ).properties(width=W, height=H, title="Share of games with zero reviews")
    (_a | _b)
    return


@app.cell
def _(mo):
    mo.md("## Exploration 3. Genres, crowded vs attention (Q4, Q5)")
    return


@app.cell
def _(BLUE, alt, coh, explode, mo):
    _gs = (explode(coh, "genres").groupby("genres")
          .agg(games=("app_id", "size"), median_reviews=("total_reviews", "median"))
          .reset_index())
    _gs = _gs[_gs.games >= 200]
    _pts = alt.Chart(_gs).mark_circle(size=90, color=BLUE, opacity=0.9, stroke="white", strokeWidth=1.5).encode(
        x=alt.X("games:Q", scale=alt.Scale(type="log"), title="Games with this genre (log scale). Further right = more crowded"),
        y=alt.Y("median_reviews:Q", title="Median reviews per game"),
        tooltip=[alt.Tooltip("genres:N", title="Genre"), alt.Tooltip("games:Q", format=","),
                 alt.Tooltip("median_reviews:Q", title="Median reviews")],
    )
    _low = ["RPG"]  # placed left of its point so it does not hit Simulation
    _txt = alt.Chart(_gs[~_gs.genres.isin(_low)]).mark_text(align="left", dx=7, dy=-6, fontSize=10, color="#555").encode(
        x="games:Q", y="median_reviews:Q", text="genres:N")
    _txt2 = alt.Chart(_gs[_gs.genres.isin(_low)]).mark_text(align="right", dx=-7, dy=-6, fontSize=10, color="#555").encode(
        x="games:Q", y="median_reviews:Q", text="genres:N")
    ((_pts + _txt + _txt2).properties(
        width=700, height=380,
        title=alt.Title("Genres: how crowded each one is vs attention per game",
                        subtitle="Genres with 200+ games. Includes non-game software genres")))
    return


@app.cell
def _(mo):
    mo.md("## Exploration 4. Genres of the top games over time (Q14)")
    return


@app.cell
def _(SIX, alt, explode, games, mo):
    _g2 = games[(games.release_year >= 2010) & (games.release_year <= 2025)].copy()
    _cut = _g2.groupby("release_year").total_reviews.transform(lambda s: s.quantile(0.9))
    _top = _g2[_g2.total_reviews >= _cut]
    _n_top = _top.groupby("release_year").app_id.nunique()
    _sh = (explode(_top, "genres").groupby(["release_year", "genres"]).app_id.nunique()
          .div(_n_top, level="release_year").mul(100).rename("share").reset_index())
    _main = _sh.groupby("genres").share.mean().nlargest(6).index.tolist()
    _sh = _sh[_sh.genres.isin(_main)]
    _last = _sh[_sh.release_year == _sh.release_year.max()]
    _color = alt.Color("genres:N", scale=alt.Scale(domain=_main, range=SIX), title="Genre")
    _line = alt.Chart(_sh).mark_line(strokeWidth=2.5).encode(
        x=alt.X("release_year:O", title="Release year", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("share:Q", title="% of that year's top 10% games", scale=alt.Scale(domain=[0, 100])),
        color=_color,
        tooltip=[alt.Tooltip("genres:N", title="Genre"), alt.Tooltip("release_year:O", title="Year"),
                 alt.Tooltip("share:Q", title="% of top games", format=".1f")],
    )
    _dots = _line.mark_circle(size=30)
    _labels = alt.Chart(_last).mark_text(align="left", dx=8, fontSize=11).encode(
        x="release_year:O", y="share:Q", text="genres:N", color=_color)
    ((_line + _dots + _labels).properties(
        width=680, height=380,
        title=alt.Title("Which genres the most reviewed games carry, by year",
                        subtitle=["Top 10% of each year's games by reviews.",
                                  "A game can have several genres, so the lines overlap and do not add up to 100%."])))
    return


@app.cell
def _(mo):
    mo.md("## Exploration 5. Rating vs attention (Q6, Q7, Q9)")
    return


@app.cell
def _(BLUE, H, W, alt, coh, mo, pd):
    _rated = coh[coh.total_reviews >= 10].copy()
    _rated["band"] = pd.cut(_rated.positive_share * 100, bins=range(0, 101, 10), include_lowest=True)
    _rb = (_rated.groupby("band", observed=True)
          .agg(games=("app_id", "size"), median_reviews=("total_reviews", "median")).reset_index())
    _rb["band"] = [f"{int(max(i.left, 0))} to {int(i.right)}%" for i in _rb.band]
    _order = _rb.band.tolist()
    _enc = dict(x=alt.X("band:N", sort=_order, title="Positive review share", axis=alt.Axis(labelAngle=-30)),
               tooltip=[alt.Tooltip("band:N", title="Positive share"), alt.Tooltip("games:Q", format=","),
                        alt.Tooltip("median_reviews:Q", title="Median reviews")])
    _bar = dict(color=BLUE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    _a = alt.Chart(_rb).mark_bar(**_bar).encode(y=alt.Y("games:Q", title="Games"), **_enc).properties(
        width=W, height=H, title=alt.Title("Games by positive review share", subtitle="Games with 10+ reviews"))
    _b = alt.Chart(_rb).mark_bar(**_bar).encode(y=alt.Y("median_reviews:Q", title="Median reviews per game"), **_enc).properties(
        width=W, height=H, title=alt.Title("Median reviews, by positive review share", subtitle="Games with 10+ reviews"))
    (_a | _b)
    return


@app.cell
def _(coh, mo):
    _pt = coh.median_playtime_min
    mo.md(f"""
    **Q8 playtime.** {(_pt == 0).mean():.0%} of games have _a median playtime of 0,
    so playtime cannot be compared fairly. Among games with 1,000+ reviews,
    {(coh[coh.total_reviews >= 1000].median_playtime_min == 0).mean():.0%} are 0.
    """)
    return


@app.cell
def _(mo):
    mo.md("## Exploration 6. Tags (Q11, Q12)")
    return


@app.cell
def _(BLUE, alt, coh, explode, mo):
    _tagged = coh[coh.has_tags]
    _te = explode(_tagged, "tags")
    _ts = (_te.groupby("tags").agg(games=("app_id", "size"), median_reviews=("total_reviews", "median"))
          .reset_index())
    _ts = _ts[_ts.games >= 300]
    _cut1 = _tagged.total_reviews.quantile(0.99)
    _topg = _tagged[_tagged.total_reviews >= _cut1]
    _in_top = explode(_topg, "tags").groupby("tags").app_id.nunique() / len(_topg)
    _in_all = _te.groupby("tags").app_id.nunique() / len(_tagged)
    _lift = (_in_top / _in_all).dropna().rename("lift").reset_index()
    _lift = _lift.merge(_ts[["tags", "games"]], on="tags")
    _lift["pct_top"] = _lift.tags.map(_in_top) * 100
    _lift["pct_all"] = _lift.tags.map(_in_all) * 100
    _lift = _lift.nlargest(15, "lift")

    # A few labels only; hover shows every tag name.
    _show = ["Great Soundtrack", "Classic", "Moddable", "Remake", "Mature", "Turn-Based"]
    _crowd = _ts.nlargest(2, "games")
    _pts = alt.Chart(_ts).mark_circle(size=40, color=BLUE, opacity=0.7).encode(
        x=alt.X("games:Q", scale=alt.Scale(type="log"), title="Games with this tag (log scale)"),
        y=alt.Y("median_reviews:Q", title="Median reviews per game"),
        tooltip=[alt.Tooltip("tags:N", title="Tag"), alt.Tooltip("games:Q", format=","),
                 alt.Tooltip("median_reviews:Q", title="Median reviews")],
    )
    _txt = alt.Chart(_ts[_ts.tags.isin(_show)]).mark_text(align="left", dx=6, dy=-5, fontSize=10, color="#555").encode(
        x="games:Q", y="median_reviews:Q", text="tags:N")
    _ctxt = alt.Chart(_crowd.iloc[[0]]).mark_text(align="right", dx=-6, dy=-12, fontSize=10, color="#555").encode(
        x="games:Q", y="median_reviews:Q", text="tags:N")
    _ctxt = _ctxt + alt.Chart(_crowd.iloc[[1]]).mark_text(align="right", dx=-6, dy=14, fontSize=10, color="#555").encode(
        x="games:Q", y="median_reviews:Q", text="tags:N")
    _a = (_pts + _txt + _ctxt).properties(width=380, height=320, title=alt.Title(
        "Tags: how crowded vs attention per game", subtitle="Tags on 300+ games. Hover for names"))
    _bars = alt.Chart(_lift).mark_bar(color=BLUE, cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        y=alt.Y("tags:N", sort="-x", title=None),
        x=alt.X("lift:Q", title="Times more common in top 1% games"),
        tooltip=[alt.Tooltip("tags:N", title="Tag"), alt.Tooltip("lift:Q", format=".1f", title="Times more common"),
                 alt.Tooltip("pct_top:Q", format=".1f", title="% of top 1% games"),
                 alt.Tooltip("pct_all:Q", format=".1f", title="% of all tagged games")],
    )
    _rule = alt.Chart().mark_rule(color="#888", strokeDash=[3, 3]).encode(x=alt.datum(1))
    _b = (_bars + _rule).properties(width=280, height=320, title=alt.Title(
        "Tags most over-represented in the top 1%", subtitle=f"Top 1% = {_cut1:,.0f}+ reviews. Dashed line = same as average"))
    (_a | _b)
    return


@app.cell
def _(mo):
    mo.md("## Exploration 7. How attention is shared out (Q13)")
    return


@app.cell
def _(BLUE, GRAY, alt, coh, explode, mo, pd):
    _r = coh.total_reviews.sort_values(ascending=False).reset_index(drop=True)
    _n, _total = len(_r), _r.sum()
    _t1, _t10 = int(_n * 0.01), int(_n * 0.10)
    _groups = pd.DataFrame({
        "group": ["Top 1% of games", "Next 9%", "Bottom 90%"],
        "games": [_t1, _t10 - _t1, _n - _t10],
        "share": [_r[:_t1].sum() / _total * 100, _r[_t1:_t10].sum() / _total * 100, _r[_t10:].sum() / _total * 100],
    })
    _groups["label"] = _groups.share.map(lambda v: f"{v:.0f}%")
    _order = _groups.group.tolist()
    _a_bars = alt.Chart(_groups).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        y=alt.Y("group:N", sort=_order, title=None),
        x=alt.X("share:Q", title="% of all reviews", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("group:N", scale=alt.Scale(domain=_order, range=[BLUE, "#8fbcef", GRAY]), legend=None),
        tooltip=[alt.Tooltip("group:N", title="Group"), alt.Tooltip("games:Q", format=",", title="Games"),
                 alt.Tooltip("share:Q", format=".1f", title="% of all reviews")],
    )
    _a_txt = _a_bars.mark_text(align="left", dx=5, fontSize=12, color="#191919").encode(text="label:N", color=alt.value("#191919"))
    _a = (_a_bars + _a_txt).properties(width=300, height=180, title=alt.Title(
        "Share of all reviews held by each group of games", subtitle="Games ranked by review count"))

    _pubs = (explode(coh, "publishers").groupby("publishers").total_reviews.sum()
            .div(_total).mul(100).rename("share").nlargest(12).reset_index())
    _b = alt.Chart(_pubs).mark_bar(color=BLUE, cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        y=alt.Y("publishers:N", sort="-x", title=None),
        x=alt.X("share:Q", title="% of all reviews"),
        tooltip=[alt.Tooltip("publishers:N", title="Publisher"), alt.Tooltip("share:Q", format=".2f", title="% of all reviews")],
    ).properties(width=300, height=300, title="Publishers with the most total reviews")
    (_a | _b)
    return


@app.cell
def _(mo):
    mo.md("## Exploration 8. AI disclosure (Q10, Q15)")
    return


@app.cell
def _(BLUE, GRAY, H, W, ai, alt, mo):
    _m = (ai.assign(month=ai.release_date.dt.to_period("M").dt.to_timestamp())
         .groupby("month").agg(share=("has_ai_disclosure", "mean"), games=("app_id", "size"))
         .reset_index())
    _m["share"] *= 100
    _a = alt.Chart(_m).mark_line(color=BLUE, strokeWidth=2.5, point=alt.OverlayMarkDef(size=25, filled=True)).encode(
        x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %Y", tickCount=6)),
        y=alt.Y("share:Q", title="% of new games", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("month:T", format="%b %Y", title="Month"),
                 alt.Tooltip("share:Q", format=".1f", title="% with AI disclosure"),
                 alt.Tooltip("games:Q", format=",", title="Games released")],
    ).properties(width=W, height=H, title="Share of new games with an AI disclosure")

    _by = (ai.groupby(["release_year", "has_ai_disclosure"])
          .agg(median_reviews=("total_reviews", "median"), games=("app_id", "size")).reset_index())
    _by["group"] = _by.has_ai_disclosure.map({True: "AI disclosure", False: "No AI disclosure"})
    _dom = ["No AI disclosure", "AI disclosure"]
    _b = alt.Chart(_by).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("release_year:O", title="Release year", axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("group:N", sort=_dom),
        y=alt.Y("median_reviews:Q", title="Median reviews per game"),
        color=alt.Color("group:N", scale=alt.Scale(domain=_dom, range=[GRAY, BLUE]), title=None,
                        legend=alt.Legend(orient="right")),
        tooltip=[alt.Tooltip("release_year:O", title="Year"), alt.Tooltip("group:N", title="Group"),
                 alt.Tooltip("median_reviews:Q", title="Median reviews"), alt.Tooltip("games:Q", format=",")],
    ).properties(width=W, height=H, title=alt.Title("Median reviews, AI vs no AI",
                                                    subtitle="Compare within a year. Newer games have had less time"))
    ((_a | _b).properties(
        title=alt.Title("Source: Steam Games from Jan2024 to Nov2026 (Kaggle)", orient="bottom",
                        fontSize=10, fontWeight="normal", color="#666")))
    return


if __name__ == "__main__":
    app.run()
