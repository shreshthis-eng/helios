"""
server.py
REST API and Web Server for Helios Solar Rooftop Prospecting
"""

import os
import json
import sqlite3
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from helios.p5_integration import Person5PlatformEngineer

PORT = 8000
DB_PATH = "helios_database.sqlite"

class HeliosRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/candidates":
            self._send_json(self._get_candidates_geojson())
        elif path.startswith("/api/candidates/"):
            cand_id = path.replace("/api/candidates/", "")
            self._send_json(self._get_candidate_detail(cand_id))
        elif path == "/api/summary":
            self._send_json(self._get_summary())
        elif path == "/" or path == "/index.html":
            self._serve_static("public/index.html", "text/html")
        else:
            # serve static files from public directory
            static_file = os.path.join("public", path.lstrip("/"))
            if os.path.exists(static_file) and not os.path.isdir(static_file):
                ext = os.path.splitext(static_file)[1]
                content_type = "text/html"
                if ext == ".css": content_type = "text/css"
                elif ext == ".js": content_type = "application/javascript"
                elif ext == ".json": content_type = "application/json"
                self._serve_static(static_file, content_type)
            else:
                self.send_error(404, "File Not Found")

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

def run_server():
    os.makedirs("public", exist_ok=True)
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, HeliosRequestHandler)
    print(f"Server running on http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
