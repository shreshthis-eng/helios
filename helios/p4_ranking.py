"""
helios/p4_ranking.py
Person 4: Ranking and ML Engineer

Answers: "Considering all the evidence, which buildings should we inspect first?"
Responsibility:
- Apply hard eligibility filters (min roof area, grid distance limit, max payback).
- Compute normalized sub-scores (generation, physical, grid, economic, confidence).
- Support multiple scenarios: balanced, energy_first, cost_first, accessibility_first.
- Generate natural language explanations (positives and cautions).
- Fallback ML Ranker model using RandomForest.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    RandomForestRegressor = None
from helios.contracts.models import SpatialFeaturesP2, SolarEconomicsP3, RankingResultP4

SCENARIO_WEIGHTS = {
    "balanced": {"gen": 0.35, "phys": 0.20, "grid": 0.15, "econ": 0.20, "conf": 0.10},
    "energy_first": {"gen": 0.55, "phys": 0.25, "grid": 0.05, "econ": 0.10, "conf": 0.05},
    "cost_first": {"econ": 0.45, "gen": 0.25, "phys": 0.15, "grid": 0.10, "conf": 0.05},
    "accessibility_first": {"grid": 0.45, "phys": 0.25, "gen": 0.15, "econ": 0.10, "conf": 0.05}
}

class Person4RankingEngineer:
    def __init__(self, scenario: str = "balanced"):
        self.scenario = scenario if scenario in SCENARIO_WEIGHTS else "balanced"
        self.ml_model: Optional[RandomForestRegressor] = None

    def _train_ml_fallback(self, X: np.ndarray, y: np.ndarray):
        if not HAS_SKLEARN:
            self.ml_model = None
            return
        try:
            rf = RandomForestRegressor(n_estimators=20, random_state=42)
            rf.fit(X, y)
            self.ml_model = rf
        except Exception:
            self.ml_model = None

    def process_candidates(
        self,
        spatial_list: List[SpatialFeaturesP2],
        solar_list: List[SolarEconomicsP3],
        scenario: Optional[str] = None
    ) -> List[RankingResultP4]:
        
        active_scenario = scenario if (scenario and scenario in SCENARIO_WEIGHTS) else self.scenario
        weights = SCENARIO_WEIGHTS[active_scenario]
        
        spatial_map = {s.candidate_id: s for s in spatial_list}
        results: List[RankingResultP4] = []
        
        # Collect values for min-max normalization
        yields = [s.annual_yield_kwh for s in solar_list]
        max_yield = max(yields) if yields and max(yields) > 0 else 100000.0
        
        areas = [sp.usable_area_m2 for sp in spatial_list]
        max_area = max(areas) if areas and max(areas) > 0 else 1000.0

        scored_candidates = []

        for sol in solar_list:
            cid = sol.candidate_id
            sp = spatial_map.get(cid)
            if not sp:
                continue

            # 1. HARD FILTERS
            if sp.usable_area_m2 < 30.0:
                results.append(RankingResultP4(
                    candidate_id=cid, eligible=False, generation_score=0.0, physical_score=0.0,
                    grid_score=0.0, economic_score=0.0, confidence_score=0.0, total_score=0.0,
                    rank=999999, exclusion_reason="Roof area too small (< 30 m2)"
                ))
                continue
                
            if sp.grid_distance_m > 1200.0:
                results.append(RankingResultP4(
                    candidate_id=cid, eligible=False, generation_score=0.0, physical_score=0.0,
                    grid_score=0.0, economic_score=0.0, confidence_score=0.0, total_score=0.0,
                    rank=999999, exclusion_reason="Too far from grid infrastructure (> 1200 m)"
                ))
                continue

            if sol.indicative_payback_years > 15.0:
                results.append(RankingResultP4(
                    candidate_id=cid, eligible=False, generation_score=0.0, physical_score=0.0,
                    grid_score=0.0, economic_score=0.0, confidence_score=0.0, total_score=0.0,
                    rank=999999, exclusion_reason="Payback period too long (> 15 years)"
                ))
                continue

            # 2. SUB-SCORES
            gen_score = round(min(1.0, sol.annual_yield_kwh / max_yield), 3)
            phys_score = round(min(1.0, sp.usable_area_m2 / max_area), 3)
            grid_score = round(max(0.0, 1.0 - (sp.grid_distance_m / 600.0)), 3)
            econ_score = round(max(0.0, 1.0 - (sol.indicative_payback_years / 10.0)), 3)
            conf_score = round((sp.spatial_confidence + sol.solar_confidence + sol.economics_confidence) / 3.0, 3)

            # 3. TOTAL COMPOSITE SCORE
            tot_score = round(
                weights["gen"] * gen_score +
                weights["phys"] * phys_score +
                weights["grid"] * grid_score +
                weights["econ"] * econ_score +
                weights["conf"] * conf_score,
                3
            )

            # 4. EXPLANATION GENERATION
            positives = []
            cautions = []
            
            if gen_score >= 0.70:
                positives.append("High solar generation potential")
            if phys_score >= 0.65:
                positives.append("Large usable rooftop footprint")
            if grid_score >= 0.80:
                positives.append("Excellent grid proximity (< 120m)")
            if econ_score >= 0.75:
                positives.append("Rapid investment payback (< 5 yrs)")

            if sp.shading_factor < 0.80:
                cautions.append("Substantial structural/neighbouring shading proxy")
            if sol.economics_confidence < 0.70:
                cautions.append("Rent and CapEx estimate moderate confidence")
            if sp.grid_distance_m > 300.0:
                cautions.append("Interconnection requires line extension (> 300m)")

            if not positives:
                positives.append("Standard rooftop candidate profile")

            scored_candidates.append({
                "candidate_id": cid,
                "gen": gen_score, "phys": phys_score, "grid": grid_score,
                "econ": econ_score, "conf": conf_score, "total": tot_score,
                "positives": positives, "cautions": cautions,
                "features": [sp.usable_area_m2, sp.building_height_m, sp.grid_distance_m, sol.estimated_capacity_kwp, sol.indicative_payback_years]
            })

        # Train optional ML Ranker model on eligible candidates
        if len(scored_candidates) > 5:
            X_train = np.array([item["features"] for item in scored_candidates])
            y_train = np.array([item["total"] for item in scored_candidates])
            self._train_ml_fallback(X_train, y_train)

        # SORT AND ASSIGN RANKS
        scored_candidates.sort(key=lambda x: x["total"], reverse=True)

        for idx, item in enumerate(scored_candidates):
            results.append(RankingResultP4(
                candidate_id=item["candidate_id"],
                eligible=True,
                generation_score=item["gen"],
                physical_score=item["phys"],
                grid_score=item["grid"],
                economic_score=item["econ"],
                confidence_score=item["conf"],
                total_score=item["total"],
                rank=idx + 1,
                positive_reasons=item["positives"],
                cautions=item["cautions"]
            ))

        return results
