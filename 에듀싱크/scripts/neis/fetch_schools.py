"""NEIS schoolInfo로 학교 기본정보 시딩. office_code 단위로 페이지네이션 전수 수집.

사용 예:
    python fetch_schools.py B10          # 서울 전체 학교
    python fetch_schools.py B10 J10      # 서울 + 경기
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_db, neis_get, now_iso, slugify, load_config, log_etl_error

PAGE_SIZE = 1000


def fetch_office_schools(key, office_code):
    schools = []
    page = 1
    while True:
        rows = neis_get(
            "schoolInfo",
            key,
            ATPT_OFCDC_SC_CODE=office_code,
            pIndex=page,
            pSize=PAGE_SIZE,
        )
        if not rows:
            break
        schools.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return schools


def upsert_school(conn, row):
    conn.execute(
        """
        INSERT INTO schools (
            office_code, office_name, school_code, name, school_kind, sido,
            jurisdiction_office, address_road, address_detail, phone, homepage,
            founded_ymd, est_type, coedu, slug, last_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (office_code, school_code) DO UPDATE SET
            office_name=excluded.office_name, name=excluded.name,
            school_kind=excluded.school_kind, sido=excluded.sido,
            jurisdiction_office=excluded.jurisdiction_office,
            address_road=excluded.address_road, address_detail=excluded.address_detail,
            phone=excluded.phone, homepage=excluded.homepage,
            founded_ymd=excluded.founded_ymd, est_type=excluded.est_type, coedu=excluded.coedu,
            last_synced_at=excluded.last_synced_at
        """,
        (
            row["ATPT_OFCDC_SC_CODE"],
            row["ATPT_OFCDC_SC_NM"],
            row["SD_SCHUL_CODE"],
            row["SCHUL_NM"],
            row["SCHUL_KND_SC_NM"],
            row["LCTN_SC_NM"],
            row.get("JU_ORG_NM"),
            row.get("ORG_RDNMA"),
            row.get("ORG_RDNDA"),
            row.get("ORG_TELNO"),
            row.get("HMPG_ADRES"),
            row.get("FOND_YMD"),
            row.get("FOND_SC_NM"),
            row.get("COEDU_SC_NM"),
            slugify(row["SCHUL_NM"], row["SD_SCHUL_CODE"]),
            now_iso(),
        ),
    )


def main(office_codes):
    config = load_config()
    key = config["neis_api_key"]
    conn = get_db()

    # 관리자 페이지 진행률 표시용(§관리자페이지 지시서 1번). 교육청 단위를 "완료 단계"로 셈 —
    # 학교 단위 진행률이 아니라 다소 거칠지만, 오래 도는 전국 배치의 대략적 진행 상황 파악엔 충분.
    run_id = conn.execute(
        "INSERT INTO etl_runs (job_name, total, completed, status, started_at) VALUES (?, ?, 0, 'running', ?)",
        ("fetch_schools", len(office_codes), now_iso()),
    ).lastrowid
    conn.commit()

    total = 0
    for i, office_code in enumerate(office_codes, start=1):
        try:
            rows = fetch_office_schools(key, office_code)
        except RuntimeError as e:
            print(f"[{office_code}] 실패: {e}")
            log_etl_error(conn, "fetch_schools", e)
            continue

        saved = 0
        for row in rows:
            # 학교급(SCHUL_KND_SC_NM)이 비어있는 행은 초·중·고 대상 서비스에 무의미(특수/기타·폐교 등) → 건너뜀.
            if not (row.get("SCHUL_KND_SC_NM") or "").strip():
                continue
            upsert_school(conn, row)
            saved += 1
        conn.commit()
        print(f"[{office_code}] {saved}개 학교 적재(원본 {len(rows)})")
        total += saved

        conn.execute("UPDATE etl_runs SET completed = ? WHERE id = ?", (i, run_id))
        conn.commit()

    conn.execute(
        "UPDATE etl_runs SET status = 'done', finished_at = ? WHERE id = ?", (now_iso(), run_id)
    )
    conn.commit()

    print(f"완료: 총 {total}개 학교")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python fetch_schools.py <교육청코드> [교육청코드...]")
        print("예: python fetch_schools.py B10 J10")
        sys.exit(1)
    main(sys.argv[1:])
