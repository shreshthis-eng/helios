# ☀️ Helios - Solar Rooftop Prospecting & Ranking Platform

**Helios** is an end-to-end solar rooftop prospecting and multi-criteria candidate ranking application for Kharghar, Navi Mumbai. It evaluates 30,000+ building footprints using metric spatial feature extraction, physics-based solar generation modeling, financial feasibility analysis, and dynamic multi-scenario ranking.

---

## 🏗️ 6-Role Decoupled Architecture

Helios is structured into 6 modular, independent engineering roles:

| Role | Module | Responsibility | Key Output |
| :--- | :--- | :--- | :--- |
| **Person 1** | `helios.p1_gis` | Data & GIS Engineer | Ingests building polygons, clips boundary box, assigns permanent IDs (`KHAR_000123`), fuses DEM elevation & height. |
| **Person 2** | `helios.p2_spatial` | Spatial Roof Feature Engineer | Metric reprojection (**EPSG:32643 UTM 43N**), calculates footprint area, 70% usable roof area, perimeter, road & grid distances, shading factor, and spatial confidence. |
| **Person 3** | `helios.p3_solar_economics` | Solar & Economics Engineer | Converts roof area to kWp capacity, calculates annual kWh yield, CapEx, monthly roof lease rent, payback years, and confidence metrics. |
| **Person 4** | `helios.p4_ranking` | Ranking & ML Engineer | Hard eligibility filtering, 4-scenario score normalization (Balanced, Energy-First, Cost-First, Accessibility-First), deterministic explanation generator, and RandomForest ML ranker fallback. |
| **Person 5** | `helios.p5_integration` | Integration & Platform Engineer | Pydantic/dataclass data contracts, SQLite database storage (`helios_database.sqlite`), REST API backend (`server.py`), and interactive Leaflet map dashboard (`public/index.html`). |
| **Person 6** | `helios.p6_validation` | Validation & Demo Owner | Human review labeling (`inspect`, `uncertain`, `reject`), traditional manual scouting vs. Helios automated benchmarking report (`VALIDATION_REPORT.md`). |

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install geopandas pandas shapely scipy scikit-learn
```

### 2. Run the End-to-End Pipeline
Run the pipeline for 1,000 Kharghar building candidates using the `balanced` ranking scenario:
```bash
python run_pipeline.py 1000 balanced
```

To run with custom input data (GeoJSON / CSV / Shapefile / GeoPackage):
```bash
python run_pipeline.py 1000 balanced "path/to/custom_data.geojson"
```

### 3. Launch the REST API & Web Dashboard
```bash
python server.py
```
Open **`http://localhost:8000`** in your browser to view the interactive Leaflet map dashboard, inspect candidate scorecards, toggle ranking scenarios, and assign review labels!

---

## 🧪 Running Automated Tests
Run the unit and integration test suite:
```bash
python -m unittest discover tests
```

---

## 📄 Documentation Deliverables

- 📘 [Spatial Roof Feature Dictionary (Person 2)](docs/features/SPATIAL_FEATURES.md)
- 📊 [Validation & Benchmark Report (Person 6)](VALIDATION_REPORT.md)
