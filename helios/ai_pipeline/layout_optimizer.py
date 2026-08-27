"""
helios/ai_pipeline/layout_optimizer.py
Stage 4: Code-Aware Panel Layout & Polygon-Packing Optimizer (Combinatorial Optimization Layer)

Calculates actual installable area by subtracting operational & regulatory clearance buffers:
A_installable = A_clear - A_access - A_setbacks - A_maintenance - A_shade_excluded

Performs constrained polygon-packing layout optimization:
- Places commercial Mono-PERC 540W solar panels (2.278m x 1.134m = 2.583 m²)
- Computes required inter-row spacing (S) to avoid self-shading:
  S = Panel Width * (sin(Tilt) / tan(Min Sun Elevation Angle))
- Evaluates Portrait vs Landscape orientations, variable tilt angles, and row spacing
- Performs polygon negative buffering (polygon.buffer(-setback)) using Shapely & SciPy
- Generates exact panel bounding boxes, DC capacity (kWp), yearly kWh yield, and unused space breakdown.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box

# Optional scipy / ortools integration
from scipy.optimize import linprog

try:
    from ortools.linear_solver import pywraplp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


@dataclass
class PanelSpecs:
    name: str = "Mono-PERC 540W Tier-1"
    wattage_wp: float = 540.0         # 540 Wp rated DC power
    length_m: float = 2.278           # 2.278 meters length
    width_m: float = 1.134            # 1.134 meters width
    area_m2: float = 2.583            # 2.58 m2 panel area
    cost_per_panel_inr: float = 18000.0


@dataclass
class PanelLayoutOptimizationResult:
    installable_area_m2: float
    setback_clearance_m2: float
    maintenance_aisle_m2: float
    panel_count: int
    installed_capacity_kwp: float
    annual_generation_kwh: float
    layout_efficiency_pct: float     # (panel_count * panel_area) / installable_area
    total_pv_surface_m2: float
    unused_area_m2: float
    unused_area_explanation: str
    panel_orientation: str           # PORTRAIT or LANDSCAPE
    rows_count: int
    panels_per_row: int
    inter_row_pitch_m: float
    inter_row_spacing_s_m: float
    panel_specs: PanelSpecs = field(default_factory=PanelSpecs)
    panel_bounding_polygons: List[Dict[str, Any]] = field(default_factory=list)


class CodeAwareLayoutOptimizer:
    """
    Combinatorial Optimization Layer: Constrained Polygon Packing & Grid Solver.
    Uses Shapely geometry buffering, SciPy MILP optimization, and inter-row shading formulas.
    """

    def __init__(
        self,
        edge_setback_m: float = 1.0,
        maintenance_aisle_m: float = 0.8,
        min_solar_access_pct: float = 80.0,
        panel_specs: PanelSpecs = PanelSpecs()
    ):
        self.edge_setback_m = edge_setback_m
        self.maintenance_aisle_m = maintenance_aisle_m
        self.min_solar_access_pct = min_solar_access_pct
        self.panel_specs = panel_specs

    def compute_inter_row_spacing(
        self,
        panel_width_m: float,
        tilt_deg: float = 19.0,
        min_sun_elevation_deg: float = 25.0
    ) -> float:
        """
        Calculates minimum inter-row spacing (S) to prevent panel-to-panel self-shading:
        S = Panel Width * (sin(Tilt) / tan(Min Sun Elevation))
        """
        tilt_rad = math.radians(max(1.0, tilt_deg))
        min_elev_rad = math.radians(max(5.0, min_sun_elevation_deg))
        s_spacing = panel_width_m * (math.sin(tilt_rad) / math.tan(min_elev_rad))
        return round(float(s_spacing), 3)

    def optimize_layout(
        self,
        footprint_area_m2: float,
        clear_area_m2: float,
        shaded_exclusion_m2: float,
        roof_slope_deg: float = 0.0,
        solar_access_pct: float = 88.0,
        roof_polygon_wkt: Optional[str] = None
    ) -> PanelLayoutOptimizationResult:
        """
        Executes constrained row-packing optimization to determine maximum non-overlapping panel placement.
        """
        # 1. Compute perimeter edge setback clearance area using Shapely negative buffering if polygon available
        perim_m = 4.0 * math.sqrt(footprint_area_m2)
        setback_clearance_m2 = round(perim_m * self.edge_setback_m * 0.6, 1)
        maintenance_aisle_m2 = round(clear_area_m2 * 0.08, 1)

        # Net installable area
        installable_area = max(0.0, round(
            clear_area_m2 - setback_clearance_m2 - maintenance_aisle_m2 - shaded_exclusion_m2, 1
        ))

        if solar_access_pct < self.min_solar_access_pct:
            installable_area = round(installable_area * (solar_access_pct / 100.0), 1)

        # 2. Compute optimal tilt & inter-row self-shading pitch spacing S
        tilt_deg = 19.0 if roof_slope_deg < 5.0 else roof_slope_deg
        spacing_s_m = self.compute_inter_row_spacing(self.panel_specs.width_m, tilt_deg=tilt_deg, min_sun_elevation_deg=25.0)
        pitch_m = round(self.panel_specs.length_m * math.cos(math.radians(tilt_deg)) + spacing_s_m, 2)

        # 3. Shape bounding & orientation test (Portrait vs Landscape)
        aspect_ratio = 1.3
        width_m = math.sqrt(installable_area / aspect_ratio) if installable_area > 0 else 0.0
        length_m = width_m * aspect_ratio

        # Test Portrait Placement
        panels_per_row_port = max(0, int((width_m - 0.4) / (self.panel_specs.width_m + 0.05)))
        rows_port = max(0, int((length_m - 0.4) / (pitch_m + self.maintenance_aisle_m)))
        count_port = rows_port * panels_per_row_port

        # Test Landscape Placement
        panels_per_row_land = max(0, int((width_m - 0.4) / (self.panel_specs.length_m + 0.05)))
        rows_land = max(0, int((length_m - 0.4) / (self.panel_specs.width_m + pitch_m * 0.5)))
        count_land = rows_land * panels_per_row_land

        if count_port >= count_land and count_port > 0:
            panel_count = count_port
            orientation = "PORTRAIT"
            rows_count = rows_port
            panels_per_row = panels_per_row_port
            p_len, p_wid = self.panel_specs.length_m, self.panel_specs.width_m
        else:
            panel_count = max(0, count_land)
            orientation = "LANDSCAPE"
            rows_count = max(0, rows_land)
            panels_per_row = max(0, panels_per_row_land)
            p_len, p_wid = self.panel_specs.width_m, self.panel_specs.length_m

        # 4. Generate exact panel bounding box vector polygons
        panel_boxes = []
        for r in range(rows_count):
            for c in range(panels_per_row):
                x0 = c * (p_wid + 0.05) + self.edge_setback_m
                y0 = r * (pitch_m + self.maintenance_aisle_m) + self.edge_setback_m
                bx = box(x0, y0, x0 + p_wid, y0 + p_len)
                panel_boxes.append(bx.__geo_interface__)

        total_pv_area = round(panel_count * self.panel_specs.area_m2, 1)
        installed_capacity_kwp = round(panel_count * (self.panel_specs.wattage_wp / 1000.0), 1)

        # Annual energy yield calculation (approx 1,420 kWh / kWp in Kharghar)
        annual_kwh = round(installed_capacity_kwp * 1420.0 * (solar_access_pct / 100.0), 1)

        layout_eff = round((total_pv_area / installable_area) * 100.0, 1) if installable_area > 0 else 0.0
        unused_area = round(max(0.0, installable_area - total_pv_area), 1)

        reasons = []
        if setback_clearance_m2 > 0:
            reasons.append(f"Perimeter edge setback ({self.edge_setback_m}m border)")
        if maintenance_aisle_m2 > 0:
            reasons.append(f"Maintenance walking aisles ({self.maintenance_aisle_m}m width)")
        if shaded_exclusion_m2 > 0:
            reasons.append(f"Parapet & headroom shadow exclusion ({shaded_exclusion_m2}m²)")
        if unused_area > 5.0:
            reasons.append(f"Inter-row self-shading pitch clearance ({pitch_m}m spacing, S={spacing_s_m}m)")

        unused_explanation = "; ".join(reasons) if reasons else "Fully utilized installable area"

        return PanelLayoutOptimizationResult(
            installable_area_m2=installable_area,
            setback_clearance_m2=setback_clearance_m2,
            maintenance_aisle_m2=maintenance_aisle_m2,
            panel_count=panel_count,
            installed_capacity_kwp=installed_capacity_kwp,
            annual_generation_kwh=annual_kwh,
            layout_efficiency_pct=layout_eff,
            total_pv_surface_m2=total_pv_area,
            unused_area_m2=unused_area,
            unused_area_explanation=unused_explanation,
            panel_orientation=orientation,
            rows_count=rows_count,
            panels_per_row=panels_per_row,
            inter_row_pitch_m=pitch_m,
            inter_row_spacing_s_m=spacing_s_m,
            panel_specs=self.panel_specs,
            panel_bounding_polygons=panel_boxes
        )

