"""NEIS mealServiceDietInfo로 일자별 급식 수집. schools 테이블에 이미 시딩된 학교 대상.

사용 예:
    python fetch_meals.py 20260713 20260731          # DB의 전체 학교
    python fetch_meals.py 20260713 20260731 B10       # 서울만
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, neis_get, now_iso, load_config, parse_dishes, log_etl_error


def upsert_meal(conn, school_id, row):
    dishes_raw = row.get("DDISH_NM") or ""
    conn.execute(
        """
        INSERT INTO meals (
            school_id, meal_date, meal_type_code, meal_type_name,
            dishes, dishes_parsed, calorie_info, origin_info, nutrition_info, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (school_id, meal_date, meal_type_code) DO UPDATE SET
            dishes=excluded.dishes, dishes_parsed=excluded.dishes_parsed,
            calorie_info=excluded.calorie_info,
            origin_info=excluded.origin_info, nutrition_info=excluded.nutrition_info,
            last_synced_at=excluded.last_synced_at
        """,
        (
            school_id,
            row["MLSV_YMD"],
            row["MMEAL_SC_CODE"],
            row["MMEAL_SC_NM"],
            dishes_raw,
            json.dumps(parse_dishes(dishes_raw), ensure_ascii=False),
            row.get("CAL_INFO"),
            row.get("ORPLC_INFO"),
            row.get("NTR_INFO"),
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
                "mealServiceDietInfo",
                key,
                ATPT_OFCDC_SC_CODE=school["office_code"],
                SD_SCHUL_CODE=school["school_code"],
                MLSV_FROM_YMD=from_ymd,
                MLSV_TO_YMD=to_ymd,
                pSize=1000,
            )
        except RuntimeError as e:
            print(f"  [스킵] {school['name']}: {e}")
            log_etl_error(conn, "fetch_meals", e, target_school_id=school["id"])
            skipped += 1
            continue

        for row in rows:
            upsert_meal(conn, school["id"], row)
        conn.commit()
        fetched += len(rows)
        print(f"  {school['name']}: {len(rows)}건")

    print(f"완료: {fetched}건 적재, {skipped}개 학교 스킵")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python fetch_meals.py <시작YYYYMMDD> <종료YYYYMMDD> [교육청코드...]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
