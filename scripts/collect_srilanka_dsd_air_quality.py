"""
Sri Lanka DSD-Level Air Quality Dataset Collector.

Collects historical air quality data for all 339 Divisional Secretariat Divisions (DSDs)
across all 25 Districts and 9 Provinces of Sri Lanka.

Data Source:
  - Copernicus Atmosphere Monitoring Service (CAMS) Global Reanalysis & Near-Real-Time Models
  - Open-Meteo Air Quality API (CC BY 4.0)
  - UN OCHA / Survey Department of Sri Lanka Subnational Administrative Boundaries (COD-AB)

Features:
  - Batched API queries (up to 25 DSDs per call for optimal performance)
  - Resilient disk checkpointing/caching (resumes seamlessly if interrupted)
  - Daily statistical aggregation (mean, min, max) for key atmospheric pollutants:
    PM2.5, PM10, NO2, SO2, O3, CO, Dust, Aerosol Optical Depth, UV Index, and US AQI
  - Categorical US EPA AQI classification
  - Automatic reconciliation with official Sri Lanka DSD P-codes and district/province hierarchy

Usage:
  python collect_srilanka_dsd_air_quality.py
  python collect_srilanka_dsd_air_quality.py --start 2023-01-01 --end 2024-12-31

The end date defaults to yesterday (Sri Lanka time) and is never later than that:
today and future dates from the API are forecasts, not observations.
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
import pandas as pd
import requests

from daily_update import save_dataset

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEZONE = "Asia/Colombo"

AIR_VARIABLES = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide",
    "aerosol_optical_depth",
    "dust",
    "uv_index",
    "us_aqi",
]


def classify_aqi(value):
    """US EPA AQI categorization based on daily peak AQI."""
    if pd.isna(value):
        return "Unknown"
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for Sensitive Groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def fetch_batch_data(lats, lons, start_date, end_date, retries=8, backoff_factor=15):
    """Fetch air quality data for multiple coordinates in a single API call."""
    lat_str = ",".join([f"{lat:.4f}" for lat in lats])
    lon_str = ",".join([f"{lon:.4f}" for lon in lons])

    params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(AIR_VARIABLES),
        "timezone": TIMEZONE,
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(AIR_QUALITY_URL, params=params, timeout=120)
            if resp.status_code == 429:
                body_text = resp.text
                if "Daily" in body_text or "tomorrow" in body_text:
                    print("\n  [Daily API Quota Limit Reached] Open-Meteo free tier limit (10,000 calls/day) reached for today.")
                    print("  The daily limit resets at 00:00 UTC (05:30 AM Sri Lanka Time).")
                    print("  Merging all downloaded records into the master dataset now...")
                    raise KeyboardInterrupt("Daily quota reached. Progress preserved in cache.")

                if "Hourly" in body_text or "hour" in body_text:
                    now = datetime.now(timezone.utc)
                    wait_seconds = (60 - now.minute) * 60 - now.second + 30
                    print(f"\n  [Hourly API Quota Limit] Open-Meteo hourly limit resets at the top of the clock hour.")
                    print(f"  Sleeping {wait_seconds // 60}m {wait_seconds % 60}s until the new window opens, then continuing automatically...\n")
                    time.sleep(wait_seconds)
                    continue

                wait_time = max(30, backoff_factor * attempt)
                print(f"  [Rate limited 429] Waiting {wait_time}s for window reset (Attempt {attempt}/{retries})...")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and len(lats) == 1:
                return [data]
            return data
        except (requests.RequestException, ValueError) as err:
            wait_time = max(10, 5 * attempt)
            print(f"  [Request Error: {err}] Retrying in {wait_time}s (Attempt {attempt}/{retries})...")
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch batch after {retries} attempts.")


def process_batch_response(resp_list, batch_df):
    """Aggregate hourly observations into daily metrics per DSD."""
    records = []
    for idx, item in enumerate(resp_list):
        meta = batch_df.iloc[idx]
        hourly = item.get("hourly", {})
        if not hourly or "time" not in hourly:
            continue

        df_h = pd.DataFrame(hourly)
        df_h["time"] = pd.to_datetime(df_h["time"])
        df_h["date"] = df_h["time"].dt.strftime("%Y-%m-%d")

        # Group by day
        agg_dict = {
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
        # Only aggregate keys that exist in output
        valid_aggs = {k: v for k, v in agg_dict.items() if k in df_h.columns}
        daily = df_h.groupby("date").agg(valid_aggs).reset_index()
        daily.columns = ["_".join(c).strip("_") for c in daily.columns]

        # Round numeric values for readability and storage efficiency
        float_cols = daily.select_dtypes(include=[np.float64, np.float32]).columns
        daily[float_cols] = daily[float_cols].round(2)

        # Classify daily peak AQI
        if "us_aqi_max" in daily.columns:
            daily["aqi_category"] = daily["us_aqi_max"].apply(classify_aqi)

        # Attach spatial metadata
        for col in [
            "province_name", "province_pcode",
            "district_name", "district_pcode",
            "dsd_name", "dsd_pcode",
            "latitude", "longitude", "area_sqkm"
        ]:
            if col in meta:
                daily[col] = meta[col]

        records.append(daily)

    if records:
        return pd.concat(records, ignore_index=True)
    return pd.DataFrame()


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REF = REPO_ROOT / "data" / "reference" / "sri_lanka_dsd_reference.csv"
DEFAULT_CACHE = REPO_ROOT / "data" / "cache_dsd"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed"


def split_date_chunks(start_str, end_str):
    """Break wide date ranges into manageable chunks (by year) for reliable batching."""
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")

    chunks = []
    curr_start = start_dt
    while curr_start < end_dt:
        year = curr_start.year
        year_end = datetime(year, 12, 31)
        curr_end = min(year_end, end_dt)
        chunks.append((
            f"{year}",
            curr_start.strftime("%Y-%m-%d"),
            curr_end.strftime("%Y-%m-%d")
        ))
        curr_start = datetime(year + 1, 1, 1)
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Collect Sri Lanka DSD-Level Air Quality Dataset")
    parser.add_argument("--start", default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD); default and maximum: yesterday")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of DSDs per API request")
    parser.add_argument("--reference", default=str(DEFAULT_REF), help="DSD master reference file")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE), help="Directory for checkpoint parquet files")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Folder for the yearly CSV files (files for collected years are replaced)")
    args = parser.parse_args()

    ref_path = Path(args.reference)
    if not ref_path.exists():
        sys.exit(f"Error: Reference CSV not found at {ref_path}")

    dsd_master = pd.read_csv(ref_path)
    total_dsds = len(dsd_master)
    print(f"Loaded {total_dsds} DSD locations from {ref_path}.")

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    yesterday = (datetime.now(ZoneInfo(TIMEZONE)).date() - timedelta(days=1)).isoformat()
    if not args.end or args.end > yesterday:
        args.end = yesterday  # only completed days are observations
    date_chunks = split_date_chunks(args.start, args.end)
    print(f"Collection timeline: {args.start} to {args.end} ({len(date_chunks)} chunks):")
    for chunk_label, c_start, c_end in date_chunks:
        print(f"  Chunk {chunk_label}: {c_start} -> {c_end}")

    # Process each chunk and batch
    batch_size = args.batch_size
    num_batches = (total_dsds + batch_size - 1) // batch_size
    total_steps = len(date_chunks) * num_batches
    step = 0

    print(f"\nTotal tasks: {len(date_chunks)} time chunks x {num_batches} DSD batches = {total_steps} requests.")

    try:
        for chunk_label, c_start, c_end in date_chunks:
            print(f"\n================ Processing Chunk {chunk_label} ({c_start} to {c_end}) ================")
            for b_idx in range(num_batches):
                step += 1
                start_i = b_idx * batch_size
                end_i = min(start_i + batch_size, total_dsds)
                batch_df = dsd_master.iloc[start_i:end_i].copy()

                cache_file = cache_dir / f"chunk_{chunk_label}_batch_{b_idx:02d}.parquet"

                if cache_file.exists():
                    print(f"[{step}/{total_steps}] [CACHED] Chunk {chunk_label} Batch {b_idx + 1}/{num_batches} (DSDs {start_i + 1}-{end_i})")
                    continue

                print(f"[{step}/{total_steps}] Fetching Chunk {chunk_label} Batch {b_idx + 1}/{num_batches} ({len(batch_df)} DSDs: {batch_df['dsd_name'].iloc[0]} to {batch_df['dsd_name'].iloc[-1]})...")
                
                try:
                    t0 = time.time()
                    resp = fetch_batch_data(
                        batch_df["latitude"].tolist(),
                        batch_df["longitude"].tolist(),
                        c_start,
                        c_end
                    )
                    df_daily = process_batch_response(resp, batch_df)
                    df_daily.to_parquet(cache_file, index=False)
                    elapsed = time.time() - t0
                    print(f"    -> Done in {elapsed:.2f}s, saved {len(df_daily)} daily records to {cache_file.name}")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"    !! Error processing batch {b_idx} in chunk {chunk_label}: {e}")
                    raise e

                # Be courteous to Open-Meteo public endpoints
                time.sleep(3.5)
    except KeyboardInterrupt:
        print("\n[Paused] Saving and compiling all downloaded data so far...")

    # Merge all cached parquets into final master CSV
    print("\nMerging all cached batches into master dataset...")
    cache_files = sorted(list(cache_dir.glob("chunk_*_batch_*.parquet")))
    if not cache_files:
        sys.exit("Error: No cached parquet files found to merge.")

    all_dfs = [pd.read_parquet(f) for f in cache_files]
    merged_df = pd.concat(all_dfs, ignore_index=True)

    # Same column order, de-duplication and yearly files as the daily updater
    merged_df = save_dataset(merged_df[merged_df["aqi_category"] != "Unknown"], Path(args.output_dir))

    print("\n================ DATASET GENERATION COMPLETE ================")
    print(f"Output folder:     {Path(args.output_dir).resolve()} (one CSV per year)")
    print(f"Date Range:        {merged_df['date'].min()} to {merged_df['date'].max()}")
    print(f"Total Records:     {len(merged_df):,}")
    print(f"Unique DSDs:       {merged_df['dsd_name'].nunique()} (across {merged_df['district_name'].nunique()} districts, {merged_df['province_name'].nunique()} provinces)")
    print("\nAQI Category Breakdown:")
    print(merged_df["aqi_category"].value_counts(dropna=False).to_string())
    print("\nSample records:")
    print(merged_df[["date", "district_name", "dsd_name", "pm2_5_mean", "pm10_mean", "us_aqi_max", "aqi_category"]].head(5))


if __name__ == "__main__":
    main()
