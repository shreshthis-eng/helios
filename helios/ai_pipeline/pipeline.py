"""
helios/ai_pipeline/pipeline.py
Unified Orchestrator for Helios AI-Assisted Rooftop Engineering Pipeline

Connects:
Stage 1: Roof-element & Obstruction Segmentation (Segmentation Model)
Stage 2: Roof-plane Geometry & Slope/Aspect Estimation (Geometry Model)
Stage 3: Time-Dependent 3D Solar Position Ray-Tracing (Shading Engine)
Stage 4: Code-Aware Constrained Panel Layout Optimization (Layout Optimizer)
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from helios.ai_pipeline.segmentation import RoofSegmentationModel, RoofObstructionBreakdown
from helios.ai_pipeline.roof_geometry import RoofGeometryModel, RoofPlaneGeometry
from helios.ai_pipeline.shading_engine import TimeDependentShadingEngine, TimeDependentShadingResult
from helios.ai_pipeline.layout_optimizer import CodeAwareLayoutOptimizer, PanelLayoutOptimizationResult, PanelSpecs

@dataclass
class AIRooftopAnalysisResult:
    candidate_id: str
    footprint_area_m2: float
    usable_area_m2: float            # Installable area from AI pipeline
    clear_area_m2: float
    obstruction_area_m2: float
    roof_type: str
    slope_deg: float
    true_surface_area_m2: float
    annual_solar_access_pct: float
    shading_factor: float
    panel_count: int
    installed_capacity_kwp: float
    layout_efficiency_pct: float
    unused_area_explanation: str
    pipeline_confidence: float
    stage1_segmentation: Dict[str, Any]
    stage2_geometry: Dict[str, Any]
    stage3_shading: Dict[str, Any]
    stage4_layout: Dict[str, Any]

class AIRooftopEngineeringPipeline:
    def __init__(
        self,
        resident_reserve_pct: float = 0.15,
        edge_setback_m: float = 1.0,
        maintenance_aisle_m: float = 0.8,
        min_solar_access_pct: float = 80.0
    ):
        self.stage1_model = RoofSegmentationModel(resident_reserve_pct=resident_reserve_pct)
        self.stage2_model = RoofGeometryModel()
        self.stage3_engine = TimeDependentShadingEngine()
        self.stage4_optimizer = CodeAwareLayoutOptimizer(
            edge_setback_m=edge_setback_m,
            maintenance_aisle_m=maintenance_aisle_m,
            min_solar_access_pct=min_solar_access_pct
        )

    def analyze_rooftop(
        self,
        candidate_id: str,
        footprint_area_m2: float,
        building_height_m: float = 15.0
    ) -> AIRooftopAnalysisResult:
        
        # Stage 1: Segmentation
        stg1 = self.stage1_model.segment_roof(candidate_id, footprint_area_m2, building_height_m)
        
        # Stage 2: Plane Geometry
        stg2 = self.stage2_model.estimate_plane_geometry(candidate_id, footprint_area_m2, building_height_m)
        
        # Stage 3: Time-Dependent Shading Simulation
        stg3 = self.stage3_engine.simulate_shading(
            candidate_id=candidate_id,
            footprint_area_m2=stg2.true_surface_area_m2,
            building_height_m=building_height_m,
            obstruction_area_m2=footprint_area_m2 - stg1.unobstructed_roof_m2
        )
        
        # Stage 4: Layout Optimization
        stg4 = self.stage4_optimizer.optimize_layout(
            footprint_area_m2=stg2.true_surface_area_m2,
            clear_area_m2=stg1.clear_area_m2,
            shaded_exclusion_m2=stg3.shaded_exclusion_area_m2,
            roof_slope_deg=stg2.slope_deg,
            solar_access_pct=stg3.annual_solar_access_pct
        )

        overall_conf = round((stg1.segmentation_confidence + stg2.geometry_confidence + stg3.shading_confidence) / 3.0, 2)

        return AIRooftopAnalysisResult(
            candidate_id=candidate_id,
            footprint_area_m2=footprint_area_m2,
            usable_area_m2=stg4.installable_area_m2,
            clear_area_m2=stg1.clear_area_m2,
            obstruction_area_m2=round(footprint_area_m2 - stg1.unobstructed_roof_m2, 1),
            roof_type=stg2.roof_type,
            slope_deg=stg2.slope_deg,
            true_surface_area_m2=stg2.true_surface_area_m2,
            annual_solar_access_pct=stg3.annual_solar_access_pct,
            shading_factor=stg3.shading_factor,
            panel_count=stg4.panel_count,
            installed_capacity_kwp=stg4.installed_capacity_kwp,
            layout_efficiency_pct=stg4.layout_efficiency_pct,
            unused_area_explanation=stg4.unused_area_explanation,
            pipeline_confidence=overall_conf,
            stage1_segmentation=asdict(stg1),
            stage2_geometry=asdict(stg2),
            stage3_shading=asdict(stg3),
            stage4_layout=asdict(stg4)
        )
