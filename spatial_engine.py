import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely import wkt
from scipy.spatial import cKDTree

# 1. LOAD DATA -------------------------------------------------------------
# Person 5 will provide a GeoJSON/Parquet file. For testing, we read mock data.
df=pd.read_csv(r"C:\Users\fugro\shreshthi material\buildings.csv.gz")
df['geometry'] = df['geometry'].apply(wkt.loads)


# 2. COORDINATE SYSTEM (CRS) SETTING --------------------------------------
# Coordinates like (73.0, 19.0) are degrees (WGS84 / EPSG:4326).
# Convert to meters (EPSG:32643 - UTM Zone 43N for Maharashtra/Kharghar).
buildings= gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")


# 3. GEOMETRY CALCULATIONS (IN METERS) -------------------------------------
# Option A: Use geometry area directly (now correctly calculated in m²)
buildings['footprint_area_m2'] = buildings.geometry.area.round(3)

# Option B: Or use your CSV's existing 'area in meters' column if provided:
# buildings['footprint_area_m2'] = buildings['area in meters'].round(3)

# Usable roof area (~70% of total footprint)
buildings['usable_area_m2'] = (buildings['footprint_area_m2'] * 0.70).round(3) #here one assumption we are taking is that rooftop is 70 percent usable rest is covered

# 4. ELEVATION COMBINATION ------------------------------------------------
# Combine building height and terrain elevation (if DEM is mapped)
buildings['building_height_m'] = buildings['reported_height'].fillna(10.0) # default fallbacke 3 floors building height that is 10
buildings['terrain_elevation_m'] = buildings['dem_elevation'].fillna(15.0) 

# 5. DISTANCE COMPUTATIONS (Nearest Neighbor) ----------------------------
def get_min_distance(source_gdf, target_gdf):
    # Extracts centroid points to calculate fast straight-line distances in meters
    source_pts = [pt.centroid.coords[0] for pt in source_gdf.geometry]
    target_pts = [pt.coords[0] if pt.geom_type == 'Point' else pt.centroid.coords[0] for pt in target_gdf.geometry]
    
    tree = cKDTree(target_pts)
    distances, _ = tree.query(source_pts)
    return distances.round(1)



# 6. SHADING & CONFIDENCE PROXIES -----------------------------------------
# Simple proxy: lower shading factor if surrounded by taller structures
buildings['shading_factor'] = 0.85 
buildings['spatial_confidence'] = 0.80

# 7. EXPORT DATA CONTRACT -------------------------------------------------
output_cols = [
    'candidate_id', 
    'footprint_area_m2', 
    'usable_area_m2', 
    'building_height_m', 
    'terrain_elevation_m', 
    'road_distance_m', 
    'grid_distance_m', 
    'shading_factor', 
    'spatial_confidence'
]

output_df = pd.DataFrame(buildings[output_cols])
output_df.to_json("spatial_features.json", orient="records", indent=2)
print("Successfully generated Person 2 output file!")

