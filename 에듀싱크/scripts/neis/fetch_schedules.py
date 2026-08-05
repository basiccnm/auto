"""NEIS SchoolSchedule로 학사일정 수집.

사용 예:
    python fetch_schedules.py 20260301 20270228          # DB의 전체 학교
    python fetch_schedules.py 20260301 20270228 B10       # 서울만
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, neis_get, now_iso, load_config, log_etl_error

# 원문 학년별 대상여부 플래그. 초등은 1~6, 중고는 필드 자체가 없을 수 있음(§원천 필드 특성) — 있는 것만 저장.
GRADE_FLAG_FIELDS = [
    "ONE_GRADE_EVENT_YN", "TW_GRADE_EVENT_YN", "THREE_GRADE_EVENT_YN",
    "FR_GRADE_EVENT_YN", "FIV_GRADE_EVENT_YN", "SIX_GRADE_EVENT_YN",
]


def upsert_schedule(conn, school_id, row):
    grade_flags = {f: row.get(f) for f in GRADE_FLAG_FIELDS if row.get(f) is not None}
    conn.execute(
        """
        INSERT INTO academic_schedules (
            school_id, event_date, event_name, event_content, closure_type,
            grade_flags, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (school_id, event_date, event_name) DO UPDATE SET
            event_content=excluded.event_content, closure_type=excluded.closure_type,
            grade_flags=excluded.grade_flags, last_synced_at=excluded.last_synced_at
        """,
        (
            school_id,
            row["AA_YMD"],
            row["EVENT_NM"],
            row.get("EVENT_CNTNT"),
            row.get("SBTR_DD_SC_NM"),
            json.dumps(grade_flags, ensure_ascii=False),
            now_iso(),
        ),
    )


def main(from_ymd, to_ymd, office_codes=None):
    config = load_config()
    key = config["neis_api_key"]
    conn = get_db()

    query = "SELECT id, office_code, school_code, name FROM schools"
    params = []
    if office_codes:
        placeholders = ",".join("?" * len(office_codes))
        query += f" WHERE office_code IN ({placeholders})"
        params = office_codes
    schools = conn.execute(query, params).fetchall()

    fetched, skipped = 0, 0
    for school in schools:
        try:
            rows = neis_get(
                "SchoolSchedule",
                key,
                ATPT_OFCDC_SC_CODE=school["office_code"],
                SD_SCHUL_CODE=school["school_code"],
                AA_FROM_YMD=from_ymd,
                AA_TO_YMD=to_ymd,
                pSize=1000,
            )
        except RuntimeError as e:
            print(f"  [스킵] {school['name']}: {e}")
            log_etl_error(conn, "fetch_schedules", e, target_school_id=school["id"])
            skipped += 1
            continue

        # 같은 날짜에 동일 행사명이 중복으로 오는 경우가 있어(예: 제헌절이 두 번) dedup
        seen = set()
        for row in rows:
            dedup_key = (row["AA_YMD"], row["EVENT_NM"])
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            upsert_schedule(conn, school["id"], row)
        conn.commit()
        fetched += len(seen)
        print(f"  {school['name']}: {len(seen)}건")

    print(f"완료: {fetched}건 적재, {skipped}개 학교 스킵")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python fetch_schedules.py <시작YYYYMMDD> <종료YYYYMMDD> [교육청코드...]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
