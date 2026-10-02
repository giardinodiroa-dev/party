#!/usr/bin/env python3
"""The eye-exam site: serves the clips, takes his feedback, tells Claude when he is done.
GET /            the index · GET /clips/<id>.html  a scene · POST /feedback {clip, text}
POST /done       marks the exam finished · GET /feedback.json  everything he wrote."""
from __future__ import annotations
import json, sys, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEEDBACK = ROOT / "feedback.json"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8891


def load() -> dict:
    try:
        return json.loads(FEEDBACK.read_text())
    except Exception:
        return {"clips": {}, "done": False, "updated": None}


def save(d: dict) -> None:
    d["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = FEEDBACK.with_suffix(".json.tmp"); tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False)); tmp.replace(FEEDBACK)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        if self.path == "/clips.json":
            clips = sorted(p.stem for p in (ROOT / "clips").glob("*.html"))
            out = json.dumps({"clips": clips, "feedback": load()}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out); return
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        d = load()
        if self.path == "/feedback":
            clip = str(body.get("clip", "")); text = str(body.get("text", "")).strip()
            verdict = str(body.get("verdict", ""))
            d["clips"][clip] = {"text": text, "verdict": verdict, "at": time.strftime("%H:%M:%S")}
            d["done"] = False
        elif self.path == "/done":
            d["done"] = True
        save(d)
        out = json.dumps({"ok": True, "saved": len(d["clips"]), "done": d["done"]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


if __name__ == "__main__":
    print(f"eye exam at http://localhost:{PORT}/  (feedback → {FEEDBACK})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
