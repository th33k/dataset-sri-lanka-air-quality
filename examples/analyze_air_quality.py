"""
Quickstart Analysis: Sri Lanka DSD Air Quality Dataset.

Demonstrates how to load the dataset, filter by district/province,
compute key environmental metrics, and inspect air quality trends.
"""

from pathlib import Path
import pandas as pd

# 1. Load the processed dataset (one CSV per year)
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
files = sorted(DATA_DIR.glob("sri_lanka_dsd_air_quality_*.csv"))
if not files:
    raise FileNotFoundError(f"No dataset files found in {DATA_DIR}.")

print(f"Loading {len(files)} yearly files from data/processed/ ...")
df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)

print(f"Loaded {len(df):,} records spanning {df['date'].min()} to {df['date'].max()}.")
print(f"Coverage: {df['dsd_name'].nunique()} DSDs, {df['district_name'].nunique()} districts, {df['province_name'].nunique()} provinces.\n")

# 2. Top 5 Most Polluted Districts by Average PM2.5
print("=" * 60)
print("Top 5 Districts by Mean PM2.5 (ug/m3):")
print("=" * 60)
district_pm25 = (
    df.groupby("district_name")["pm2_5_mean"]
    .agg(["mean", "max"])
    .rename(columns={"mean": "avg_pm2_5", "max": "peak_pm2_5"})
    .sort_values("avg_pm2_5", ascending=False)
    .head(5)
    .round(2)
)
print(district_pm25)

# 3. Air Quality Index (AQI) Category Distribution
print("\n" + "=" * 60)
print("Overall AQI Category Distribution:")
print("=" * 60)
aqi_counts = df["aqi_category"].value_counts(normalize=True) * 100
for cat, pct in aqi_counts.items():
    print(f"  - {cat:32s}: {pct:5.2f}%")

# 4. Filter Specific DSD (e.g., Colombo DSD)
colombo_dsd = df[df["dsd_name"] == "Colombo"].copy()
print("\n" + "=" * 60)
print(f"Recent Observations for Colombo DSD (Total: {len(colombo_dsd)} days):")
print("=" * 60)
cols = ["date", "pm2_5_mean", "pm10_mean", "nitrogen_dioxide_mean", "us_aqi_max", "aqi_category"]
print(colombo_dsd[cols].tail(5).to_string(index=False))
