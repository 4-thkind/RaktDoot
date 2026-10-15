"""Wipe the database and seed blood banks + synthetic donors.

    python scripts/seed_donors.py            # 200 donors
    python scripts/seed_donors.py --donors 1000
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, init_db  # noqa: E402
from app.seed import reset_and_seed  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--donors", type=int, default=200)
    args = ap.parse_args()
    init_db()
    with SessionLocal() as db:
        print(reset_and_seed(db, args.donors))
