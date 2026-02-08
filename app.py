import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

from swarm.orchestrator import run_swarm_sync, stream_swarm_sync

APP_ROOT = Path(__file__).resolve().parent
PROVIDERS_PATH = APP_ROOT / "data" / "providers.json"

app = Flask(__name__, static_folder='data')
CORS(app)  # Enable CORS for all routes


def load_providers():
    with open(PROVIDERS_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("providers", [])


def filter_providers(providers, service, limit):
    filtered = providers
    if service:
        filtered = [p for p in providers if p.get("service") == service]
    if limit:
        filtered = filtered[:limit]
    return filtered


def _load_busy_slots():
    calendar_path = APP_ROOT / "data" / "calendar.json"
    try:
        with open(calendar_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        busy = []
        for item in data.get("user_calendar", {}).get("busy_slots", []):
            start = datetime.fromisoformat(item["start"])
            end = datetime.fromisoformat(item["end"])
            busy.append((start, end))
        return busy
    except Exception:
        return []


def _overlaps(slot_start, slot_end, busy_slots):
    for busy_start, busy_end in busy_slots:
        if slot_start < busy_end and slot_end > busy_start:
            return True
    return False


def _parse_time(time_str, date_str):
    if not time_str or not date_str:
        return None
    return datetime.fromisoformat(f"{date_str} {time_str}")


def _filter_time_window(available, time_window):
    if not time_window:
        return available
    date_str = time_window.get("date")
    start = _parse_time(time_window.get("start"), date_str)
    end = _parse_time(time_window.get("end"), date_str)
    if not start and not end:
        return available
    filtered = []
    for slot in available:
        slot_dt = _parse_time(slot, date_str)
        if not slot_dt:
            continue
        if start and slot_dt < start:
            continue
        if end and slot_dt > end:
            continue
        filtered.append(slot)
    return filtered


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/")
def index():
    return jsonify(
        {
            "service": "CallPilot Swarm Orchestrator",
            "endpoints": ["/health", "/swarm", "/swarm/stream"],
        }
    )


@app.get("/data/calendar.json")
def get_calendar():
    """Serve calendar data for frontend"""
    calendar_path = APP_ROOT / "data" / "calendar.json"
    try:
        with open(calendar_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"user_calendar": {"busy_slots": []}}), 404


@app.post("/swarm")
def swarm():
    payload = request.get_json(silent=True) or {}
    service = payload.get("service")
    limit = payload.get("limit")
    providers = filter_providers(load_providers(), service, limit)
    if not providers:
        return jsonify({"error": "no providers available"}), 400

    result = run_swarm_sync(payload, providers)
    return jsonify(result)


@app.post("/swarm/stream")
def swarm_stream():
    payload = request.get_json(silent=True) or {}
    service = payload.get("service")
    limit = payload.get("limit")
    print("Payload received for streaming swarm:", payload)
    providers = filter_providers(load_providers(), service, limit)
    if not providers:
        return jsonify({"error": "no providers available"}), 400

    def event_stream():
        # Output NDJSON format for frontend compatibility
        for event in stream_swarm_sync(payload, providers):
            yield json.dumps(event) + "\n"

    return Response(stream_with_context(event_stream()), mimetype="application/x-ndjson")


@app.post("/check-calendar")
def check_calendar():
    payload = request.get_json(silent=True) or {}
    date_str = payload.get("date")
    time_window = payload.get("time_window") or {}
    if not time_window:
        time_window = {
            "start": payload.get("start"),
            "end": payload.get("end"),
        }

    if not date_str:
        return jsonify({"error": "date is required"}), 400

    busy_slots = _load_busy_slots()

    window_start = _parse_time(time_window.get("start") or "09:00", date_str)
    window_end = _parse_time(time_window.get("end") or "17:00", date_str)
    if not window_start or not window_end or window_start >= window_end:
        return jsonify({"error": "invalid time window"}), 400

    available = []
    slot_start = window_start
    while slot_start < window_end:
        slot_end = slot_start + timedelta(minutes=60)
        if slot_end > window_end:
            break
        if not _overlaps(slot_start, slot_end, busy_slots):
            available.append(
                {
                    "date": date_str,
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                }
            )
        slot_start = slot_start + timedelta(minutes=60)

    return jsonify({"available_slots": available})


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
