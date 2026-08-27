"""
run_ai_pipeline_test.py
Testing the AI-Assisted Rooftop Engineering Pipeline on Real Building Datasets in Helios

Runs the 4-stage pipeline:
Stage 1: Roof Obstruction & Element Segmentation
Stage 2: Roof-Plane & Slope Geometry Estimation
Stage 3: 3D Sun Vector Shading Simulation
Stage 4: Code-Aware Constrained Panel Layout Optimization

Benchmarked against:
1. Kharghar Google Open Buildings Dataset (30,587 real footprints)
2. Static 70% fixed area baseline comparison
"""

import sys
import time
import json
import pandas as pd
import numpy as np

from helios.p1_gis import Person1GISEngineer
from helios.p2_spatial import Person2SpatialEngineer
from helios.ai_pipeline.pipeline import AIRooftopEngineeringPipeline

def main():
    sample_size = 500
    if len(sys.argv) > 1:
        try:
            sample_size = int(sys.argv[1])
        except ValueError:
            pass

    print("=" * 70)
    print(f"[START] RUNNING HELIOS AI-ASSISTED ROOFTOP ENGINEERING PIPELINE BENCHMARK")
    print(f"Dataset: Kharghar Google Open Buildings (Targeting {sample_size} Footprints)")
    print("=" * 70)

    t0 = time.time()

    # Load buildings using Person 1 GIS Engineer
    p1 = Person1GISEngineer()
    raw_candidates = p1.load_raw_candidates(limit=sample_size)
    print(f"[OK] Loaded {len(raw_candidates)} real building candidates from repository dataset.")

    # Instantiate Person 2 Spatial Engineer & AI Pipeline
    p2 = Person2SpatialEngineer(resident_reserve_pct=0.15)
    ai_pipeline = AIRooftopEngineeringPipeline(resident_reserve_pct=0.15)

    results = []
    baseline_usable_area_sum = 0.0
    ai_usable_area_sum = 0.0
    total_panels = 0
    total_kwp = 0.0
    total_obstructions_m2 = 0.0

    roof_type_counts = {"FLAT": 0, "GABLE": 0, "HIP": 0, "SINGLE_SLOPE": 0}

    print("\nProcessing buildings through 4-stage AI pipeline...")

    for idx, cand in enumerate(raw_candidates):
        # 1. Static 70% Baseline
        footprint = cand.footprint_area_m2
        baseline_usable = footprint * 0.70
        baseline_usable_area_sum += baseline_usable

        # 2. AI-Assisted Rooftop Pipeline (Stages 1 -> 2 -> 3 -> 4)
        sp = p2.process_candidate(cand)
        ai_res = ai_pipeline.analyze_rooftop(
            candidate_id=cand.candidate_id,
            footprint_area_m2=footprint,
            building_height_m=cand.reported_height_m or 15.0
        )

        ai_usable_area_sum += ai_res.usable_area_m2
        total_panels += ai_res.panel_count
        total_kwp += ai_res.installed_capacity_kwp
        total_obstructions_m2 += ai_res.obstruction_area_m2

        r_type = ai_res.roof_type
        roof_type_counts[r_type] = roof_type_counts.get(r_type, 0) + 1

        results.append({
            "candidate_id": cand.candidate_id,
            "footprint_m2": footprint,
            "baseline_usable_70_m2": round(baseline_usable, 1),
            "ai_clear_area_m2": ai_res.clear_area_m2,
            "ai_installable_area_m2": ai_res.usable_area_m2,
            "obstruction_m2": ai_res.obstruction_area_m2,
            "roof_type": ai_res.roof_type,
            "slope_deg": ai_res.slope_deg,
            "solar_access_pct": ai_res.annual_solar_access_pct,
            "panel_count": ai_res.panel_count,
            "installed_capacity_kwp": ai_res.installed_capacity_kwp,
            "layout_efficiency_pct": ai_res.layout_efficiency_pct,
            "unused_explanation": ai_res.unused_area_explanation
        })

    elapsed = round(time.time() - t0, 2)

    # Summary Analysis
    df = pd.DataFrame(results)
    avg_footprint = round(df["footprint_m2"].mean(), 1)
    avg_baseline_usable = round(df["baseline_usable_70_m2"].mean(), 1)
    avg_ai_usable = round(df["ai_installable_area_m2"].mean(), 1)
    avg_panels = round(df["panel_count"].mean(), 1)
    avg_kwp = round(df["installed_capacity_kwp"].mean(), 1)
    avg_solar_access = round(df["solar_access_pct"].mean(), 1)
    avg_efficiency = round(df["layout_efficiency_pct"].mean(), 1)

    area_diff_pct = round(((ai_usable_area_sum - baseline_usable_area_sum) / baseline_usable_area_sum) * 100.0, 1)

    print("\n" + "=" * 70)
    print("[RESULTS] AI-ASSISTED ROOFTOP ENGINEERING BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total Buildings Tested:          {len(df)} footprints")
    print(f"Execution Time:                  {elapsed} seconds ({round(elapsed/len(df)*1000, 1)} ms/building)")
    print(f"Average Building Footprint:      {avg_footprint} m2")
    print(f"Static 70% Baseline Usable Area: {avg_baseline_usable} m2/building (Total: {round(baseline_usable_area_sum):,} m2)")
    print(f"AI Code-Aware Installable Area:  {avg_ai_usable} m2/building (Total: {round(ai_usable_area_sum):,} m2)")
    print(f"Engineering Accuracy Delta:      {area_diff_pct:+} % correction over static 70% rule")
    print("-" * 70)
    print(f"Average Solar Panels Installed:  {avg_panels} panels/building (540W Mono-PERC)")
    print(f"Average Installed DC Capacity:   {avg_kwp} kWp/building")
    print(f"Total Potential Capacity:        {(total_kwp/1000.0):.2f} MWp across {len(df)} test buildings")
    print(f"Average Annual Solar Access:     {avg_solar_access}% solar exposure")
    print(f"Average Panel Packing Efficiency:{avg_efficiency}%")
    print("-" * 70)
    print("Roof Geometry Plane Types Detected:")
    for rtype, count in roof_type_counts.items():
        print(f"  - {rtype.ljust(15)}: {count} buildings ({round(count/len(df)*100, 1)}%)")
    print("=" * 70)

    # Print Top 3 Sample Detailed Breakdowns
    print("\n[TOP 3] BUILDING DETAILED ENGINEERING BREAKDOWNS:")
    for idx, row in df.head(3).iterrows():
        print(f"\n[Building {row['candidate_id']}]")
        print(f"  Footprint Area:          {row['footprint_m2']} m2")
        print(f"  Obstruction Deductions:  {row['obstruction_m2']} m2 (Water tanks, stairwells, HVAC)")
        print(f"  AI Clear Surface Area:   {row['ai_clear_area_m2']} m2")
        print(f"  Installable Area:        {row['ai_installable_area_m2']} m2 (after 1m edge & maintenance aisles)")
        print(f"  Roof Geometry:           {row['roof_type']} plane ({row['slope_deg']} deg tilt)")
        print(f"  Solar Access Rating:     {row['solar_access_pct']}% sun exposure")
        print(f"  Panel Count & Capacity:  {row['panel_count']} panels -> {row['installed_capacity_kwp']} kWp")
        print(f"  Layout Efficiency:       {row['layout_efficiency_pct']}% packing factor")
        print(f"  Clearance Explanation:   {row['unused_explanation']}")

    # Save summary report artifact
    report_file = "AI_ROOFTOP_BENCHMARK_REPORT.json"
    df.to_json(report_file, orient="records", indent=2)
    print(f"\n[EXPORT] Exported benchmark report to {report_file}")

if __name__ == "__main__":
    main()
