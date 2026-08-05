import json
import sqlite3
from datetime import date, timedelta

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\src\_data\dojos.json"

CUTOFF = (date.today() - timedelta(days=365 * 2)).isoformat()

FIELDS = [
    "name", "sport_name", "category_name", "category_slug", "sido", "sigungu", "slug",
    "is_open", "closed_ymd", "address_road", "address_lot", "phone", "leader_count",
    "member_capacity", "license_ymd", "lat", "lng",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM dojos WHERE sido = ? AND sigungu = ? ORDER BY name",
        ("서울", "도봉구"),
    ).fetchall()

    out = []
    skipped_old_closed = 0
    for r in rows:
        if not r["is_open"] and r["closed_ymd"] and r["closed_ymd"] < CUTOFF:
            skipped_old_closed += 1
            continue
        rec = {f: r[f] for f in FIELDS}
        rec["is_open"] = bool(rec["is_open"])
        out.append(rec)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    open_count = sum(1 for r in out if r["is_open"])
    print(
        f"exported {len(out)} dobong dojos (open={open_count}, "
        f"recently-closed={len(out)-open_count}, skipped old-closed={skipped_old_closed})"
    )


if __name__ == "__main__":
    main()
