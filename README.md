# FAA Ground Stop Tracker

A public, free dashboard tracking the 13–14 November 2026 FAA nationwide ground stop, with priority on Alaska and Hawaii ground saturation.

## Live dashboard

After enabling GitHub Pages:

`https://chris-anchor.github.io/faa-ground-stop-tracker/`

## What it shows

- FAA root-cause status
- Cyberattack assessment
- Ground-stop status
- U.S. nationwide / Hawaii / Alaska saturation cards
- Airport watchlist, sorted most serious first
- FAA NAS live feed from `https://nasstatus.faa.gov/api/airport-events`

## How it updates

- The dashboard auto-refreshes every 6 minutes.
- A GitHub Action runs every 5 minutes and updates `data.json` from the FAA NAS public API.
- GitHub Pages serves the static dashboard for free.

## Data sources

- FAA National Airspace System Status: https://nasstatus.faa.gov/
- FAA ATCSCC advisories: https://www.fly.faa.gov/ois/
- FlightAware: https://www.flightaware.com/
- Flightradar24: https://www.flightradar24.com/
- Hawaii DOT: https://hidot.hawaii.gov/
- Alaska DOT&PF: https://dot.alaska.gov/aias/

## Disclaimer

This is an independent research artifact. It is not an official FAA finding. The FAA investigation is ongoing. For operational flight planning, use official FAA, ATC, and airline sources.