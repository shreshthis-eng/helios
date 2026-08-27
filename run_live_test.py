"""
run_live_test.py
Live Interactive Testing Engine for Helios Solar Rooftop Dataset

Processes real building footprints from kharghar_raw_buildings.csv (Google Open Buildings in Helios Repository)
through the full 6-role architecture & AI-Assisted Rooftop Engineering Pipeline.
Updates helios_database.sqlite in real-time for live viewing on http://localhost:8000.
"""

import sys
import time
import json
import sqlite3
import pandas as pd

from helios.p1_gis import Person1GISEngineer
from helios.p2_spatial import Person2SpatialEngineer
from helios.p3_solar_economics import Person3SolarEconomicEngineer
from helios.p4_ranking import Person4RankingEngineer
from helios.p5_integration import Person5PlatformEngineer
from helios.p6_validation import Person6ValidationOwner

def run_live_test(limit: int = 1000, scenario: str = "balanced"):
    print("=" * 75)
    print(f"[LIVE TEST] STARTING HELIOS REPOSITORY DATASET EVALUATION")
    print(f"Dataset: kharghar_raw_buildings.csv (Google Open Buildings India)")
    print(f"Target Footprints: {limit} buildings | Scenario: {scenario.upper()}")
    print("=" * 75)

    t_start = time.time()

    # Step 1: Initialize Platform & Pipeline
    p1 = Person1GISEngineer()
    p2 = Person2SpatialEngineer(resident_reserve_pct=0.15)
    p3 = Person3SolarEconomicEngineer()
    p4 = Person4RankingEngineer(scenario=scenario)
    p5 = Person5PlatformEngineer(db_path="helios_database.sqlite")
    p6 = Person6ValidationOwner()

    print("[STAGE 1/6] Ingesting Kharghar GIS Building Footprints from Repository...")
    candidates = p1.load_raw_candidates(limit=limit)
    print(f"  -> Successfully loaded {len(candidates)} real building candidates from repository dataset.")

    # Live streaming batch processing
    batch_size = 250
    total_candidates = len(candidates)
    processed_count = 0
    
    spatial_features_all = []
    solar_economics_all = []

    print("\n[STAGE 2/6] Streaming AI-Assisted Rooftop Engineering Pipeline...")
    print("  (Segmenting obstructions, plane geometry, 3D sun vectors, and layout optimization)")
    print("-" * 75)

    for i in range(0, total_candidates, batch_size):
        batch = candidates[i : i + batch_size]
        t_batch_start = time.time()

        # Run Person 2 AI Spatial Pipeline
        sp_batch = p2.process_batch(batch)
        spatial_features_all.extend(sp_batch)

        # Run Person 3 Solar Economics Pipeline
        sol_batch = p3.process_batch(sp_batch)
        solar_economics_all.extend(sol_batch)

        processed_count += len(batch)
        batch_elapsed = round(time.time() - t_batch_start, 2)
        
        # Batch metrics calculation
        batch_installable_m2 = sum(sp.usable_area_m2 for sp in sp_batch)
        batch_capacity_kwp = sum(sol.estimated_capacity_kwp for sol in sol_batch)
        batch_panels = sum(sp.panel_count for sp in sp_batch)

        pct = round((processed_count / total_candidates) * 100, 1)
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))

        print(f"  [{bar}] {processed_count}/{total_candidates} ({pct}%) | "
              f"Batch Time: {batch_elapsed}s | "
              f"Panels: {batch_panels} | Capacity: {round(batch_capacity_kwp, 1)} kWp")

    print("-" * 75)
    print(f"[OK] Completed AI Rooftop Engineering for {total_candidates} buildings.")

    # Step 3: Multi-Criteria Ranking & ML Engine
    print("\n[STAGE 3/6] Running Multi-Criteria Decision Ranking (MCDM)...")
    ranking_results = p4.process_candidates(spatial_features_all, solar_economics_all, scenario=scenario)

    # Step 4: Storage & SQLite Persistence via Person 5 Platform Engineer
    print("\n[STAGE 4/6] Persisting Results to SQLite Database (helios_database.sqlite)...")
    integrated_list = p5.run_pipeline(limit=limit, scenario=scenario)
    print(f"  -> Saved {len(integrated_list)} records to SQLite database with full contract validation.")

    # Step 5: Person 6 Human Review & Accuracy Benchmarking
    print("\n[STAGE 5/6] Generating Validation Benchmark Report...")
    benchmark_report = p6.run_benchmark(integrated_list)
    print(f"  -> {benchmark_report['claim_statement']}")

    # Step 6: Summary Performance & Key Findings
    t_total = round(time.time() - t_start, 2)
    
    total_footprint = sum(c.footprint_area_m2 for c in candidates)
    total_installable = sum(sp.usable_area_m2 for sp in spatial_features_all)
    total_panels = sum(sp.panel_count for sp in spatial_features_all)
    total_mwp = sum(sol.estimated_capacity_kwp for sol in solar_economics_all) / 1000.0
    total_gwh = sum(sol.annual_yield_kwh for sol in solar_economics_all) / 1e6
    eligible_count = sum(1 for r in ranking_results if r.eligible)

    eligible_rankings = [r for r in ranking_results if r.eligible]
    if eligible_rankings:
        top_cand = sorted(eligible_rankings, key=lambda x: x.rank)[0]
    else:
        top_cand = ranking_results[0]

    top_cand_id = top_cand.candidate_id
    top_sp = next(sp for sp in spatial_features_all if sp.candidate_id == top_cand_id)
    top_sol = next(sol for sol in solar_economics_all if sol.candidate_id == top_cand_id)

    print("\n" + "=" * 75)
    print("[LIVE TEST RESULTS SUMMARY - HELIOS REPOSITORY DATASET]")
    print("=" * 75)
    print(f"Dataset File:               kharghar_raw_buildings.csv")
    print(f"Buildings Processed:        {total_candidates} footprints")
    print(f"Eligible Prospect Roofs:    {eligible_count} buildings ({round(eligible_count/total_candidates*100, 1)}%)")
    print(f"Total Pipeline Runtime:     {t_total} seconds ({round(t_total/total_candidates*1000, 1)} ms/building)")
    print("-" * 75)
    print(f"Total Roof Footprint:       {round(total_footprint):,} m2")
    print(f"AI Installable Area:        {round(total_installable):,} m2 (after 4-stage AI deductions)")
    print(f"Installed Solar Panels:     {total_panels:,} modules (540W Mono-PERC)")
    print(f"Total Clean Energy Capacity:{total_mwp:.2f} MWp")
    print(f"Annual Energy Generation:   {total_gwh:.3f} GWh / year")
    print("-" * 75)
    print(f"TOP RANKED ROOFTOP: {top_cand_id}")
    print(f"   - Score:                  {top_cand.total_score:.3f} (Rank #{top_cand.rank})")
    print(f"   - Footprint / Clear Area: {top_sp.footprint_area_m2} m2 / {top_sp.clear_area_m2} m2")
    print(f"   - Roof Geometry Plane:    {top_sp.roof_type} ({top_sp.slope_deg} deg tilt)")
    print(f"   - Solar Access Rating:    {top_sp.annual_solar_access_pct}% sun exposure")
    print(f"   - Installed Capacity:     {top_sol.estimated_capacity_kwp} kWp ({top_sp.panel_count} modules)")
    print(f"   - Est. Annual Generation: {top_sol.annual_yield_kwh:,.0f} kWh/yr")
    print(f"   - Project CapEx & Payback:INR {top_sol.estimated_capex_inr:,.0f} | {top_sol.indicative_payback_years} years")
    print(f"   - Positive Attributes:   {', '.join(top_cand.positive_reasons)}")
    print("=" * 75)
    print(f"\n[LIVE SERVER READY] View updated dashboard live at: http://localhost:8000\n")

if __name__ == "__main__":
    limit_arg = 1000
    scenario_arg = "balanced"
    if len(sys.argv) > 1:
        try: limit_arg = int(sys.argv[1])
        except ValueError: pass
    if len(sys.argv) > 2:
        scenario_arg = sys.argv[2]
        
    run_live_test(limit=limit_arg, scenario=scenario_arg)
