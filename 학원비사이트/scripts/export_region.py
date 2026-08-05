import json
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
ACADEMIES_OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\src\_data\academies.json"
DOJOS_OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\src\_data\dojos.json"

ACADEMY_CUTOFF = (datetime.now(timezone.utc) - timedelta(days=365 * 2)).isoformat()
DOJO_CUTOFF = (date.today() - timedelta(days=365 * 2)).isoformat()

ACADEMY_FIELDS = [
    "aca_asnum", "name", "inst_type", "sido", "sigungu", "status", "closed_at",
    "category_name", "category_slug", "course_name", "fee_raw", "has_fee_data",
    "capacity_total", "capacity_hourly", "address_road", "address_detail", "zipcode",
    "phone", "reg_date", "lat", "lng", "slug",
]

DOJO_FIELDS = [
    "name", "sport_name", "category_name", "category_slug", "sido", "sigungu", "slug",
    "is_open", "closed_ymd", "address_road", "address_lot", "phone", "leader_count",
    "member_capacity", "license_ymd", "lat", "lng",
]


def export_academies(conn, sido_list):
    placeholders = ",".join("?" * len(sido_list))
    rows = conn.execute(
        f"SELECT * FROM academies WHERE sido IN ({placeholders}) ORDER BY sido, sigungu, name",
        sido_list,
    ).fetchall()

    out = []
    skipped_old_closed = 0
    for r in rows:
        if r["status"] == "폐원" and r["closed_at"] and r["closed_at"] < ACADEMY_CUTOFF:
            skipped_old_closed += 1
            continue
        rec = {f: r[f] for f in ACADEMY_FIELDS}
        rec["has_fee_data"] = bool(rec["has_fee_data"])
        rec["fee_parsed"] = json.loads(r["fee_parsed"]) if r["fee_parsed"] else None
        out.append(rec)

    with open(ACADEMIES_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"academies: exported {len(out)} (skipped old-closed: {skipped_old_closed})")


def export_dojos(conn, sido_list):
    placeholders = ",".join("?" * len(sido_list))
    rows = conn.execute(
        f"SELECT * FROM dojos WHERE sido IN ({placeholders}) ORDER BY sido, sigungu, name",
        sido_list,
    ).fetchall()

    out = []
    skipped_old_closed = 0
    for r in rows:
        if not r["is_open"] and r["closed_ymd"] and r["closed_ymd"] < DOJO_CUTOFF:
            skipped_old_closed += 1
            continue
        rec = {f: r[f] for f in DOJO_FIELDS}
        rec["is_open"] = bool(rec["is_open"])
        out.append(rec)

    with open(DOJOS_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    open_count = sum(1 for r in out if r["is_open"])
    print(
        f"dojos: exported {len(out)} (open={open_count}, recently-closed={len(out)-open_count}, "
        f"skipped old-closed: {skipped_old_closed})"
    )


def main():
    sido_list = sys.argv[1:] or ["서울", "경기", "인천"]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"exporting region: {sido_list}")
    export_academies(conn, sido_list)
    export_dojos(conn, sido_list)


if __name__ == "__main__":
    main()
