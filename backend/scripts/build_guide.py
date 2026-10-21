"""Build the family-guide knowledge base snapshot (F13) from official pages.

    python scripts/build_guide.py     # TinyFish Fetch if TINYFISH_API_KEY is set, else direct HTTPS

Writes data/guide_kb.json (passages + source URLs). /admin can rebuild it live."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import guide  # noqa: E402

if __name__ == "__main__":
    chunks = guide.build()
    out = {"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sources": [u for _, u in guide.SOURCES], "chunks": chunks}
    guide.KB.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(chunks)} passages from {len(guide.SOURCES)} sources -> {guide.KB}")
