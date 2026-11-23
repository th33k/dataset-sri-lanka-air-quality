# Data Dictionary: Sri Lanka DSD-Level Air Quality Dataset

This document defines the 32 columns of the yearly files `data/processed/sri_lanka_dsd_air_quality_<year>.csv`. All files share the same columns, one row per DSD per day, with no missing values. Daily statistics are computed from hourly values over the Sri Lanka calendar day (see [`METHODOLOGY.md`](METHODOLOGY.md)).

---

## 1. Spatial and Administrative Identifiers

| Column Name | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `date` | `string (YYYY-MM-DD)` | `2024-03-15` | Observation date in Sri Lanka Standard Time (UTC+05:30). |
| `province_name` | `string` | `Western` | One of the 9 administrative Provinces of Sri Lanka. |
| `province_pcode` | `string` | `LK1` | Official UN OCHA standard administrative P-code for the Province. |
| `district_name` | `string` | `Colombo` | One of the 25 administrative Districts of Sri Lanka. |
| `district_pcode` | `string` | `LK11` | Official UN OCHA standard administrative P-code for the District. |
| `dsd_name` | `string` | `Kaduwela` | Name of the Divisional Secretariat Division (ADM Level 3). |
| `dsd_pcode` | `string` | `LK1103` | Official UN OCHA standard administrative P-code for the DSD. |
| `latitude` | `float` | `6.901985` | Latitude of the DSD polygon centroid (WGS84, decimal degrees). |
| `longitude` | `float` | `79.972773` | Longitude of the DSD polygon centroid (WGS84, decimal degrees). |
| `area_sqkm` | `float` | `87.72` | Geographic surface area of the division in square kilometers ($km^2$). |

---

## 2. Particulate Pollutants

| Column Name | Unit | Type | Description |
| :--- | :--- | :--- | :--- |
| `pm2_5_mean` | $\mu\text{g/m}^3$ | `float` | Daily 24-hour mean mass concentration of fine particles ($\le 2.5\,\mu\text{m}$). |
| `pm2_5_min` | $\mu\text{g/m}^3$ | `float` | Diurnal minimum hourly concentration of $\text{PM}_{2.5}$. |
| `pm2_5_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak (maximum) hourly concentration of $\text{PM}_{2.5}$. |
| `pm10_mean` | $\mu\text{g/m}^3$ | `float` | Daily 24-hour mean mass concentration of coarse respirable particles ($\le 10\,\mu\text{m}$). |
| `pm10_min` | $\mu\text{g/m}^3$ | `float` | Diurnal minimum hourly concentration of $\text{PM}_{10}$. |
| `pm10_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak (maximum) hourly concentration of $\text{PM}_{10}$. |

---

## 3. Gaseous Pollutants

| Column Name | Unit | Type | Description |
| :--- | :--- | :--- | :--- |
| `nitrogen_dioxide_mean` | $\mu\text{g/m}^3$ | `float` | Daily arithmetic mean concentration of Nitrogen Dioxide ($\text{NO}_2$). |
| `nitrogen_dioxide_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak hourly concentration of $\text{NO}_2$. |
| `sulphur_dioxide_mean` | $\mu\text{g/m}^3$ | `float` | Daily arithmetic mean concentration of Sulphur Dioxide ($\text{SO}_2$). |
| `sulphur_dioxide_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak hourly concentration of $\text{SO}_2$. |
| `ozone_mean` | $\mu\text{g/m}^3$ | `float` | Daily mean ground-level Ozone ($\text{O}_3$). |
| `ozone_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak hourly ground-level Ozone concentration. |
| `carbon_monoxide_mean` | $\mu\text{g/m}^3$ | `float` | Daily arithmetic mean concentration of Carbon Monoxide ($\text{CO}$). |
| `carbon_monoxide_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak hourly concentration of $\text{CO}$. |

---

## 4. Optical & Atmospheric Indicators

| Column Name | Unit | Type | Description |
| :--- | :--- | :--- | :--- |
| `aerosol_optical_depth_mean` | Dimensionless | `float` | Daily average total Aerosol Optical Depth at $550\text{ nm}$. |
| `aerosol_optical_depth_max` | Dimensionless | `float` | Diurnal peak Aerosol Optical Depth. |
| `dust_mean` | $\mu\text{g/m}^3$ | `float` | Daily average atmospheric mineral dust mass concentration. |
| `dust_max` | $\mu\text{g/m}^3$ | `float` | Diurnal peak atmospheric dust concentration. |
| `uv_index_max` | Index ($0-12+$) | `float` | Daily peak hourly UV index. |

---

## 5. Air Quality Index (AQI)

| Column Name | Unit | Type | Description |
| :--- | :--- | :--- | :--- |
| `us_aqi_mean` | Index ($0-500$) | `float` | Daily mean of Open-Meteo's hourly US AQI (each hour is the highest pollutant sub-index). |
| `us_aqi_max` | Index ($0-500$) | `integer` | Daily maximum of the hourly US AQI. |
| `aqi_category` | Category | `string` | US EPA category of `us_aqi_max` (bands below). |

### AQI Category Breakpoints (US EPA Standard)
- **Good (0 – 50):** Air quality is satisfactory; air pollution poses little or no risk.
- **Moderate (51 – 100):** Air quality is acceptable; moderate health concern for a very small number of sensitive individuals.
- **Unhealthy for Sensitive Groups (101 – 150):** Members of sensitive groups may experience health effects.
- **Unhealthy (151 – 200):** Some members of the general public may experience health effects; sensitive groups experience more serious effects.
- **Very Unhealthy (201 – 300):** Health alert: The risk of health effects is increased for everyone.
- **Hazardous (301+):** Health warning of emergency conditions: Everyone is more likely to be affected.

*Categories are assigned from the daily **maximum** AQI, so they describe the worst hour of the day, not the daily average.*
