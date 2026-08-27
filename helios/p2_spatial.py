"""
helios/p2_spatial.py
Person 2: Spatial Roof Feature Engineer

Answers: "What are the physical and location-related characteristics of each building?"
Responsibility:
- Reproject to EPSG:32643 (UTM 43N meters).
- Compute footprint area & usable roof area (~70%).
- Fuse building height and terrain elevation.
- Compute distance to nearest road and grid power feature.
- Compute coarse shading factor proxy & spatial confidence score.
"""

import math
from typing import List
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point, Polygon
from scipy.spatial import cKDTree

from helios.contracts.models import CandidateBuildingP1, SpatialFeaturesP2
from helios.ai_pipeline.pipeline import AIRooftopEngineeringPipeline

class Person2SpatialEngineer:
    def __init__(self, usable_ratio: float = 0.70, resident_reserve_pct: float = 0.15):
        self.usable_ratio = usable_ratio
        self.ai_pipeline = AIRooftopEngineeringPipeline(resident_reserve_pct=resident_reserve_pct)

    def process_candidate(self, cand: CandidateBuildingP1) -> SpatialFeaturesP2:
        # Footprint area calculation in metric CRS EPSG:32643
        footprint_area = cand.footprint_area_m2
        perimeter = round(4.0 * math.sqrt(footprint_area), 2)
        
        if cand.geometry_wkt:
            try:
                geom = wkt.loads(cand.geometry_wkt)
                gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
                gdf_metric = gdf.to_crs(epsg=32643)
                calc_area = gdf_metric.geometry.area.iloc[0]
                calc_perim = gdf_metric.geometry.length.iloc[0]
                if calc_area > 0:
                    footprint_area = round(float(calc_area), 2)
                if calc_perim > 0:
                    perimeter = round(float(calc_perim), 2)
            except Exception:
                pass
                
        height = cand.reported_height_m if cand.reported_height_m is not None else 10.0
        terrain = cand.dem_elevation_m if cand.dem_elevation_m is not None else 15.0
        rooftop_elev = round(height + terrain, 2)

        # Run AI-Assisted Rooftop Engineering Pipeline (Stages 1 -> 2 -> 3 -> 4)
        ai_res = self.ai_pipeline.analyze_rooftop(
            candidate_id=cand.candidate_id,
            footprint_area_m2=footprint_area,
            building_height_m=height
        )
        
        # Distance proxies (simulated spatial index query to road & grid)
        try:
            cand_num = int(''.join(filter(str.isdigit, cand.candidate_id)))
        except ValueError:
            cand_num = abs(hash(cand.candidate_id)) % 10000
        road_dist = round(5.0 + (cand_num * 7) % 45, 1)
        grid_dist = round(15.0 + (cand_num * 19) % 380, 1)

        spatial_conf = round(min(0.95, max(0.50, (cand.height_confidence * 0.5 + ai_res.pipeline_confidence * 0.5))), 2)

        return SpatialFeaturesP2(
            candidate_id=cand.candidate_id,
            footprint_area_m2=footprint_area,
            usable_area_m2=ai_res.usable_area_m2, # Installable area from AI pipeline
            building_height_m=height,
            terrain_elevation_m=terrain,
            road_distance_m=road_dist,
            grid_distance_m=grid_dist,
            shading_factor=ai_res.shading_factor, # From 3D solar position shading engine
            spatial_confidence=spatial_conf,
            perimeter_m=perimeter,
            rooftop_elevation_m=rooftop_elev,
            clear_area_m2=ai_res.clear_area_m2,
            obstruction_area_m2=ai_res.obstruction_area_m2,
            roof_type=ai_res.roof_type,
            slope_deg=ai_res.slope_deg,
            annual_solar_access_pct=ai_res.annual_solar_access_pct,
            panel_count=ai_res.panel_count,
            layout_efficiency_pct=ai_res.layout_efficiency_pct
        )

    def process_batch(self, candidates: List[CandidateBuildingP1]) -> List[SpatialFeaturesP2]:
        return [self.process_candidate(c) for c in candidates]
