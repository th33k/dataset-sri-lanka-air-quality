"""
Daily updater for the Sri Lanka DSD-level air quality dataset.

Run by GitHub Actions every day (or by hand: `python scripts/daily_update.py`).

Each run:
  1. Drops rows that are not finished observations: dates after yesterday
     (Open-Meteo returns CAMS *forecasts* for today and future days) and rows
     with no values.
  2. Finds every (date, DSD) pair missing between START_DATE and yesterday
     (Asia/Colombo), and also re-fetches the last REFRESH_DAYS days, whose
     values can still be revised.
  3. Fetches only those date ranges, per batch of DSDs, from Open-Meteo.
  4. Merges, deduplicates, sorts, and rewrites the dataset (one CSV per year in
     data/processed/) and the district summary.

If the API rate limit is hit, the run keeps everything fetched so far and the
next run continues from where this one stopped.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import sys
import time

import numpy as np
import pandas as pd
import requests

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEZONE = "Asia/Colombo"
START_DATE = date(2023, 1, 1)
REFRESH_DAYS = 3        # re-fetch the most recent days in case values were revised
BATCH_SIZE = 25         # DSDs per API request
MERGE_GAP_DAYS = 7      # join missing-date ranges closer than this into one request

AIR_VARIABLES = [
    "pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
    "carbon_monoxide", "aerosol_optical_depth", "dust", "uv_index", "us_aqi",
]
DAILY_AGGS = {
    "pm2_5": ["mean", "min", "max"],
    "pm10": ["mean", "min", "max"],
    "nitrogen_dioxide": ["mean", "max"],
    "sulphur_dioxide": ["mean", "max"],
    "ozone": ["mean", "max"],
    "carbon_monoxide": ["mean", "max"],
    "aerosol_optical_depth": ["mean", "max"],
    "dust": ["mean", "max"],
    "uv_index": ["max"],
    "us_aqi": ["mean", "max"],
}
META_COLS = [
    "province_name", "province_pcode", "district_name", "district_pcode",
    "dsd_name", "dsd_pcode", "latitude", "longitude", "area_sqkm",
]
COLUMNS = ["date"] + META_COLS + [
    f"{var}_{stat}" for var, stats in DAILY_AGGS.items() for stat in stats
] + ["aqi_category"]
SORT_COLS = ["date", "province_name", "district_name", "dsd_name"]

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "processed"  # one CSV per year
DISTRICT_SUMMARY_CSV = REPO_ROOT / "data" / "processed" / "sri_lanka_district_air_quality_summary.csv"
REF_CSV = REPO_ROOT / "data" / "reference" / "sri_lanka_dsd_reference.csv"


class RateLimited(Exception):
    """Raised when the API keeps refusing requests."""


def classify_aqi(value):
    """US EPA AQI category from the daily peak AQI."""
    if pd.isna(value):
        return "Unknown"
    for limit, name in [(50, "Good"), (100, "Moderate"), (150, "Unhealthy for Sensitive Groups"),
                        (200, "Unhealthy"), (300, "Very Unhealthy")]:
        if value <= limit:
            return name
    return "Hazardous"


def fetch(batch, start, end, retries=6):
    """Fetch hourly data for a batch of DSDs between two dates (inclusive)."""
    params = {
        "latitude": ",".join(f"{v:.4f}" for v in batch["latitude"]),
        "longitude": ",".join(f"{v:.4f}" for v in batch["longitude"]),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(AIR_VARIABLES),
        "timezone": TIMEZONE,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(AIR_QUALITY_URL, params=params, timeout=90)
            if resp.status_code == 429:
                wait = 20 * attempt
                print(f"    rate limited, waiting {wait}s ({attempt}/{retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return [data] if isinstance(data, dict) else data
        except (requests.RequestException, ValueError) as err:
            wait = 10 * attempt
            print(f"    request error: {err}; retrying in {wait}s ({attempt}/{retries})")
            time.sleep(wait)
    raise RateLimited(f"gave up on {start}..{end} after {retries} attempts")


def to_daily(responses, batch, start, end):
    """Aggregate hourly responses into one row per DSD per day."""
    frames = []
    for item, (_, meta) in zip(responses, batch.iterrows()):
        hourly = item.get("hourly") or {}
        if "time" not in hourly:
            continue
        h = pd.DataFrame(hourly)
        h["date"] = pd.to_datetime(h["time"]).dt.strftime("%Y-%m-%d")
        aggs = {k: v for k, v in DAILY_AGGS.items() if k in h.columns}
        daily = h.groupby("date").agg(aggs)
        daily.columns = ["_".join(c) for c in daily.columns]
        daily = daily.reset_index()
        floats = daily.select_dtypes(include=[np.floating]).columns
        daily[floats] = daily[floats].round(2)
        daily["aqi_category"] = daily["us_aqi_max"].apply(classify_aqi)
        for col in META_COLS:
            daily[col] = meta[col]
        frames.append(daily)
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    out = pd.concat(frames, ignore_index=True).reindex(columns=COLUMNS)
    in_window = out["date"].between(start.isoformat(), end.isoformat())
    return out[in_window & (out["aqi_category"] != "Unknown")]


def to_ranges(dates):
    """Collapse sorted dates into (start, end) ranges, joining small gaps."""
    ranges = []
    for d in dates:
        if ranges and (d - ranges[-1][1]).days <= MERGE_GAP_DAYS:
            ranges[-1][1] = d
        else:
            ranges.append([d, d])
    return [tuple(r) for r in ranges]


def load_dataset():
    """Read all yearly files into one DataFrame."""
    files = sorted(DATA_DIR.glob("sri_lanka_dsd_air_quality_*.csv"))
    if not files:
        sys.exit(f"No dataset files found in {DATA_DIR}")
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)


def save_dataset(df, out_dir=DATA_DIR):
    """Write one CSV per year, which keeps every file far below GitHub's 100 MB limit."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = (df.drop_duplicates(["date", "dsd_pcode"], keep="last")
          .sort_values(SORT_COLS).reindex(columns=COLUMNS).reset_index(drop=True))
    for year, part in df.groupby(df["date"].str[:4]):
        part.to_csv(out_dir / f"sri_lanka_dsd_air_quality_{year}.csv", index=False, lineterminator="\n")
    return df


def update_district_summary(df):
    """Recompute the district summary table."""
    summary = df.groupby(["province_name", "district_name"]).agg(
        total_dsds=("dsd_name", "nunique"),
        total_records=("date", "count"),
        avg_pm25=("pm2_5_mean", "mean"),
        max_pm25=("pm2_5_max", "max"),
        avg_pm10=("pm10_mean", "mean"),
        max_pm10=("pm10_max", "max"),
        avg_no2=("nitrogen_dioxide_mean", "mean"),
        avg_so2=("sulphur_dioxide_mean", "mean"),
        avg_aqi=("us_aqi_mean", "mean"),
        peak_aqi=("us_aqi_max", "max"),
    ).round(2).reset_index()
    summary.sort_values("avg_pm25", ascending=False).to_csv(DISTRICT_SUMMARY_CSV, index=False, lineterminator="\n")


def main():
    yesterday = datetime.now(ZoneInfo(TIMEZONE)).date() - timedelta(days=1)
    ref = pd.read_csv(REF_CSV)
    master = load_dataset()
    print(f"Dataset: {len(master):,} rows, {master['date'].min()} to {master['date'].max()}")

    # 1. Keep only finished observations inside the dataset window.
    keep = (master["date"].between(START_DATE.isoformat(), yesterday.isoformat())
            & (master["aqi_category"] != "Unknown"))
    if (~keep).any():
        print(f"Dropping {int((~keep).sum()):,} rows that are forecasts, empty, or out of range")
    master = master[keep]

    # 2. Work out which (date, DSD) pairs need fetching.
    all_days = pd.date_range(START_DATE, yesterday).strftime("%Y-%m-%d")
    expected = pd.MultiIndex.from_product([all_days, ref["dsd_pcode"]], names=["date", "dsd_pcode"])
    have = pd.MultiIndex.from_frame(master[["date", "dsd_pcode"]])
    missing = expected.difference(have).to_frame(index=False)
    refresh = set(all_days[-REFRESH_DAYS:])
    print(f"Target window: {START_DATE} to {yesterday} | missing DSD-days: {len(missing):,}")

    # 3. Fetch per batch, only the date ranges that batch needs.
    new, stopped = [], False
    for b, start_i in enumerate(range(0, len(ref), BATCH_SIZE), 1):
        batch = ref.iloc[start_i:start_i + BATCH_SIZE]
        need = set(missing.loc[missing["dsd_pcode"].isin(batch["dsd_pcode"]), "date"]) | refresh
        for start, end in to_ranges(sorted(date.fromisoformat(d) for d in need)):
            print(f"  batch {b}: {start} to {end}")
            try:
                new.append(to_daily(fetch(batch, start, end), batch, start, end))
            except RateLimited as err:
                print(f"::warning::Stopping early, progress kept for next run ({err})")
                stopped = True
                break
            time.sleep(2)
        if stopped:
            break

    # 4. Merge and save.
    combined = save_dataset(pd.concat([master] + new, ignore_index=True))
    update_district_summary(combined)

    still_missing = len(expected.difference(pd.MultiIndex.from_frame(combined[["date", "dsd_pcode"]])))
    print(f"Saved {len(combined):,} rows, {combined['date'].min()} to {combined['date'].max()} "
          f"| still missing DSD-days: {still_missing:,}")
    if stopped and not new:
        sys.exit("No data fetched: API rate limit reached.")


if __name__ == "__main__":
    main()
