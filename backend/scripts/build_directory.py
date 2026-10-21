"""Build the blood-bank directory snapshot (W2) from eRaktKosh's public Blood Bank Directory.

    python scripts/build_directory.py              # TinyFish Fetch if TINYFISH_API_KEY is set, else direct HTTPS
    python scripts/build_directory.py --no-geocode

Writes data/eraktkosh_directory.json, which seed.py loads instead of the small hand-made list.
Addresses are geocoded once with OpenStreetMap Nominatim (max 1 request/second, results cached in
data/geocode_cache.json). Emails are never stored. Re-run any time; the app can also refresh the
directory live from /admin (TinyFish Fetch)."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import directory  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-geocode", action="store_true")
    args = ap.parse_args()
    rows, via = directory.download(directory.NCR_SCOPE)
    print(f"{len(rows)} blood centres via {via}")
    if not args.no_geocode:
        directory.geocode_rows(rows, progress=lambda i, n: print(f"\rgeocoding {i}/{n}", end="", flush=True))
        print()
    out = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fetched_via": via,
           "source": "eRaktKosh Blood Bank Directory (public)", "banks": rows}
    directory.SNAPSHOT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    quality = {q: sum(1 for r in rows if r.get("geo_quality") == q) for q in ("geocoded", "district", "none")}
    print(f"wrote {directory.SNAPSHOT} {quality}")
