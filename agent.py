import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

try:
	# Optional ElevenLabs SDK (latest). If missing, we fall back to text-only.
	from elevenlabs.client import ElevenLabs
except Exception:  # pragma: no cover - optional dependency
	ElevenLabs = None

APP_ROOT = Path(__file__).resolve().parent
CALENDAR_PATH = APP_ROOT / "data" / "calendar.json"

app = FastAPI(title="CallPilot Voice Agent", version="0.1.0")


class TimeWindow(BaseModel):
	date: Optional[str] = None
	start: Optional[str] = None
	end: Optional[str] = None


class AgentRequest(BaseModel):
	provider: Dict[str, Any]
	request: Dict[str, Any]


def _load_busy_slots() -> List[tuple[datetime, datetime]]:
	if not CALENDAR_PATH.exists():
		return []
	try:
		with open(CALENDAR_PATH, "r", encoding="utf-8") as handle:
			data = json.load(handle)
		busy = []
		for item in data.get("user_calendar", {}).get("busy_slots", []):
			start = datetime.fromisoformat(item["start"])
			end = datetime.fromisoformat(item["end"])
			busy.append((start, end))
		return busy
	except Exception:
		return []


def _is_busy(slot_dt: datetime, busy_slots: List[tuple[datetime, datetime]]) -> bool:
	for start, end in busy_slots:
		if start <= slot_dt < end:
			return True
	return False


def _parse_slot(slot_str: Optional[str], date_hint: Optional[str] = None) -> Optional[datetime]:
	if not slot_str:
		return None
	if len(slot_str) == 5 and ":" in slot_str and date_hint:
		return datetime.fromisoformat(f"{date_hint} {slot_str}")
	try:
		return datetime.fromisoformat(slot_str)
	except ValueError:
		return None


def _pick_slot(
	availability: List[str],
	time_window: Optional[Dict[str, Any]],
	busy_slots: List[tuple[datetime, datetime]],
) -> Optional[str]:
	if not availability:
		return None

	date_hint = None
	if time_window:
		date_hint = time_window.get("date")

	parsed = [(slot, _parse_slot(slot, date_hint)) for slot in availability]
	parsed = [(slot, dt) for slot, dt in parsed if dt]
	if not parsed:
		return None

	parsed = [(slot, dt) for slot, dt in parsed if not _is_busy(dt, busy_slots)]
	if not parsed:
		return None

	if not time_window:
		return sorted(parsed, key=lambda item: item[1])[0][0]

	start = _parse_slot(time_window.get("start"), time_window.get("date"))
	end = _parse_slot(time_window.get("end"), time_window.get("date"))
	for slot, dt in sorted(parsed, key=lambda item: item[1]):
		if start and dt < start:
			continue
		if end and dt > end:
			continue
		return slot
	return None


def _get_elevenlabs_client() -> Optional["ElevenLabs"]:
	api_key = os.environ.get("ELEVENLABS_API_KEY")
	if not api_key or ElevenLabs is None:
		return None
	return ElevenLabs(api_key=api_key)


def _tts_lines(lines: List[str]) -> Dict[int, str]:
	client = _get_elevenlabs_client()
	if not client:
		return {}

	voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
	audio_map: Dict[int, str] = {}
	for idx, line in enumerate(lines):
		# Generate short audio per agent line for demo purposes.
		audio = client.text_to_speech.convert(
			voice_id=voice_id,
			text=line,
			model_id="eleven_multilingual_v2",
		)
		audio_map[idx] = base64.b64encode(audio).decode("ascii")
	return audio_map


@app.get("/health")
def health() -> Dict[str, str]:
	return {"status": "ok"}


@app.post("/agent")
def run_agent(payload: AgentRequest) -> Dict[str, Any]:
	provider = payload.provider
	request_payload = payload.request

	availability = provider.get("availability", [])
	time_window = request_payload.get("time_window")
	service = request_payload.get("service", "appointment")

	service_clean = str(service).strip() or "appointment"
	article = "an" if service_clean[:1].lower() in {"a", "e", "i", "o", "u"} else "a"

	window_desc = None
	if time_window:
		window_desc = (
			f"{time_window.get('date', '')} between "
			f"{time_window.get('start', '')} and {time_window.get('end', '')}"
		).strip()

	request_line = f"Agent: I'd like to book {article} {service_clean}"
	if window_desc:
		request_line = f"{request_line} for {window_desc}"
	request_line = f"{request_line}."

	busy_slots = _load_busy_slots()
	slot = _pick_slot(availability, time_window, busy_slots)

	if not slot:
		transcript = [
			f"{provider.get('name', 'Provider')}: Thank you for calling. How can we help?",
			request_line,
			f"{provider.get('name', 'Provider')}: Sorry, no slots match that request.",
			"Agent: Thanks for checking. Please let us know if anything opens up.",
		]
		return {
			"status": "no_availability",
			"provider": provider,
			"slot": None,
			"transcript": transcript,
			"tts_audio_b64": _tts_lines([transcript[1], transcript[3]]),
		}

	transcript = [
		f"{provider.get('name', 'Provider')}: Thank you for calling. How can we help?",
		request_line,
		f"{provider.get('name', 'Provider')}: We can do {slot}.",
		"Agent: Great, please book it under Alex.",
		f"{provider.get('name', 'Provider')}: You're all set for {slot}.",
	]

	return {
		"status": "ok",
		"provider": provider,
		"slot": slot,
		"transcript": transcript,
		"tts_audio_b64": _tts_lines([transcript[1], transcript[3]]),
	}
