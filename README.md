<div align="center">

# dataset-sri-lanka-air-quality
### A High-Resolution Spatiotemporal Air Quality and Atmospheric Pollutant Dataset for Sri Lanka at the Divisional Secretariat Division (DSD) Level (2023–2026)

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Auto-Update](https://img.shields.io/badge/Auto--Update-Daily%20(08:30%20SLST)-brightgreen.svg)](#6-automated-continuous-integration-pipeline-github-actions)
[![Spatial Coverage](https://img.shields.io/badge/Coverage-339%20DSDs%20%7C%2025%20Districts-blue.svg)](#1-introduction-and-overview)
[![Temporal Coverage](https://img.shields.io/badge/Temporal-2023--2026-green.svg)](#3-dataset-schema-and-variable-specifications)
[![Format](https://img.shields.io/badge/Format-CSV-orange.svg)](#3-dataset-schema-and-variable-specifications)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#5-usage-and-quickstart-guide)

</div>

---

## Dataset Profile

| Attribute | Specification |
| :--- | :--- |
| **Identifier** | `dataset-sri-lanka-air-quality` |
| **Formal Title** | A High-Resolution Spatiotemporal Air Quality and Atmospheric Pollutant Dataset for Sri Lanka at the Divisional Secretariat Division (DSD) Level (2023–2026) |
| **Spatial Coverage** | All 339 Divisional Secretariat Divisions (339 DSDs, 25 Districts, 9 Provinces) |
| **Temporal Coverage** | 2023-01-01 to the last complete day (yesterday), updated daily |
| **Temporal Resolution** | Daily statistics (mean, minimum, maximum) from hourly values |
| **Primary Sources** | Copernicus Atmosphere Monitoring Service (ECMWF CAMS) & Survey Dept of Sri Lanka / UN OCHA (COD-AB) |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |

---

## 1. Introduction and Overview

Sri Lanka has only a small number of ground-level air quality monitoring stations, mostly in a few urban centres, so most of the country has no continuous measurements.

This dataset addresses this spatial observational constraint by providing division-level environmental metrics for all **339 Divisional Secretariat Divisions (DSDs)** (Administrative Level 3) across all **25 Districts** and **9 Provinces** of Sri Lanka.

The dataset couples two authoritative primary data sources:
1. **Subnational Boundaries:** Official subnational boundary geometries and P-codes from the **Survey Department of Sri Lanka** and **United Nations OCHA** (Common Operational Datasets - COD-AB Level 3).
2. **Atmospheric Composition Model:** The global atmospheric composition model of the **Copernicus Atmosphere Monitoring Service (CAMS)**, run by the European Centre for Medium-Range Weather Forecasts (ECMWF), accessed through the Open-Meteo Air Quality API.

> **Note on resolution:** values are model estimates on a ~45 km grid, not station measurements. DSDs that fall in the same grid cell share identical values; the 339 DSDs currently map to 47 distinct series. See [Limitations](docs/METHODOLOGY.md#6-limitations).

---

## 2. Repository Architecture

```text
├── data/
│   ├── reference/
│   │   └── sri_lanka_dsd_reference.csv        # Spatial master table of 339 DSDs with UN P-codes and WGS84 centroids
│   ├── processed/
│   │   ├── sri_lanka_dsd_air_quality_<year>.csv   # Primary daily dataset, one CSV per year (2023, 2024, ...)
│   │   └── sri_lanka_district_air_quality_summary.csv # District-level benchmark aggregations
│   └── raw/
│       └── README.md                          # Source boundary data provenance and download instructions
├── docs/
│   ├── DATA_DICTIONARY.md                     # Definitions of all 32 columns
│   └── METHODOLOGY.md                         # Sources, daily aggregation, update process, limitations
├── examples/
│   └── analyze_air_quality.py                 # Reproducible Python analysis and summary script
├── scripts/
│   ├── collect_srilanka_dsd_air_quality.py    # Automated batch ingestion and caching pipeline
│   ├── daily_update.py                        # Automated incremental daily synchronization script
│   └── resume_dataset_collection.bat          # Windows batch execution script
├── .github/workflows/daily_update.yml        # Daily automatic update (GitHub Actions)
├── .gitignore                                 # Cache and temporary file exclusions
├── LICENSE                                    # Creative Commons Attribution 4.0 International (CC BY 4.0)
├── README.md                                  # Repository documentation and academic index
└── requirements.txt                           # Software dependencies
```

---

## 3. Dataset Schema and Variable Specifications

The primary dataset is stored as one CSV per year in [`data/processed/`](data/processed/) (`sri_lanka_dsd_air_quality_<year>.csv`) (all files share the same **32 attributes**; splitting by year keeps each file well under GitHub's 100 MB limit):

- **Administrative Identifiers:** `date`, `province_name`, `province_pcode`, `district_name`, `district_pcode`, `dsd_name`, `dsd_pcode`, `latitude`, `longitude`, `area_sqkm`
- **Particulate Pollutants ($\mu\text{g/m}^3$):** `pm2_5_mean`, `pm2_5_min`, `pm2_5_max`, `pm10_mean`, `pm10_min`, `pm10_max`
- **Gaseous Pollutants ($\mu\text{g/m}^3$):** `nitrogen_dioxide_mean/max`, `sulphur_dioxide_mean/max`, `ozone_mean/max`, `carbon_monoxide_mean/max`
- **Atmospheric Measures:** `aerosol_optical_depth_mean/max`, `dust_mean/max`, `uv_index_max`
- **Air Quality Index:** `us_aqi_mean`, `us_aqi_max`, `aqi_category` (*Good*, *Moderate*, *Unhealthy for Sensitive Groups*, *Unhealthy*, *Very Unhealthy*, *Hazardous*)

*For units and definitions of every column, see [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md). For sources, aggregation and limitations, see [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).*

---

## 4. Subnational Administrative Benchmarks

District averages over the full record (2023-01-01 to 2026-11-22), from [`data/processed/sri_lanka_district_air_quality_summary.csv`](data/processed/sri_lanka_district_air_quality_summary.csv), which the daily update keeps current. Values here are a snapshot.

| Province | District | DSDs | Mean PM2.5 (µg/m³) | Peak PM2.5 (µg/m³) | Mean AQI | Peak AQI |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Western | Colombo | 13 | 20.97 | 82.0 | 75.6 | 232 |
| Western | Kalutara | 14 | 19.84 | 82.0 | 73.1 | 232 |
| Western | Gampaha | 13 | 18.95 | 91.3 | 71.1 | 232 |
| Sabaragamuwa | Kegalle | 11 | 17.76 | 89.2 | 66.1 | 174 |
| Southern | Galle | 22 | 15.78 | 80.8 | 63.6 | 218 |
| Central | Kandy | 20 | 14.94 | 103.6 | 59.4 | 167 |
| North Western | Kurunegala | 30 | 14.55 | 163.9 | 59.1 | 223 |
| North Western | Puttalam | 16 | 14.31 | 231.4 | 59.0 | 223 |
| Sabaragamuwa | Ratnapura | 18 | 13.97 | 80.8 | 56.9 | 174 |
| Southern | Matara | 16 | 13.68 | 80.8 | 57.5 | 175 |
| Central | Matale | 11 | 13.66 | 103.6 | 56.4 | 159 |
| Central | Nuwara Eliya | 10 | 13.20 | 84.8 | 55.1 | 174 |
| Northern | Jaffna | 15 | 12.69 | 77.8 | 53.9 | 203 |
| Northern | Mannar | 5 | 11.78 | 69.2 | 51.9 | 169 |
| Northern | Kilinochchi | 4 | 11.74 | 70.5 | 50.9 | 179 |
| Uva | Badulla | 15 | 11.61 | 84.8 | 51.1 | 157 |
| Eastern | Ampara | 19 | 11.45 | 72.2 | 51.2 | 146 |
| Eastern | Batticaloa | 14 | 11.36 | 71.5 | 50.9 | 132 |
| North Central | Polonnaruwa | 7 | 11.30 | 80.8 | 50.3 | 150 |
| North Central | Anuradhapura | 22 | 11.12 | 231.4 | 49.5 | 176 |
| Uva | Monaragala | 11 | 11.11 | 70.1 | 49.8 | 145 |
| Southern | Hambantota | 12 | 11.06 | 56.8 | 50.5 | 166 |
| Northern | Mullaitivu | 6 | 10.65 | 60.1 | 47.6 | 150 |
| Eastern | Trincomalee | 11 | 10.52 | 67.1 | 47.8 | 139 |
| Northern | Vavuniya | 4 | 10.36 | 60.3 | 46.7 | 138 |

---

## 5. Usage and Quickstart Guide

### Environment Setup
```bash
pip install -r requirements.txt
```

### Exploratory Data Loading in Python
```python
import pandas as pd

# Load dataset (all yearly files)
from pathlib import Path
df = pd.concat(pd.read_csv(f) for f in sorted(Path("data/processed").glob("sri_lanka_dsd_air_quality_*.csv")))

# Filter for Western Province
western_df = df[df["province_name"] == "Western"]

# Compute monthly mean PM2.5 in Colombo District
df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
colombo_monthly = df[df["district_name"] == "Colombo"].groupby("month")["pm2_5_mean"].mean()
print(colombo_monthly)
```

### Execution of Example Analysis Script
```bash
python examples/analyze_air_quality.py
```

---

## 6. Automated Continuous Integration Pipeline (GitHub Actions)

This repository includes a scheduled **GitHub Actions CI/CD workflow** ([`.github/workflows/daily_update.yml`](.github/workflows/daily_update.yml)) that runs **daily at 03:00 AM Sri Lanka Standard Time (21:30 UTC)**; GitHub may start scheduled runs late:

1. **Completed days only:** Keeps observations from 2023-01-01 up to *yesterday* (Asia/Colombo). Today and future dates are CAMS forecasts and are never stored.
2. **Gap repair:** Finds every missing (date, DSD) pair in that window and fetches only those date ranges, then re-fetches the last 3 days in case values were revised.
3. **Rate-limit safe:** If the Open-Meteo limit is hit, progress so far is kept and the next run continues from there.
4. **Automated Commit:** Commits refreshed dataset files as `github-actions[bot]` with `[skip ci]`.
5. **Manual Dispatch:** Supports on-demand manual triggering from the GitHub **Actions** interface.

---

## 7. Data Collection and Reproduction

To reproduce or extend data collection over custom time intervals:

```bash
python scripts/collect_srilanka_dsd_air_quality.py --start 2023-01-01
```

- **End date:** defaults to yesterday and is capped there; today and future dates are forecasts, not observations.

- **Checkpoint Cache:** Downloaded batches are preserved in `data/cache_dsd/*.parquet` to prevent data loss or duplicate network queries.
- **Windows Environments:** Execute `scripts/resume_dataset_collection.bat` to launch with preconfigured arguments.

---

## 8. Citation

If using this dataset in academic publications, theses, environmental impact assessments, or policy briefs, please cite:

```bibtex
@dataset{dataset_sri_lanka_air_quality_2026,
  author       = {{Sri Lanka Environmental Open Data Contributors}},
  title        = {A High-Resolution Spatiotemporal Air Quality and
                  Atmospheric Pollutant Dataset for Sri Lanka at the
                  Divisional Secretariat Division (DSD) Level (2023--2026)},
  year         = {2026},
  publisher    = {GitHub},
  version      = {1.0.0},
  howpublished = {\url{https://github.com/th33k/dataset-sri-lanka-air-quality}},
  note         = {Data sources: Copernicus Atmosphere Monitoring Service
                  (CAMS) and UN OCHA / Survey Department of Sri Lanka}
}
```

---

## 9. License and Data Attribution

This dataset is licensed under the **[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE)** license.

### Attribution Statement:
- **Atmospheric Data:** Copernicus Atmosphere Monitoring Service (CAMS), European Centre for Medium-Range Weather Forecasts (ECMWF), and Open-Meteo.
- **Administrative Boundary Data:** Survey Department of Sri Lanka and United Nations Office for the Coordination of Humanitarian Affairs (UN OCHA, COD-AB Level 3).
