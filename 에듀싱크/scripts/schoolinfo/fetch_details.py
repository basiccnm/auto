"""학교알리미 OPEN API → school_details. 지역(시도+시군구+학교급) 단위 조회.

2026-07-12 API 실사 + 개발자가이드 코드표로 확정한 매핑:
- 엔드포인트: GET https://www.schoolinfo.go.kr/openApi.do
- 필수: apiKey, apiType, pbanYr, schulKndCode(02초/03중/04고), sidoCode, sggCode (신규키는 sido/sgg 필수)
- apiType=0  : 학교기본정보 목록 → SCHUL_CODE + SCHUL_NM + SCHUL_RDNMA (학교명+주소 매칭용)
- apiType=09 : 학년별·학급별 학생수 → COL_S_SUM(전교생), COL_C_SUM(학급수), COL_S1..8(학년별 학생), COL_C1..8(학년별 학급)
- apiType=22 : 직위별 교원현황 → COL_S(교원 총계, =COL_SM 남+COL_SW 여로 검증)
- apiType=08 : 수업일수·수업시수 → COL_1..8(학년별 수업일수), WEEK_TOT_ITRT_HR_FGR(주당 총 수업시수)

주의: 전교생/학급수는 반드시 apiType=09(전용 dataset). apiType 10(전출입)·34(급식)·43(안전)의 학생수는
      기준일이 달라 값이 다름. COL_x 추측 금지(20/21은 시설유무였음).

⚠️ pbanYr(공시연도)는 반드시 현재 학년도로! 학년도마다 값이 다름
   (숭미초 09: 2024=570/32, 2025=512/29, 2026=487/26). 2026-07-12 최초 연동 때
   실수로 2025로 돌려 작년값이 박혔던 버그 있음. 인자 생략 시 current_school_year()로 자동 계산.

사용 예 (02=초/03=중/04=고):
    python fetch_details.py auto 02 11 11320   # 현재 학년도 자동
    python fetch_details.py 2026 02 11 11320   # 명시
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, now_iso, load_config
import requests

BASE = "https://www.schoolinfo.go.kr/openApi.do"
KIND_NAME = {"02": "초등학교", "03": "중학교", "04": "고등학교"}


def current_school_year():
    """한국 학년도: 3월 시작. 3월 이후면 올해, 1~2월이면 작년. (KST 기준)"""
    kst = datetime.now(timezone.utc) + timedelta(hours=9)
    return kst.year if kst.month >= 3 else kst.year - 1


def api_list(key, api_type, pban_yr, kind, sido, sgg):
    r = requests.get(BASE, params={
        "apiKey": key, "apiType": api_type, "pbanYr": pban_yr,
        "schulKndCode": kind, "sidoCode": sido, "sggCode": sgg}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("resultCode") != "success":
        raise RuntimeError(f"apiType={api_type}: {data.get('resultMsg')}")
    return data.get("list", [])


def norm(s):
    return "".join((s or "").split())


def to_int(v):
    try:
        return int(round(float(str(v).strip())))
    except (TypeError, ValueError):
        return None


MAX_GRADE = {"02": 6, "03": 3, "04": 3}  # 초6 / 중3 / 고3


def build_breakdown(s09, s08, s63, kind):
    """학년별 학생수/학급수(09) + 학년별 수업일수(08) + 학년별 남/여(63)를
    [{grade,students,classes,school_days,male,female}]로.
    apiType09의 COL_S7/S8은 정규학년이 아니라 특수학급 등 → 학교급 최대 학년까지만 노출.
    성별(63): COL_M{g}=남, COL_W{g}=여. 없는 학교는 male/female=None."""
    out = []
    for g in range(1, MAX_GRADE.get(kind, 6) + 1):
        students = to_int((s09 or {}).get(f"COL_S{g}"))
        classes = to_int((s09 or {}).get(f"COL_C{g}"))
        days = to_int((s08 or {}).get(f"COL_{g}"))
        male = to_int((s63 or {}).get(f"COL_M{g}"))
        female = to_int((s63 or {}).get(f"COL_W{g}"))
        if (students or classes):
            out.append({"grade": g, "students": students, "classes": classes,
                        "school_days": days, "male": male, "female": female})
    return out


def main(pban_yr, kind, sido, sgg):
    key = load_config()["schoolinfo_api_key"]
    if not key:
        print("schoolinfo_api_key 미설정"); sys.exit(1)
    conn = get_db()

    neis_rows = conn.execute(
        "SELECT id, name, address_road FROM schools WHERE school_kind = ?", (KIND_NAME[kind],)
    ).fetchall()

    base = api_list(key, 0, pban_yr, kind, sido, sgg)
    enroll = {r["SCHUL_CODE"]: r for r in api_list(key, "09", pban_yr, kind, sido, sgg)}
    teacher = {r["SCHUL_CODE"]: r for r in api_list(key, "22", pban_yr, kind, sido, sgg)}
    days = {r["SCHUL_CODE"]: r for r in api_list(key, "08", pban_yr, kind, sido, sgg)}
    # 방과후(apiType59): 강좌목록 아닌 집계치 → 프로그램수/참여학생수/돌봄운영여부만.
    after = {r["SCHUL_CODE"]: r for r in api_list(key, "59", pban_yr, kind, sido, sgg)}
    # 성별 학생수(apiType63): 학년별 남(COL_M{g})/여(COL_W{g}) → 상세정보 성비.
    gender = {r["SCHUL_CODE"]: r for r in api_list(key, "63", pban_yr, kind, sido, sgg)}

    by_name = {}
    for r in base:
        by_name.setdefault(norm(r.get("SCHUL_NM")), []).append(r)

    saved = 0
    for s in neis_rows:
        cands = by_name.get(norm(s["name"]), [])
        if not cands:
            continue
        match = cands[0]
        if len(cands) > 1 and s["address_road"]:
            match = next((c for c in cands if norm(c.get("SCHUL_RDNMA", ""))[:10] == norm(s["address_road"])[:10]), cands[0])
        code = match["SCHUL_CODE"]

        s09 = enroll.get(code, {})
        s22 = teacher.get(code, {})
        s08 = days.get(code, {})
        s59 = after.get(code, {})
        s63 = gender.get(code, {})

        student_count = to_int(s09.get("COL_S_SUM"))
        male_count = to_int(s63.get("COL_MSUM"))    # 특수학급 포함 총계 → student_count와 합 일치
        female_count = to_int(s63.get("COL_WSUM"))
        class_count = to_int(s09.get("COL_C_SUM"))
        teacher_count = to_int(s22.get("COL_S"))
        grade_days = [to_int(s08.get(f"COL_{g}")) for g in range(1, 9) if to_int(s08.get(f"COL_{g}"))]
        school_days = max(grade_days) if grade_days else None
        week_hours = to_int(s08.get("WEEK_TOT_ITRT_HR_FGR"))
        breakdown = json.dumps(build_breakdown(s09, s08, s63, kind), ensure_ascii=False)

        as_program = to_int(s59.get("SUM_ASL_PGM_FGR"))
        as_student = to_int(s59.get("ASL_PTPT_STDNT_FGR"))
        ecc = (to_int(s59.get("ECC_PM_OPER_CCCLA_FGR")) or 0) + (to_int(s59.get("ECC_DINNR_OPER_CCCLA_FGR")) or 0)
        care_yn = "Y" if ecc > 0 else ("N" if s59 else None)

        conn.execute(
            """
            INSERT INTO school_details (
                school_id, source_school_code, student_count, male_count, female_count,
                class_count, teacher_count,
                school_days, week_class_hours, grade_breakdown,
                afterschool_program_count, afterschool_student_count, care_class_yn,
                disclosure_round, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (school_id) DO UPDATE SET
                source_school_code=excluded.source_school_code,
                student_count=excluded.student_count,
                male_count=excluded.male_count, female_count=excluded.female_count,
                class_count=excluded.class_count,
                teacher_count=excluded.teacher_count, school_days=excluded.school_days,
                week_class_hours=excluded.week_class_hours, grade_breakdown=excluded.grade_breakdown,
                afterschool_program_count=excluded.afterschool_program_count,
                afterschool_student_count=excluded.afterschool_student_count,
                care_class_yn=excluded.care_class_yn,
                disclosure_round=excluded.disclosure_round, last_synced_at=excluded.last_synced_at
            """,
            (s["id"], code, student_count, male_count, female_count, class_count, teacher_count,
             school_days, week_hours, breakdown, as_program, as_student, care_yn,
             str(pban_yr), now_iso()),
        )
        saved += 1
        print(f"  {s['name']}: 전교생 {student_count}/학급 {class_count}/교원 {teacher_count}/방과후 {as_program}개·{as_student}명·돌봄 {care_yn}")

    conn.commit()
    print(f"완료: {saved}개교 (sido={sido}, sgg={sgg}, {KIND_NAME[kind]})")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("사용법: python fetch_details.py <공시년도|auto> <학교급02/03/04> <시도코드> <시군구코드>")
        sys.exit(1)
    pban_yr = current_school_year() if sys.argv[1] == "auto" else sys.argv[1]
    main(pban_yr, sys.argv[2], sys.argv[3], sys.argv[4])
