import json
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\src\_data\academies.json"

CUTOFF = (datetime.now(timezone.utc) - timedelta(days=365 * 2)).isoformat()

FIELDS = [
    "aca_asnum", "name", "inst_type", "sido", "sigungu", "status", "closed_at",
    "category_name", "category_slug", "course_name", "fee_raw", "has_fee_data",
    "capacity_total", "capacity_hourly", "address_road", "address_detail", "zipcode",
    "phone", "reg_date", "lat", "lng", "slug",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM academies WHERE sido = ? AND sigungu = ? ORDER BY name",
        ("서울", "도봉구"),
    ).fetchall()

    out = []
    skipped_old_closed = 0
    for r in rows:
        # NEIS API에는 폐원일자 필드가 없어 closed_at(당사 최초 감지 시점)을 대리 기준으로 사용.
        # 최초 백필 시점에는 모든 폐원 건의 closed_at이 오늘 날짜이므로 이번 빌드에서는
        # 실질적으로 컷오프에 걸러지는 건이 없음 — 배치가 누적되며 점차 정확해짐.
        if r["status"] == "폐원" and r["closed_at"] and r["closed_at"] < CUTOFF:
            skipped_old_closed += 1
            continue

        rec = {f: r[f] for f in FIELDS}
        rec["has_fee_data"] = bool(rec["has_fee_data"])
        rec["fee_parsed"] = json.loads(r["fee_parsed"]) if r["fee_parsed"] else None
        out.append(rec)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"exported {len(out)} academies (skipped old-closed: {skipped_old_closed})")


if __name__ == "__main__":
    main()
