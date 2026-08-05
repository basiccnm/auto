"""유치원알리미 schoolMeal+schoolBus+afterSchoolPresent 병합 수집.
kindergartens 테이블에 이미 시딩된 유치원 대상 (sido/sgg 코드는 원본 조회에 필요해 재사용).

사용 예:
    python fetch_disclosures.py 11 11320    # 서울 도봉구
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, kinder_get, now_iso, load_config


def to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main(sido_code, sgg_code):
    config = load_config()
    key = config["kindergarten_api_key"]
    conn = get_db()

    meal_rows = {r["kindercode"]: r for r in kinder_get("schoolMeal", key, sido_code, sgg_code)}
    bus_rows = {r["kindercode"]: r for r in kinder_get("schoolBus", key, sido_code, sgg_code)}
    after_rows = {r["kindercode"]: r for r in kinder_get("afterSchoolPresent", key, sido_code, sgg_code)}

    kinder_codes = set(meal_rows) | set(bus_rows) | set(after_rows)
    kindergartens = {
        r["kinder_code"]: r["id"]
        for r in conn.execute("SELECT id, kinder_code FROM kindergartens").fetchall()
    }

    saved, missing = 0, 0
    for code in kinder_codes:
        kindergarten_id = kindergartens.get(code)
        if kindergarten_id is None:
            # basicInfo2로 아직 시딩 안 된 유치원 — fetch_kindergartens.py 먼저 실행 필요
            missing += 1
            continue

        meal = meal_rows.get(code, {})
        bus = bus_rows.get(code, {})
        after = after_rows.get(code, {})
        disclosure_round = meal.get("pbnttmng") or bus.get("pbnttmng") or after.get("pbnttmng")

        conn.execute(
            """
            INSERT INTO kindergarten_disclosures (
                kindergarten_id, disclosure_round,
                meal_operation_type, meal_vendor_name, meal_total_pupils,
                meal_served_pupils, nutrition_teacher_assigned,
                bus_operating, bus_operating_count, bus_registered_count,
                afterschool_class_count, afterschool_operating_hours, afterschool_pupil_count,
                last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (kindergarten_id, disclosure_round) DO UPDATE SET
                meal_operation_type=excluded.meal_operation_type,
                meal_vendor_name=excluded.meal_vendor_name,
                meal_total_pupils=excluded.meal_total_pupils,
                meal_served_pupils=excluded.meal_served_pupils,
                nutrition_teacher_assigned=excluded.nutrition_teacher_assigned,
                bus_operating=excluded.bus_operating,
                bus_operating_count=excluded.bus_operating_count,
                bus_registered_count=excluded.bus_registered_count,
                afterschool_class_count=excluded.afterschool_class_count,
                afterschool_operating_hours=excluded.afterschool_operating_hours,
                afterschool_pupil_count=excluded.afterschool_pupil_count,
                last_synced_at=excluded.last_synced_at
            """,
            (
                kindergarten_id,
                disclosure_round,
                meal.get("mlsr_oprn_way_tp_cd"),
                meal.get("cons_ents_nm"),
                to_int(meal.get("al_kpcnt")),
                to_int(meal.get("mlsr_kpcnt")),
                meal.get("ntrt_tchr_agmt_yn"),
                bus.get("vhcl_oprn_yn"),
                to_int(bus.get("opra_vhcnt")),
                to_int(bus.get("dclr_vhcnt")),
                to_int(after.get("pm_rrgn_clcnt")),
                after.get("oper_time"),
                to_int(after.get("pm_rrgn_ptcn_kpcnt")),
                now_iso(),
            ),
        )
        saved += 1

    conn.commit()
    print(f"완료: {saved}건 적재, {missing}건 스킵(기관정보 미시딩 - fetch_kindergartens.py 먼저 실행)")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python fetch_disclosures.py <시도코드> <시군구코드>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
