"""Sync 3 правок nameRu из JSON в Postgres (Priority 3 defer)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.session import SessionLocal
from db import models as M

FIXES = {
    "8ARQ9Hw": "Высокая тяга гири сумо",
    "0CXGHya": "Кроссовер (вариант)",
    "ZgwWBoC": "Тяга-гребля в блоке (по Тибодо)",
}


def main() -> int:
    with SessionLocal() as s:
        updated = 0
        for eid, new_name in FIXES.items():
            ex = s.get(M.Exercise, eid)
            if ex is None:
                print(f"[MISS] {eid} not found in DB")
                continue
            old = ex.name_ru
            if old == new_name:
                print(f"[SKIP] {eid} already == {new_name!r}")
                continue
            ex.name_ru = new_name
            updated += 1
            print(f"[UPD ] {eid}")
            print(f"       was: {old!r}")
            print(f"       now: {new_name!r}")
        if updated:
            s.commit()
            print(f"\n[OK] {updated} rows committed")
        else:
            print("\n[NOP] nothing to update")

    # Verify
    with SessionLocal() as s:
        print("\n=== VERIFY ===")
        for eid in FIXES:
            ex = s.get(M.Exercise, eid)
            print(f"{eid}: name_ru={ex.name_ru!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
