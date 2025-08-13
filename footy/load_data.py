# footy/load_data.py  (append these helpers at the bottom)
import pandas as pd


def load_season_data_any(season_paths: dict):
    """
    Same as load_season_data but accepts any number of seasons.
    season_paths: {"2025-2026": Path(...xlsx), "2024-2025": Path(...xlsx), ...}
    Returns: data_by_season (dict of dicts), sheets_by_season (dict of lists)
    """
    data = {}
    sheets = {}
    for season, path in season_paths.items():
        df_sheets = pd.read_excel(path, sheet_name=None)
        data[season] = df_sheets
        sheets[season] = list(df_sheets.keys())
    return data, sheets


def load_and_merge_multi(data_by_season: dict):
    """
    Merge ALL sheets across ALL seasons into one DataFrame.
    data_by_season: {"2025-2026": {league: df, ...}, "2024-2025": {...}, ...}
    Returns: combined DataFrame with Season + League columns, date-sorted.
    """
    merged = []
    # Find union of sheet names that exist across seasons
    # (we’ll be defensive if a league/sheet is missing in a given season)
    all_sheet_names = set()
    for season_dict in data_by_season.values():
        all_sheet_names |= set(season_dict.keys())

    for season, season_dict in data_by_season.items():
        for sheet_name in all_sheet_names:
            if sheet_name not in season_dict:
                continue
            df = season_dict[sheet_name].copy()
            if df is None or df.empty:
                continue
            df["Season"] = season
            df["League"] = sheet_name
            # Parse dates if present
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            merged.append(df)

    if not merged:
        raise ValueError("No valid data found to merge.")

    combined = pd.concat(merged, ignore_index=True)

    # Basic cleaning: drop rows without essential identifiers
    needed = [c for c in ["Date", "HomeTeam", "AwayTeam"] if c in combined.columns]
    if needed:
        combined = combined.dropna(subset=needed, how="any")

    # Sort chronologically (then league for stability)
    sort_cols = [c for c in ["Date", "League"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    return combined