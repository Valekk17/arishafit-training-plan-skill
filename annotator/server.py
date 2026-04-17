"""
server.py — локальный сервер для ручной разметки start/peak кадров.

Запуск:
    python annotator/server.py
    → http://localhost:8787/

Протокол:
  GET  /                      — annotator/index.html
  GET  /mp4/<id>.mp4          — файл из exercisedb_data/mp4/
  GET  /api/exercises         — список [{id, name, auto, annotated}]
  GET  /api/annotations       — текущий annotations.json (merge auto+manual)
  POST /api/save              — {"id":..., "start_frame":..., "peak_frame":...}
                                 сохраняет в annotations_manual.json
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MP4_DIR = ROOT / "exercisedb_data" / "mp4"
DB = ROOT / "exercisedb_data" / "exercise_db_final.json"
AUTO_F = HERE / "annotations_auto.json"
MANUAL_F = HERE / "annotations_manual.json"
RENAMES_F = HERE / "_renames_all.json"
INDEX_F = HERE / "index.html"

PORT = 8787


def load_json(p, default=None):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def save_json(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# Загружаем БД с именами
print(f"Загружаю БД упражнений из {DB}...")
db = load_json(DB, [])
ex_info = {}
renames = load_json(RENAMES_F, {})
print(f"Загрузил новых имён (Opus): {len(renames)}")

for ex in db:
    eid = ex.get("exerciseId", "")
    if not eid:
        continue
    instr = ex.get("instructions", [])
    ex_info[eid] = {
        "nameRu_old": ex.get("nameRu", "") or ex.get("nameEn", ""),
        "nameRu_new": renames.get(eid, ""),
        "nameEn": ex.get("nameEn", ""),
        "bodyParts": ex.get("bodyPartsRu") or ex.get("bodyParts", []),
        "equipments": ex.get("equipmentsRu") or ex.get("equipments", []),
        "targetMuscles": ex.get("targetMusclesRu") or ex.get("targetMuscles", []),
        "instruction_1": instr[0] if instr else "",
        "instruction_2": instr[1] if len(instr) > 1 else "",
    }
print(f"  имён загружено: {len(ex_info)}")


def get_exercises_list():
    """Список всех упражнений для UI.

    Старт для всех неразмеченных = 0 (всегда, по договорённости).
    Пик — из автодетекта (sharpness × blackness); если нет — 6.
    Ручные аннотации из annotations_manual.json перекрывают всё.
    """
    auto = load_json(AUTO_F, {})
    manual = load_json(MANUAL_F, {})

    out = []
    for mp4 in sorted(MP4_DIR.glob("*.mp4")):
        eid = mp4.stem
        info = ex_info.get(eid, {})
        a = auto.get(eid) or {}
        m = manual.get(eid) or {}
        is_manual = bool(m)
        total = a.get("total_frames") or m.get("total_frames") or 12
        # key_frames: приоритет manual → auto → дефолт [0, 6]
        if m.get("key_frames"):
            key_frames = list(m["key_frames"])
        elif a.get("key_frames"):
            key_frames = list(a["key_frames"])
        else:
            # Обратная совместимость со старым форматом start_frame/peak_frame
            sf = m.get("start_frame", a.get("start_frame", 0))
            pf = m.get("peak_frame", a.get("peak_frame", min(6, max(1, total - 1))))
            key_frames = sorted({sf, pf})
        out.append({
            "id": eid,
            "nameRu": info.get("nameRu_new") or info.get("nameRu_old") or eid,
            "nameRu_old": info.get("nameRu_old", ""),
            "nameRu_new": info.get("nameRu_new", ""),
            "nameEn": info.get("nameEn", ""),
            "bodyParts": info.get("bodyParts", []),
            "equipments": info.get("equipments", []),
            "targetMuscles": info.get("targetMuscles", []),
            "instruction_1": info.get("instruction_1", ""),
            "instruction_2": info.get("instruction_2", ""),
            "total_frames": total,
            "fps": a.get("fps") or m.get("fps") or 10,
            "key_frames": key_frames,
            "confidence": a.get("confidence", 0),
            "reliable": a.get("reliable", False),
            "ratio": a.get("ratio", 0),
            "manual": is_manual,
        })
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Тихо — не засорять консоль
        pass

    def _send(self, code, content_type, body, extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        self._send(code, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            if INDEX_F.exists():
                self._send(200, "text/html; charset=utf-8", INDEX_F.read_bytes())
            else:
                self._send(404, "text/plain", "index.html not found")
            return

        if path == "/api/exercises":
            self._json(200, get_exercises_list())
            return

        if path == "/api/annotations":
            # Объединение auto + manual (manual перекрывает)
            auto = load_json(AUTO_F, {})
            manual = load_json(MANUAL_F, {})
            merged = {**auto}
            for eid, m in manual.items():
                merged[eid] = {**auto.get(eid, {}), **m, "auto": False}
            self._json(200, merged)
            return

        if path.startswith("/mp4/"):
            fname = path[len("/mp4/"):]
            fpath = MP4_DIR / fname
            if fpath.exists() and fpath.suffix == ".mp4":
                self._send(200, "video/mp4", fpath.read_bytes(),
                           {"Accept-Ranges": "bytes"})
            else:
                self._send(404, "text/plain", "MP4 not found")
            return

        self._send(404, "text/plain", "not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/save":
            self._send(404, "text/plain", "not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
        except Exception as e:
            self._json(400, {"error": f"bad payload: {e}"})
            return

        eid = payload.get("id", "").strip()
        if not eid:
            self._json(400, {"error": "no id"})
            return

        manual = load_json(MANUAL_F, {})

        if payload.get("delete"):
            manual.pop(eid, None)
        else:
            auto = load_json(AUTO_F, {}).get(eid, {})
            # Новый формат: key_frames: [int]. Старый формат поддерживаем для совместимости.
            kf = payload.get("key_frames")
            if kf is None:
                sf = int(payload.get("start_frame", 0))
                pf = int(payload.get("peak_frame", 6))
                kf = sorted({sf, pf})
            else:
                kf = sorted({int(f) for f in kf})
            entry = {
                "total_frames": payload.get("total_frames") or auto.get("total_frames") or 0,
                "fps": payload.get("fps") or auto.get("fps") or 10,
                "key_frames": kf,
                "manual": True,
            }
            manual[eid] = entry

        save_json(MANUAL_F, manual)
        self._json(200, {"ok": True, "total_manual": len(manual)})


def main():
    os.chdir(HERE)
    srv = HTTPServer(("127.0.0.1", PORT), H)
    print()
    print(f"✓ Annotator server: http://localhost:{PORT}/")
    print(f"  MP4 dir:   {MP4_DIR}")
    print(f"  Auto:      {AUTO_F.name}")
    print(f"  Manual:    {MANUAL_F.name}")
    print()
    print("Ctrl+C для остановки")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Остановлен.")


if __name__ == "__main__":
    main()
