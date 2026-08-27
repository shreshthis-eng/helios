"""
helios/contracts/models.py
Standardized data contracts and data transfer objects for Helios.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

@dataclass
class CandidateBuildingP1:
    candidate_id: str
    latitude: float
    longitude: float
    footprint_area_m2: float
    reported_height_m: Optional[float] = None
    height_confidence: float = 0.75
    dem_elevation_m: float = 15.0
    road_layer_available: bool = True
    power_layer_available: bool = True
    source_ids: List[str] = field(default_factory=lambda: ["GOBS", "OSM"])
    geometry_wkt: str = ""

@dataclass
class SpatialFeaturesP2:
    candidate_id: str
    footprint_area_m2: float
    usable_area_m2: float
    building_height_m: float
    terrain_elevation_m: float
    road_distance_m: float
    grid_distance_m: float
    shading_factor: float
    spatial_confidence: float
    perimeter_m: float = 0.0
    rooftop_elevation_m: float = 0.0
    clear_area_m2: float = 0.0
    obstruction_area_m2: float = 0.0
    roof_type: str = "FLAT"
    slope_deg: float = 0.0
    annual_solar_access_pct: float = 85.0
    panel_count: int = 0
    layout_efficiency_pct: float = 0.0

@dataclass
class SolarEconomicsP3:
    candidate_id: str
    estimated_capacity_kwp: float
    annual_yield_kwh: float
    estimated_capex_inr: float
    estimated_rent_inr_month: float
    indicative_payback_years: float
    solar_confidence: float
    economics_confidence: float

@dataclass
class RankingResultP4:
    candidate_id: str
    eligible: bool
    generation_score: float
    physical_score: float
    grid_score: float
    economic_score: float
    confidence_score: float
    total_score: float
    rank: int
    positive_reasons: List[str] = field(default_factory=list)
    cautions: List[str] = field(default_factory=list)
    exclusion_reason: Optional[str] = None

@dataclass
class IntegratedCandidate:
    candidate_id: str
    latitude: float
    longitude: float
    geometry_wkt: str
    p1: Dict[str, Any]
    p2: Dict[str, Any]
    p3: Dict[str, Any]
    p4: Dict[str, Any]
    human_review_label: str = "unreviewed" # inspect, uncertain, reject
    human_notes: str = ""
