"""
run_pipeline.py
Master End-to-End Pipeline Orchestrator for Helios

Executes:
Person 1 (GIS Ingestion) -> Person 2 (Spatial Features) -> Person 3 (Solar & Economics) -> Person 4 (Ranking & ML) -> Person 5 (Database & Integration) -> Person 6 (Validation Benchmark)
"""

import sys
import json
from dataclasses import asdict

from helios.p5_integration import Person5PlatformEngineer
from helios.p6_validation import Person6ValidationOwner

def main():
    limit = 1000
    scenario = "balanced"
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
            
    if len(sys.argv) > 2:
        scenario = sys.argv[2]

    print("==================================================================")
    print(f"[START] Starting Helios End-to-End Pipeline [Limit: {limit}, Scenario: {scenario}]")
    print("==================================================================")

    # 1-5. Run Integrated Pipeline
    p5 = Person5PlatformEngineer()
    candidates = p5.run_pipeline(limit=limit, scenario=scenario)

    print(f"\n[OK] Pipeline complete. Processed {len(candidates)} candidates.")
    
    # Print sample top building (P2, P3, P4 outputs)
    top_candidates = [c for c in candidates if c.p4.get("eligible", False)]
    top_candidates.sort(key=lambda x: x.p4.get("rank", 99999))
    
    if top_candidates:
        top1 = top_candidates[0]
        print("\n--- [TOP] Top Ranked Candidate ---")
        print(f"Candidate ID:           {top1.candidate_id}")
        print(f"Rank:                   #{top1.p4.get('rank')}")
        print(f"Total Score:            {top1.p4.get('total_score')}")
        print(f"Footprint Area:         {top1.p2.get('footprint_area_m2')} m2")
        print(f"Usable Roof Area:       {top1.p2.get('usable_area_m2')} m2")
        print(f"Estimated Capacity:     {top1.p3.get('estimated_capacity_kwp')} kWp")
        print(f"Annual Energy Yield:    {top1.p3.get('annual_yield_kwh'):,} kWh/yr")
        print(f"Estimated CapEx:        INR {top1.p3.get('estimated_capex_inr'):,}")
        print(f"Payback Period:         {top1.p3.get('indicative_payback_years')} years")
        print(f"Positive Reasons:       {', '.join(top1.p4.get('positive_reasons', []))}")
        print(f"Cautions:               {', '.join(top1.p4.get('cautions', []))}")
        
    # Export spatial features JSON & Parquet contract artifacts for Person 2 downstream compatibility
    spatial_export = [c.p2 for c in candidates]
    with open("spatial_features.json", "w") as f:
        json.dump(spatial_export, f, indent=2)
    
    try:
        df_p2 = pd.DataFrame(spatial_export)
        df_p2.to_parquet("spatial_features.parquet", index=False)
        print("\n[EXPORT] Exported spatial_features.json & spatial_features.parquet (Person 2 contract artifacts)")
    except Exception:
        print("\n[EXPORT] Exported spatial_features.json (Person 2 contract artifact)")

    # 6. Person 6 Validation Benchmark
    p6 = Person6ValidationOwner()
    summary = p6.run_benchmark(candidates)
    p6.generate_report(summary)

    print("\n==================================================================")
    print("Person 6 Validation Benchmark Result:")
    print(f'"{summary["claim_statement"]}"')
    print("==================================================================")

if __name__ == "__main__":
    main()
