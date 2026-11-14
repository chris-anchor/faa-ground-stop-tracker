#!/usr/bin/env python3
"""Update data.json from the FAA NAS Status public API."""

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FAA_URL = "https://nasstatus.faa.gov/api/airport-events"
FLIGHTAWARE_URL = "https://www.flightaware.com/live/cancelled/"
DATA_FILE = Path("data.json")


def fetch_events():
    req = urllib.request.Request(FAA_URL, headers={"User-Agent": "faa-ground-stop-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    if isinstance(payload, dict):
        return payload.get("items", [])
    return payload


def fetch_flightaware():
    req = urllib.request.Request(
        FLIGHTAWARE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; faa-ground-stop-tracker/1.0)",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    def count(label):
        match = re.search(re.escape(label) + r".*?([0-9][0-9,]*)", html, re.S)
        return int(match.group(1).replace(",", "")) if match else None

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delays_today": count("Total delays today:"),
        "delays_us": count("Total delays within, into, or out of the United States today:"),
        "cancellations_today": count("Total cancellations today:"),
        "cancellations_us": count("Total cancellations within, into, or out of the United States today:"),
        "source_url": FLIGHTAWARE_URL,
    }


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
    old_snapshot = json.dumps(
        {"nas": data.get("nas", {}), "flightaware": data.get("flightaware", {})},
        sort_keys=True,
    )

    try:
        flightaware = fetch_flightaware()
    except Exception as exc:  # noqa: BLE001
        flightaware = data.get("flightaware", {})
        print(f"FlightAware fetch failed: {exc}")

    data["generatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data["nas"] = nas
    data["flightaware"] = flightaware

    us = data.get("us", {})
    if nas["groundStops"]:
        us["status"] = "WARNING"
        us["groundStop"] = "Active"
    else:
        us["groundStop"] = "Lifted"
    data["us"] = us

    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n")

    new_snapshot = json.dumps(
        {"nas": nas, "flightaware": flightaware},
        sort_keys=True,
    )

    if old_snapshot == new_snapshot:
        print("FAA NAS and FlightAware data unchanged; no commit needed.")
    else:
        print(
            f"Updated FAA NAS data: {len(ground_stops)} ground stop(s), "
            f"{len(airport_closures)} closure(s), {len(ground_delays)} ground delay(s); "
            f"FlightAware US delays/cancels: {flightaware.get('delays_us')}/{flightaware.get('cancellations_us')}."
        )


if __name__ == "__main__":
    main()