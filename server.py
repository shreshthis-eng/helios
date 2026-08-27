"""
server.py
REST API and Web Server for Helios Solar Rooftop Prospecting
"""

import os
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from helios.p5_integration import Person5PlatformEngineer

PORT = 8050
DB_PATH = "helios_database.sqlite"


class HeliosRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            print(f"[SERVER DEBUG] Request path: '{path}'", flush=True)

            if path == "/api/candidates":

                self._send_json(self._get_candidates_geojson())
                return
            elif path.startswith("/api/analysis/"):
                cand_id = path.replace("/api/analysis/", "")
                self._send_json(self._get_engine_analysis_json(cand_id))
                return
            elif path.startswith("/api/candidates/"):
                cand_id = path.replace("/api/candidates/", "")
                self._send_json(self._get_candidate_detail(cand_id))
                return
            elif path == "/api/summary":
                self._send_json(self._get_summary())
                return
            elif path.startswith("/api/shade_simulation"):
                params = parse_qs(parsed.query)
                lat = float(params.get("lat", [19.0307])[0])
                lon = float(params.get("lon", [73.0652])[0])
                width = float(params.get("width", [20.0])[0])
                length = float(params.get("length", [20.0])[0])
                height = float(params.get("height", [15.0])[0])
                self._send_json(self._run_shade_simulation(lat, lon, width, length, height))
                return
            elif path == "/" or path == "/index.html":
                self._serve_static("public/index.html", "text/html")
                return
            else:
                static_file = os.path.join("public", path.lstrip("/"))
                if os.path.exists(static_file) and not os.path.isdir(static_file):
                    ext = os.path.splitext(static_file)[1]
                    content_type = "text/html"
                    if ext == ".css": content_type = "text/css"
                    elif ext == ".js": content_type = "application/javascript"
                    elif ext == ".json": content_type = "application/json"
                    self._serve_static(static_file, content_type)
                else:
                    self.send_error(404, f"File Not Found: {path}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({"error": str(e)}, status=500)



    def _get_engine_analysis_json(self, cand_id: str) -> Dict[str, Any]:
        """Generates exact structured Helios System Engine JSON payload for a target rooftop."""
        from helios.ai_pipeline.pipeline import AIRooftopEngineeringPipeline
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT candidate_id, latitude, longitude, p1_data, p2_data FROM candidates WHERE candidate_id = ?", (cand_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            # Fallback evaluation for candidate_id
            footprint_area = 450.0
            height = 15.0
        else:
            cid, lat, lon, p1_str, p2_str = row
            p1 = json.loads(p1_str) if p1_str else {}
            p2 = json.loads(p2_str) if p2_str else {}
            footprint_area = float(p1.get("footprint_area_m2") or 450.0)
            height = float(p1.get("reported_height_m") or 15.0)


        pipeline = AIRooftopEngineeringPipeline(resident_reserve_pct=0.15)
        res = pipeline.analyze_rooftop(cand_id, footprint_area, height)

        baseline_70_m2 = footprint_area * 0.70
        delta_pct = round(((res.usable_area_m2 - baseline_70_m2) / baseline_70_m2) * 100.0, 1)

        return {
            "building_id": res.candidate_id,
            "roof_metrics": {
                "gross_area_sqm": res.footprint_area_m2,
                "clear_usable_area_sqm": res.clear_area_m2,
                "clear_area_percentage": round((res.clear_area_m2 / res.footprint_area_m2) * 100.0, 1) if res.footprint_area_m2 > 0 else 0.0,
                "baseline_70_percent_error_margin": f"{delta_pct:+}%"
            },
            "geometry": {
                "roof_type": f"{res.roof_type} Plane",
                "primary_slope_deg": res.slope_deg,
                "azimuth_facing": f"{int(res.stage2_geometry.get('aspect_azimuth_deg', 0))}_deg_South"
            },
            "solar_potential": {
                "annual_solar_access_avg": res.annual_solar_access_pct,
                "unshaded_usable_area_sqm": res.usable_area_m2
            },
            "engineered_layout": {
                "selected_panel": "Mono-PERC 540W (2.28m x 1.13m)",
                "total_panels_placed": res.panel_count,
                "system_dc_capacity_kwp": res.installed_capacity_kwp,
                "est_annual_generation_kwh": round(res.installed_capacity_kwp * 1420.0 * (res.annual_solar_access_pct / 100.0), 1),
                "setback_rules_applied": {
                    "parapet_clearance_m": 1.0,
                    "maintenance_walkway_m": 0.8,
                    "resident_access_reserved_pct": 15.0
                }
            },
            "flags_for_verification": [
                "VERIFY_WATER_TANK_HEIGHT",
                "CHECK_PARAPET_STRUCTURAL_MARGIN"
            ]
        }


    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/rerank":
            scenario = data.get("scenario", "balanced")
            p5 = Person5PlatformEngineer()
            p5.run_pipeline(limit=500, scenario=scenario)
            self._send_json({"status": "success", "scenario": scenario})
        elif path == "/api/review":
            cand_id = data.get("candidate_id")
            label = data.get("label", "unreviewed")
            notes = data.get("notes", "")
            if cand_id:
                p5 = Person5PlatformEngineer()
                p5.update_human_label(cand_id, label, notes)
                self._send_json({"status": "updated", "candidate_id": cand_id, "label": label})
            else:
                self._send_json({"error": "missing candidate_id"}, status=400)
        else:
            self.send_error(404, "Endpoint Not Found")

    def _serve_static(self, filepath: str, content_type: str):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_candidates_geojson(self):
        p5 = Person5PlatformEngineer()
        return p5.get_geojson()

    def _get_candidate_detail(self, cand_id: str):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT candidate_id, latitude, longitude, p1_data, p2_data, p3_data, p4_data, human_review_label, human_notes FROM candidates WHERE candidate_id = ?", (cand_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"error": "candidate not found"}
        
        cid, lat, lon, p1, p2, p3, p4, label, notes = row
        return {
            "candidate_id": cid,
            "latitude": lat,
            "longitude": lon,
            "p1": json.loads(p1) if p1 else {},
            "p2": json.loads(p2) if p2 else {},
            "p3": json.loads(p3) if p3 else {},
            "p4": json.loads(p4) if p4 else {},
            "human_review_label": label,
            "human_notes": notes
        }

    def _get_summary(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM candidates")
        total = cur.fetchone()[0]
        conn.close()
        return {
            "total_candidates": total,
            "area": "Kharghar, Navi Mumbai",
            "crs": "EPSG:32643 (UTM 43N)",
            "version": "1.0.0"
        }

    def _run_shade_simulation(self, lat: float, lon: float, width: float, length: float, height: float) -> dict:
        from shade_engine import ShadeEngine
        engine = ShadeEngine(latitude=lat, longitude=lon, grid_resolution_m=0.5, min_solar_access_threshold_pct=80.0)
        res = engine.simulate(
            candidate_id="KHAR_LIVE_SIM",
            roof_width_m=width,
            roof_length_m=length,
            building_height_m=height
        )
        return {
            "candidate_id": res.candidate_id,
            "latitude": res.latitude,
            "longitude": res.longitude,
            "grid_resolution_m": res.grid_resolution_m,
            "total_grid_cells": res.total_grid_cells,
            "unshaded_grid_cells_80pct": res.unshaded_grid_cells_80pct,
            "mean_solar_access_pct": res.mean_solar_access_pct,
            "usable_unshaded_area_m2": res.usable_unshaded_area_m2,
            "total_roof_area_m2": res.total_roof_area_m2,
            "shading_factor": res.shading_factor,
            "baseline_ghi_kwh_m2_yr": res.baseline_ghi_kwh_m2_yr,
            "effective_irradiance_factor": res.effective_irradiance_factor,
            "net_irradiance_factor": res.net_irradiance_factor,
            "annual_solar_access_matrix": res.annual_solar_access_matrix.tolist(),
            "filtered_solar_access_matrix": res.filtered_solar_access_matrix.tolist()
        }

def run_server():
    os.makedirs("public", exist_ok=True)
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, HeliosRequestHandler)
    print(f"Server running on http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
