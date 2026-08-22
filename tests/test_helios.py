"""
tests/test_helios.py
Comprehensive Unit and Integration Test Suite for Helios
"""

import unittest
import os
import json
from helios.contracts.models import CandidateBuildingP1, SpatialFeaturesP2, SolarEconomicsP3, RankingResultP4
from helios.p1_gis import Person1GISEngineer
from helios.p2_spatial import Person2SpatialEngineer
from helios.p3_solar_economics import Person3SolarEconomicEngineer
from helios.p4_ranking import Person4RankingEngineer
from helios.p5_integration import Person5PlatformEngineer
from helios.p6_validation import Person6ValidationOwner

class TestHeliosPipeline(unittest.TestCase):

    def test_person1_gis_ingestion(self):
        p1 = Person1GISEngineer()
        candidates = p1.load_raw_candidates(limit=5)
        self.assertGreaterEqual(len(candidates), 1)
        c = candidates[0]
        self.assertTrue(c.candidate_id.startswith("KHAR_"))
        self.assertGreater(c.footprint_area_m2, 0)
        self.assertGreater(c.latitude, 0)

    def test_person2_spatial_features(self):
        c1 = CandidateBuildingP1(
            candidate_id="KHAR_TEST01",
            latitude=19.03,
            longitude=73.06,
            footprint_area_m2=500.0,
            reported_height_m=20.0,
            height_confidence=0.8,
            dem_elevation_m=15.0,
            geometry_wkt="POLYGON ((73.06 19.03, 73.061 19.03, 73.061 19.031, 73.06 19.031, 73.06 19.03))"
        )
        p2 = Person2SpatialEngineer()
        sp = p2.process_candidate(c1)
        self.assertEqual(sp.candidate_id, "KHAR_TEST01")
        self.assertGreater(sp.footprint_area_m2, 0)
        self.assertAlmostEqual(sp.usable_area_m2, sp.footprint_area_m2 * 0.70, places=1)

    def test_person3_solar_economics(self):
        sp = SpatialFeaturesP2(
            candidate_id="KHAR_TEST01",
            footprint_area_m2=600.0,
            usable_area_m2=420.0,
            building_height_m=20.0,
            terrain_elevation_m=15.0,
            road_distance_m=10.0,
            grid_distance_m=100.0,
            shading_factor=0.85,
            spatial_confidence=0.8
        )
        p3 = Person3SolarEconomicEngineer()
        sol = p3.process_candidate(sp)
        self.assertEqual(sol.candidate_id, "KHAR_TEST01")
        self.assertAlmostEqual(sol.estimated_capacity_kwp, 70.0, places=1)
        self.assertGreater(sol.annual_yield_kwh, 0)
        self.assertGreater(sol.estimated_capex_inr, 0)

    def test_person4_ranking(self):
        sp = SpatialFeaturesP2(
            candidate_id="KHAR_TEST01",
            footprint_area_m2=600.0, usable_area_m2=420.0,
            building_height_m=20.0, terrain_elevation_m=15.0,
            road_distance_m=10.0, grid_distance_m=100.0,
            shading_factor=0.85, spatial_confidence=0.8
        )
        sol = SolarEconomicsP3(
            candidate_id="KHAR_TEST01",
            estimated_capacity_kwp=70.0, annual_yield_kwh=75000,
            estimated_capex_inr=3360000, estimated_rent_inr_month=12600,
            indicative_payback_years=6.5, solar_confidence=0.8, economics_confidence=0.8
        )
        p4 = Person4RankingEngineer(scenario="balanced")
        results = p4.process_candidates([sp], [sol])
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertTrue(res.eligible)
        self.assertEqual(res.rank, 1)

    def test_person5_and_6_integration(self):
        p5 = Person5PlatformEngineer(db_path="test_helios.sqlite")
        integrated = p5.run_pipeline(limit=10, scenario="balanced")
        self.assertEqual(len(integrated), 10)
        
        geojson = p5.get_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 10)

        p6 = Person6ValidationOwner()
        summary = p6.run_benchmark(integrated)
        self.assertIn("Helios found", summary["claim_statement"])

        if os.path.exists("test_helios.sqlite"):
            os.remove("test_helios.sqlite")

if __name__ == "__main__":
    unittest.main()
