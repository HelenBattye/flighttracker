"""Summary of sightings.csv: which airlines, aircraft, routes and hours you see most.

Run `python -m flighttracker.stats` for a text summary; the browser view also serves it at /stats.
"""

import csv
from collections import Counter
from html import escape
from pathlib import Path

from .sightings import LOG


def load(path: Path = LOG) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def summarise(rows: list[dict], top: int = 5) -> dict:
    def count(key: str) -> list[tuple[str, int]]:
        return Counter(r[key] for r in rows if r.get(key)).most_common(top)

    routes = Counter(f"{r['origin']} > {r['destination']}" for r in rows if r.get("origin") and r.get("destination"))
    hours = Counter(int(r["time"][11:13]) for r in rows if len(r.get("time", "")) >= 13)
    distances = [float(r["distance_km"]) for r in rows if r.get("distance_km")]
    return {
        "total": len(rows),
        "unique_aircraft": len({r["hex"] for r in rows}),
        "airlines": count("airline"),
        "types": count("aircraft_type"),
        "routes": routes.most_common(top),
        "hours": [(f"{h:02d}:00", hours.get(h, 0)) for h in range(24)],
        "closest_km": min(distances) if distances else None,
    }


def format_text(s: dict) -> str:
    if not s["total"]:
        return "No sightings yet. Run the tracker for a while first."
    lines = [f"{s['total']} sightings, {s['unique_aircraft']} different aircraft, closest {s['closest_km']} km"]
    for title, key in [("Airlines", "airlines"), ("Aircraft", "types"), ("Routes", "routes")]:
        lines += ["", title] + [f"  {n:>4}  {name}" for name, n in s[key]]
    return "\n".join(lines)


def _bars(pairs: list[tuple[str, int]]) -> str:
    peak = max((n for _, n in pairs), default=0) or 1
    return "".join(
        f"<div class=row><span class=label>{escape(name)}</span>"
        f"<span class=bar style='width:{n / peak * 100:.0f}%'></span><span class=n>{n}</span></div>"
        for name, n in pairs
    )


def render_html(s: dict) -> bytes:
    if not s["total"]:
        body = "<p>No sightings yet. Leave the tracker running for a while.</p>"
    else:
        body = (
            f"<p>{s['total']} sightings, {s['unique_aircraft']} different aircraft, closest {s['closest_km']} km</p>"
            f"<h2>Airlines</h2>{_bars(s['airlines'])}<h2>Aircraft</h2>{_bars(s['types'])}"
            f"<h2>Routes</h2>{_bars(s['routes'])}<h2>By hour</h2>{_bars(s['hours'])}"
        )
    page = (
        "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Flight tracker stats</title><style>"
        "body{font:16px system-ui;max-width:640px;margin:2rem auto;padding:0 1rem;color:#222}"
        "h2{margin:1.5rem 0 .4rem;font-size:1rem}.row{display:flex;align-items:center;gap:.5rem;margin:2px 0}"
        ".label{flex:0 0 11rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
        ".bar{height:.9rem;background:#2b6cb0;border-radius:2px;min-width:1px}.n{color:#666}"
        f"</style><h1>Flight tracker stats</h1>{body}<p><a href=/>Live card</a></p>"
    )
    return page.encode()


if __name__ == "__main__":
    print(format_text(summarise(load())))
