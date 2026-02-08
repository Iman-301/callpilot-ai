"""Google Places API integration for finding nearby service providers."""

import json
import math
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

APP_ROOT = Path(__file__).resolve().parent
PROVIDERS_PATH = APP_ROOT / "data" / "providers.json"

# Map our service names to Google Places types
SERVICE_TO_PLACES_TYPE = {
    "dentist": "dentist",
    "auto_repair": "car_repair",
    "doctor": "doctor",
    "hairdresser": "hair_care",
}

# Reverse map for labeling results
PLACES_TYPE_TO_SERVICE = {v: k for k, v in SERVICE_TO_PLACES_TYPE.items()}


def _get_api_key() -> Optional[str]:
    return os.environ.get("GOOGLE_PLACES_API_KEY")


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _generate_mock_slots(date_str: str, min_slots: int = 1, max_slots: int = 4) -> List[str]:
    """Generate random availability slots during business hours for a given date.

    Each provider gets a random number of 1-hour slots between 09:00 and 17:00.
    Slots are on the hour or half-hour and sorted chronologically.
    """
    possible_times = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
        "15:00", "15:30", "16:00", "16:30",
    ]
    count = random.randint(min_slots, min(max_slots, len(possible_times)))
    chosen = sorted(random.sample(possible_times, count))
    return [f"{date_str} {t}" for t in chosen]


def search_nearby(
    service: str,
    lat: float,
    lng: float,
    radius: int = 5000,
    max_results: int =15,
    date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for nearby providers using Google Places Nearby Search API.

    Args:
        service: One of 'dentist', 'auto_repair', 'doctor', 'hairdresser'
        lat: User latitude
        lng: User longitude
        radius: Search radius in meters (default 5000 = ~3 miles)
        max_results: Maximum number of results to return
        date: Date string (YYYY-MM-DD) for mock availability slots.
              Defaults to today if not provided.

    Returns:
        List of provider dicts in the same format as providers.json
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GOOGLE_PLACES_API_KEY not set in environment")

    places_type = SERVICE_TO_PLACES_TYPE.get(service)
    if not places_type:
        raise ValueError(
            f"Unknown service '{service}'. Must be one of: {list(SERVICE_TO_PLACES_TYPE.keys())}"
        )

    # Step 1: Nearby Search
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": places_type,
        "key": api_key,
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API error: {data.get('status')} - {data.get('error_message', '')}")

    results = data.get("results", [])[:max_results]

    # Step 2: For each result, fetch phone number via Place Details
    providers = []
    for place in results:
        place_id = place.get("place_id")
        name = place.get("name", "Unknown")
        rating = place.get("rating", 0.0)
        place_lat = place.get("geometry", {}).get("location", {}).get("lat", lat)
        place_lng = place.get("geometry", {}).get("location", {}).get("lng", lng)
        distance = round(_haversine_miles(lat, lng, place_lat, place_lng), 1)
        address = place.get("vicinity", "")
        open_now = place.get("opening_hours", {}).get("open_now")

        # Fetch phone number from Place Details
        phone = _get_phone_number(api_key, place_id) if place_id else None

        provider = {
            "name": name,
            "service": service,
            "phone": phone or "",
            "address": address,
            "availability": _generate_mock_slots(date),
            "rating": rating,
            "distance_miles": distance,
            "place_id": place_id,
            "open_now": open_now,
        }
        providers.append(provider)

    return providers


def _get_phone_number(api_key: str, place_id: str) -> Optional[str]:
    """Fetch the phone number for a place via the Place Details API."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "international_phone_number",
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return result.get("international_phone_number")
    except Exception:
        return None


def search_all_services(
    lat: float,
    lng: float,
    radius: int = 5000,
    max_per_service: int = 15,
    date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for all supported service types near a location."""
    all_providers = []
    for service in SERVICE_TO_PLACES_TYPE:
        try:
            providers = search_nearby(service, lat, lng, radius, max_per_service, date=date)
            all_providers.extend(providers)
        except Exception as e:
            print(f"[places] Error searching {service}: {e}")
    return all_providers


def save_providers(providers: List[Dict[str, Any]], merge: bool = False) -> Path:
    """
    Save providers to providers.json.

    Args:
        providers: List of provider dicts
        merge: If True, merge with existing providers (dedupe by place_id).
               If False, replace entirely.
    """
    if merge and PROVIDERS_PATH.exists():
        with open(PROVIDERS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f).get("providers", [])
        # Dedupe by place_id, preferring new data
        existing_map = {p.get("place_id"): p for p in existing if p.get("place_id")}
        for p in providers:
            pid = p.get("place_id")
            if pid:
                existing_map[pid] = p
            else:
                existing.append(p)
        # Combine: providers with place_id + those without
        no_pid = [p for p in existing if not p.get("place_id")]
        merged = list(existing_map.values()) + no_pid
        providers = merged

    PROVIDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVIDERS_PATH, "w", encoding="utf-8") as f:
        json.dump({"providers": providers}, f, indent=2, ensure_ascii=False)

    return PROVIDERS_PATH
