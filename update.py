#!/usr/bin/env python3
"""Update data.json from the FAA NAS Status public API."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FAA_URL = "https://nasstatus.faa.gov/api/airport-events"
DATA_FILE = Path("data.json")


def fetch_events():
    req = urllib.request.Request(FAA_URL, headers={"User-Agent": "faa-ground-stop-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    if isinstance(payload, dict):
        return payload.get("items", [])
    return payload


def as_text(value):
    return str(value).strip() if value is not None else ""


def latest_update(items):
    stamps = []
    for item in items:
        for key in ("groundStop", "groundDelay", "airportClosure", "freeForm", "arrivalDelay", "departureDelay"):
            block = item.get(key)
            if isinstance(block, dict):
                for stamp_key in ("updateTime", "updatedAt", "sourceTimeStamp", "createdAt"):
                    if block.get(stamp_key):
                        stamps.append(block[stamp_key])
    if stamps:
        return max(stamps)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    items = fetch_events()

    ground_stops = []
    airport_closures = []
    ground_delays = []

    for item in items:
        airport = item.get("airportId") or item.get("airportLongName") or "UNKNOWN"

        gs = item.get("groundStop")
        if isinstance(gs, dict):
            ground_stops.append({
                "airport": airport,
                "reason": gs.get("reason") or gs.get("scope") or "Ground stop",
                "scope": gs.get("scope") or gs.get("reason") or "ALL",
                "end": gs.get("endTime") or gs.get("end") or "TBD",
            })

        ac = item.get("airportClosure")
        if isinstance(ac, dict):
            airport_closures.append({
                "airport": airport,
                "reason": ac.get("reason") or ac.get("text") or "Airport closure",
                "start": ac.get("startTime") or ac.get("start") or "TBD",
                "reopen": ac.get("endTime") or ac.get("reopen") or "TBD",
            })

        gd = item.get("groundDelay")
        if isinstance(gd, dict):
            ground_delays.append({
                "airport": airport,
                "reason": gd.get("impactingCondition") or "Ground delay",
                "average": gd.get("avgDelay") if gd.get("avgDelay") is not None else "—",
                "max": gd.get("maxDelay") if gd.get("maxDelay") is not None else "—",
            })

    nas = {
        "updated": latest_update(items),
        "groundStops": ground_stops,
        "airportClosures": airport_closures,
        "groundDelays": ground_delays,
        "itemCount": len(items),
    }

    # The airport-events feed does not always expose the national ground stop as a
    # groundStop object. Detect the national stop from departure-delay reasons.
    national_stop = any(
        "NATIONAL STOP" in str((item.get("departureDelay") or {}).get("reason", "")).upper()
        for item in items
    )
    if national_stop and not ground_stops:
        nas["groundStops"].append({
            "airport": "ALL",
            "reason": "NATIONAL STOP",
            "scope": "ALL",
            "end": "TBD",
        })

    data = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else {}
    old_nas = json.dumps(data.get("nas", {}), sort_keys=True)
    new_nas = json.dumps(nas, sort_keys=True)

    data["generatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data["nas"] = nas

    us = data.get("us", {})
    if nas["groundStops"]:
        us["status"] = "WARNING"
        us["groundStop"] = "Active"
    data["us"] = us

    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n")

    if old_nas == new_nas:
        print("FAA NAS data unchanged; no commit needed.")
    else:
        print(f"Updated FAA NAS data: {len(ground_stops)} ground stop(s), {len(airport_closures)} closure(s), {len(ground_delays)} ground delay(s).")


if __name__ == "__main__":
    main()