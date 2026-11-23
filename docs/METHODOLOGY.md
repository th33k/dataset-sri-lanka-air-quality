# Methodology: Sri Lanka DSD-Level Air Quality Dataset

This document explains the data sources, spatial processing and daily aggregation used to build the dataset, and its main limitations.

---

## 1. Administrative Boundaries

### Source: UN OCHA and Survey Department of Sri Lanka
Divisions come from the Sri Lanka Common Operational Dataset for Administrative Boundaries (COD-AB), published by UN OCHA with the Survey Department of Sri Lanka (see [`data/raw/README.md`](../data/raw/README.md)).

- **Hierarchy:**
  - Country (Admin Level 0, `LK`)
  - Provinces (Admin Level 1, 9 units, `LK1`–`LK9`)
  - Districts (Admin Level 2, 25 units, `LK11`–`LK92`)
  - Divisional Secretariat Divisions (Admin Level 3, 339 units, `LK1103`–`LK9233`)
- **Point location:** each DSD is represented by the geometric centroid of its polygon (WGS84, EPSG:4326), stored in [`data/reference/sri_lanka_dsd_reference.csv`](../data/reference/sri_lanka_dsd_reference.csv). Air quality is requested at that point.

---

## 2. Atmospheric Data

### Copernicus Atmosphere Monitoring Service (CAMS), via Open-Meteo
Hourly values come from the [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api), which serves the CAMS global atmospheric composition model run by ECMWF.

- **Model data, not ground measurements:** CAMS combines a chemical transport model with assimilated satellite observations (for example aerosol optical depth and trace-gas columns). Values are model estimates at each point, not readings from monitoring stations.
- **Grid resolution:** about 0.4° (roughly 40–45 km). Every point inside the same grid cell receives the same values (see Limitations).
- **Time zone:** requested in `Asia/Colombo` (UTC+05:30), so each calendar day runs from 00:00 to 23:00 Sri Lanka time.
- **Variables requested (hourly):** `pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `ozone`, `carbon_monoxide`, `aerosol_optical_depth`, `dust`, `uv_index`, `us_aqi`.

---

## 3. Daily Aggregation

For each DSD $i$ and calendar day $d$, the hourly values $X_{i,d,h}$ ($h = 0, \dots, 23$) are reduced to daily statistics:

1. **Daily mean:** $\mu_{i,d} = \frac{1}{N} \sum_{h} X_{i,d,h}$, where $N$ is the number of non-missing hourly values that day (normally 24).
2. **Daily extremes:** $\text{Min}_{i,d} = \min_h X_{i,d,h}$ and $\text{Max}_{i,d} = \max_h X_{i,d,h}$.
3. **Rounding:** all aggregated values are rounded to 2 decimal places.

Which statistics are kept per variable is listed in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

### US AQI
The hourly `us_aqi` value is computed by Open-Meteo from the pollutant concentrations using US EPA breakpoints. Each pollutant's sub-index uses its standard averaging window (for example 24 hours for PM2.5 and PM10), and the hourly AQI is the highest sub-index. This dataset does **not** recompute the AQI; it stores the daily mean (`us_aqi_mean`) and daily maximum (`us_aqi_max`) of Open-Meteo's hourly values. `aqi_category` is assigned from `us_aqi_max` using the US EPA category bands.

Because the particulate sub-indices use 24-hour rolling averages, consecutive days' AQI values are strongly correlated.

---

## 4. Completeness and Updates

- **Coverage:** every DSD on every day from 2023-01-01 to the last complete day. The dataset has no missing values.
- **Completed days only:** for today and future dates Open-Meteo returns CAMS *forecasts*, so those days are never stored. The latest date in the dataset is always yesterday (Sri Lanka time) or earlier.
- **Daily update:** [`scripts/daily_update.py`](../scripts/daily_update.py) runs every day through GitHub Actions. It fills any missing (date, DSD) pair, re-fetches the last 3 days in case values were revised, and keeps partial progress if the API rate limit is reached.

---

## 5. Collection Pipeline

[`scripts/collect_srilanka_dsd_air_quality.py`](../scripts/collect_srilanka_dsd_air_quality.py) rebuilds the dataset for any date range:

- **Batching:** 25 DSD points per API request.
- **Checkpoints:** each year-and-batch result is saved to `data/cache_dsd/*.parquet` (not committed). An interrupted run skips batches already downloaded.
- **Retries:** waits and retries on rate-limit (HTTP 429) and network errors.
- **Output:** one CSV per year in `data/processed/`, in the same format as the daily updater.

---

## 6. Limitations

- **Shared values within a grid cell:** CAMS cells are about 45 km wide, so many DSDs fall into the same cell and have identical time series. The 339 DSDs currently map to **47 distinct series**. Treat DSD-level differences within a district with care; the data cannot resolve variation finer than the grid.
- **Model estimates:** values are not station measurements and can differ from local monitors, especially near strong local sources such as busy roads or industry.
- **Point sampling:** each DSD is sampled at a single centroid, not averaged over its whole area.
