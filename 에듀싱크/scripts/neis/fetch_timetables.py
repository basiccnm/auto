"""NEIS els/mis/hisTimetable로 시간표 수집. school_kind로 엔드포인트 자동 분기.

GRADE/CLASS_NM을 생략하면 해당 학교 전체 학년·반이 한 번에 나옴(2026-07-12 실사 확인).

주의: 원천에 완전 중복 행이 존재(§원천 필드 특성 참고). 유니크 인덱스 upsert로 자연 dedup됨.
주의: 공휴일에도 행이 채워지며 subject에 공휴일명이 들어옴 — 여기서는 원문 그대로 적재하고,
      화면 표시 시점에 academic_schedules와 대조해서 걸러낼 것(ETL 책임 아님).

사용 예:
    python fetch_timetables.py 2026 1 20260713 20260717          # DB의 전체 학교
    python fetch_timetables.py 2026 1 20260713 20260717 B10      # 서울만
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, neis_get, now_iso, load_config, log_etl_error

ENDPOINT_BY_KIND = {
    "초등학교": "elsTimetable",
    "중학교": "misTimetable",
    "고등학교": "hisTimetable",
}


def upsert_timetable(conn, school_id, ay, sem, row):
    conn.execute(
        """
        INSERT INTO timetables (
            school_id, school_year, semester, day_night, track_name,
            department_name, classroom_name, class_date, grade, class_name,
            period, subject, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (school_id, school_year, semester, grade, class_date, period,
                     COALESCE(class_name, ''), COALESCE(classroom_name, ''))
        DO UPDATE SET subject=excluded.subject, last_synced_at=excluded.last_synced_at
        """,
        (
            school_id,
            ay,
            sem,
            row.get("DGHT_CRSE_SC_NM"),
            row.get("ORD_SC_NM"),
            row.get("DDDEP_NM"),
            row.get("CLRM_NM"),
            row["ALL_TI_YMD"],
            row["GRADE"],
            row["CLASS_NM"],
            row["PERIO"],
            row.get("ITRT_CNTNT") or "",
            now_iso(),
        ),
    )


def main(ay, sem, from_ymd, to_ymd, office_codes=None):
    config = load_config()
    key = config["neis_api_key"]
    conn = get_db()

    query = "SELECT id, office_code, school_code, name, school_kind FROM schools"
    params = []
    if office_codes:
        placeholders = ",".join("?" * len(office_codes))
        query += f" WHERE office_code IN ({placeholders})"
        params = office_codes
    schools = conn.execute(query, params).fetchall()

    fetched, skipped = 0, 0
    for school in schools:
        endpoint = ENDPOINT_BY_KIND.get(school["school_kind"])
        if endpoint is None:
            print(f"  [스킵] {school['name']}: 미지원 학교급({school['school_kind']})")
            skipped += 1
            continue

        try:
            rows = neis_get(
                endpoint,
                key,
                ATPT_OFCDC_SC_CODE=school["office_code"],
                SD_SCHUL_CODE=school["school_code"],
                AY=ay,
                SEM=sem,
                TI_FROM_YMD=from_ymd,
                TI_TO_YMD=to_ymd,
                pSize=1000,
            )
        except RuntimeError as e:
            print(f"  [스킵] {school['name']}: {e}")
            log_etl_error(conn, "fetch_timetables", e, target_school_id=school["id"])
            skipped += 1
            continue

        for row in rows:
            upsert_timetable(conn, school["id"], ay, sem, row)
        conn.commit()
        fetched += len(rows)
        print(f"  {school['name']} ({endpoint}): {len(rows)}건")

    print(f"완료: {fetched}건 적재, {skipped}개 학교 스킵")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("사용법: python fetch_timetables.py <학년도> <학기> <시작YYYYMMDD> <종료YYYYMMDD> [교육청코드...]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:] or None)
