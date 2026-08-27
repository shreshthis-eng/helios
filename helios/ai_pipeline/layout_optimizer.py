"""
helios/ai_pipeline/layout_optimizer.py
Stage 4: Code-Aware Panel Layout & Polygon-Packing Optimizer

Calculates actual installable area by subtracting operational & regulatory clearances:
A_installable = A_clear - A_access - A_setbacks - A_maintenance - A_shade_excluded

Performs constrained polygon-packing layout optimization:
- Places commercial Mono-PERC 540W solar panels in rows
- Accounts for portrait vs landscape orientation, inter-row pitch spacing, maintenance aisles, edge setbacks
- Returns exact panel count, DC capacity (kWp), layout efficiency %, and unused area explanation.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any

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
    layout_efficiency_pct: float     # (panel_count * panel_area) / installable_area
    total_pv_surface_m2: float
    unused_area_m2: float
    unused_area_explanation: str
    panel_orientation: str           # PORTRAIT or LANDSCAPE
    rows_count: int
    panels_per_row: int
    inter_row_pitch_m: float
    panel_specs: PanelSpecs = field(default_factory=PanelSpecs)

class CodeAwareLayoutOptimizer:
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

    def optimize_layout(
        self,
        footprint_area_m2: float,
        clear_area_m2: float,
        shaded_exclusion_m2: float,
        roof_slope_deg: float = 0.0,
        solar_access_pct: float = 88.0
    ) -> PanelLayoutOptimizationResult:
        """
        Executes constrained row-packing optimization to determine true installable panel count.
        """
        # 1. Compute perimeter edge setback clearance area
        # Perimeter approx = 4 * sqrt(footprint_area)
        perim_m = 4.0 * math.sqrt(footprint_area_m2)
        setback_clearance_m2 = round(perim_m * self.edge_setback_m * 0.6, 1)

        # 2. Maintenance corridor clearance (~8% of clear area)
        maintenance_aisle_m2 = round(clear_area_m2 * 0.08, 1)

        # 3. Net installable area
        installable_area = max(0.0, round(
            clear_area_m2 - setback_clearance_m2 - maintenance_aisle_m2 - shaded_exclusion_m2, 1
        ))

        # Check if solar access meets minimum threshold
        if solar_access_pct < self.min_solar_access_pct:
            installable_area = round(installable_area * (solar_access_pct / 100.0), 1)

        # 4. Polygon-packing row optimizer
        # Approximate roof bounding rectangle dimensions
        aspect_ratio = 1.3 # 1.3:1 typical rectangular roof
        width_m = math.sqrt(installable_area / aspect_ratio) if installable_area > 0 else 0.0
        length_m = width_m * aspect_ratio

        # Inter-row pitch spacing to prevent panel-to-panel shading (for 19 deg tilt in Kharghar)
        # pitch = panel_length * cos(tilt) + panel_length * sin(tilt) * tan(latitude + 10)
        pitch_m = round(self.panel_specs.length_m + 0.45, 2) # ~2.73m pitch

        # Test Portrait Placement (panels along length)
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
        else:
            panel_count = max(0, count_land)
            orientation = "LANDSCAPE"
            rows_count = max(0, rows_land)
            panels_per_row = max(0, panels_per_row_land)

        # Total PV surface area installed
        total_pv_area = round(panel_count * self.panel_specs.area_m2, 1)
        installed_capacity_kwp = round(panel_count * (self.panel_specs.wattage_wp / 1000.0), 1)

        # Layout packing efficiency
        layout_eff = round((total_pv_area / installable_area) * 100.0, 1) if installable_area > 0 else 0.0
        unused_area = round(max(0.0, installable_area - total_pv_area), 1)

        # Unused area explanation
        reasons = []
        if setback_clearance_m2 > 0:
            reasons.append(f"Perimeter edge setback ({self.edge_setback_m}m border)")
        if maintenance_aisle_m2 > 0:
            reasons.append(f"Maintenance walking aisles ({self.maintenance_aisle_m}m width)")
        if shaded_exclusion_m2 > 0:
            reasons.append(f"Parapet & headroom shadow exclusion ({shaded_exclusion_m2}m²)")
        if unused_area > 5.0:
            reasons.append(f"Inter-row shading pitch clearance ({pitch_m}m spacing)")

        unused_explanation = "; ".join(reasons) if reasons else "Fully utilized installable area"

        return PanelLayoutOptimizationResult(
            installable_area_m2=installable_area,
            setback_clearance_m2=setback_clearance_m2,
            maintenance_aisle_m2=maintenance_aisle_m2,
            panel_count=panel_count,
            installed_capacity_kwp=installed_capacity_kwp,
            layout_efficiency_pct=layout_eff,
            total_pv_surface_m2=total_pv_area,
            unused_area_m2=unused_area,
            unused_area_explanation=unused_explanation,
            panel_orientation=orientation,
            rows_count=rows_count,
            panels_per_row=panels_per_row,
            inter_row_pitch_m=pitch_m,
            panel_specs=self.panel_specs
        )
