# Crowded or Overlooked? What kinds of games get attention on Steam?

CS 6730 Data Visualization final project, Fall 2026, Georgia Tech.
Team Single Player. Eric Shao.

An interactive data story about what kinds of Steam games get attention, measured by review counts.

## Repository layout

| Path | Contents |
| --- | --- |
| `data/clean/steam_games_clean.csv` | Clean main dataset, 125,854 games |
| `data/clean/steam_ai_clean.csv` | Clean AI disclosure dataset, 63,798 games released Jan 2024 to Nov 2026 |
| `data/clean/*_report.txt` | Counts from each cleaning step |
| `data/raw/` | Where the raw files go. Not committed. See its README for sources |
| `scripts/clean_steam.py` | Cleans the main dataset |
| `scripts/clean_ai.py` | Cleans the AI disclosure dataset |

## Rebuilding the clean data

1. Download the raw files listed in `data/raw/README.md` into `data/raw/`.
2. Run `python3 scripts/clean_steam.py` and `python3 scripts/clean_ai.py`. Requires pandas.

## Data sources

- [FronkonGames Steam Games Dataset](https://huggingface.co/datasets/FronkonGames/steam-games-dataset), MIT license.
- [Steam Games from Jan2024 to Nov2026](https://www.kaggle.com/datasets/josehzz/steam-games-jan2024-nov2026-with-ai-tags).

## Code and AI use

All code in `scripts/` was written for this project with help from an AI assistant, which the course allows for implementation.
