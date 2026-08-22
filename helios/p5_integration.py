"""
helios/p5_integration.py
Person 5: Platform and Integration Engineer

Answers: "How do all these separate calculations become one working application?"
Responsibility:
- Maintain SQLite database schema storing candidates, spatial features, solar estimates, rankings, and human labels.
- Execute full 5-person pipeline: P1 -> P2 -> P3 -> P4 -> P5 DB.
- Provide GeoJSON serializer for mapping UI.
"""

import sqlite3
import json
from dataclasses import asdict
from typing import List, Dict, Any, Optional

from helios.contracts.models import (
    CandidateBuildingP1, SpatialFeaturesP2, SolarEconomicsP3,
    RankingResultP4, IntegratedCandidate
)
from helios.p1_gis import Person1GISEngineer
from helios.p2_spatial import Person2SpatialEngineer
from helios.p3_solar_economics import Person3SolarEconomicEngineer
from helios.p4_ranking import Person4RankingEngineer

DB_PATH = "helios_database.sqlite"

class Person5PlatformEngineer:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                geometry_wkt TEXT,
                p1_data TEXT,
                p2_data TEXT,
                p3_data TEXT,
                p4_data TEXT,
                human_review_label TEXT DEFAULT 'unreviewed',
                human_notes TEXT DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()

    def run_pipeline(
        self,
        limit: int = 100,
        scenario: str = "balanced"
    ) -> List[IntegratedCandidate]:
        
        # 1. Person 1: Ingest GIS & raw candidates
        p1_engine = Person1GISEngineer()
        p1_candidates = p1_engine.load_raw_candidates(limit=limit)

        # 2. Person 2: Extract spatial roof features
        p2_engine = Person2SpatialEngineer()
        p2_features = p2_engine.process_batch(p1_candidates)

        # 3. Person 3: Estimate solar capacity & economics
        p3_engine = Person3SolarEconomicEngineer()
        p3_estimates = p3_engine.process_batch(p2_features)

        # 4. Person 4: Score, filter & rank candidates
        p4_engine = Person4RankingEngineer(scenario=scenario)
        p4_rankings = p4_engine.process_candidates(p2_features, p3_estimates, scenario=scenario)

        # Map lookup by candidate_id
        p1_map = {c.candidate_id: c for c in p1_candidates}
        p2_map = {f.candidate_id: f for f in p2_features}
        p3_map = {s.candidate_id: s for s in p3_estimates}
        p4_map = {r.candidate_id: r for r in p4_rankings}

        integrated_list: List[IntegratedCandidate] = []
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for c1 in p1_candidates:
            cid = c1.candidate_id
            c2 = p2_map.get(cid)
            c3 = p3_map.get(cid)
            c4 = p4_map.get(cid)

            if not (c2 and c3 and c4):
                continue

            integ = IntegratedCandidate(
                candidate_id=cid,
                latitude=c1.latitude,
                longitude=c1.longitude,
                geometry_wkt=c1.geometry_wkt,
                p1=asdict(c1),
                p2=asdict(c2),
                p3=asdict(c3),
                p4=asdict(c4),
                human_review_label="unreviewed",
                human_notes=""
            )
            integrated_list.append(integ)

            # Store into database
            cur.execute("""
                INSERT OR REPLACE INTO candidates
                (candidate_id, latitude, longitude, geometry_wkt, p1_data, p2_data, p3_data, p4_data, human_review_label, human_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid, c1.latitude, c1.longitude, c1.geometry_wkt,
                json.dumps(asdict(c1)), json.dumps(asdict(c2)),
                json.dumps(asdict(c3)), json.dumps(asdict(c4)),
                "unreviewed", ""
            ))

        conn.commit()
        conn.close()
        return integrated_list

    def get_geojson(self, scenario: str = "balanced") -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT candidate_id, latitude, longitude, p1_data, p2_data, p3_data, p4_data, human_review_label FROM candidates")
        rows = cur.fetchall()
        conn.close()

        features = []
        for r in rows:
            cid, lat, lon, p1_str, p2_str, p3_str, p4_str, label = r
            p1 = json.loads(p1_str) if p1_str else {}
            p2 = json.loads(p2_str) if p2_str else {}
            p3 = json.loads(p3_str) if p3_str else {}
            p4 = json.loads(p4_str) if p4_str else {}

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "candidate_id": cid,
                    "usable_area_m2": p2.get("usable_area_m2", 0),
                    "capacity_kwp": p3.get("estimated_capacity_kwp", 0),
                    "annual_yield_kwh": p3.get("annual_yield_kwh", 0),
                    "payback_years": p3.get("indicative_payback_years", 0),
                    "rank": p4.get("rank", 999),
                    "total_score": p4.get("total_score", 0),
                    "eligible": p4.get("eligible", False),
                    "positive_reasons": p4.get("positive_reasons", []),
                    "cautions": p4.get("cautions", []),
                    "human_review_label": label
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def update_human_label(self, candidate_id: str, label: str, notes: str = ""):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE candidates SET human_review_label = ?, human_notes = ? WHERE candidate_id = ?", (label, notes, candidate_id))
        conn.commit()
        conn.close()
