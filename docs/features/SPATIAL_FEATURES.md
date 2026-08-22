# Spatial Roof Feature Dictionary (Person 2 Deliverable)

**Module**: `helios.p2_spatial.Person2SpatialEngineer`  
**Area of Interest (AOI)**: Kharghar (EPSG:4326 -> EPSG:32643 UTM Zone 43N)

---

## Output Contract & Feature Dictionary

| Field Name | Type | Unit | Formula / Method | Direction | Null Policy | Provenance | Confidence Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `candidate_id` | String | N/A | Unique permanent identifier (e.g. `KHAR_000123`) | N/A | Required | Person 1 Ingestion | 1.00 |
| `footprint_area_m2` | Float | m² | Polylabel projected area in EPSG:32643 UTM 43N | Larger is better | Fallback to source area | GOBS / Open Buildings | Height & resolution dependent |
| `usable_area_m2` | Float | m² | `footprint_area_m2 * 0.70` (30% setback assumption) | Larger is better | Derived | Calculation | Inherited from footprint |
| `perimeter_m` | Float | m | Ground polygon boundary perimeter length in meters | Contextual | Calculated / Fallback | Geometry WKT | Inherited from footprint |
| `building_height_m` | Float | m | Combined height observation fusion from sources | Contextual | Fallback to 10.0 m | GOBS / OSM height | Source height confidence |
| `terrain_elevation_m` | Float | m | DEM raster sampling at building centroid | Contextual | Fallback to 15.0 m | Copernicus DEM | DEM resolution confidence |
| `rooftop_elevation_m` | Float | m | `building_height_m + terrain_elevation_m` | Higher is less shade | Derived | Calculation | Combined height & DEM |
| `road_distance_m` | Float | m | cKDTree nearest neighbour distance to mapped OSM road | Smaller is better | Fallback | OSM Road Layer | Spatial index accuracy |
| `grid_distance_m` | Float | m | cKDTree distance to nearest mapped power line / substation | Smaller is better | Fallback | OSM Power Layer | Proxy distance limit |
| `shading_factor` | Float | 0–1 | Heights & surrounding obstacle obstruction proxy ratio | Higher (1.0 = clear) | Default 0.85 | Coarse proxy model | Proxy heuristic |
| `spatial_confidence` | Float | 0–1 | `min(0.95, max(0.50, height_confidence * 0.9 + 0.1))` | Higher is better | Default 0.75 | Multi-factor fusion | Deterministic composite |

---

## Artifact Exports & Downstream Handoff

Person 2 exports the spatial features in two contract formats:
1. `spatial_features.json`: JSON array fixture consumed by Person 3, Person 4, and Person 5.
2. `spatial_features.parquet`: High-performance binary columnar format for large-scale Kharghar batches.

Both artifacts pass downstream loaders for Person 3 (Solar & Economics) and Person 4 (Ranking Engine) with zero manual renaming.
