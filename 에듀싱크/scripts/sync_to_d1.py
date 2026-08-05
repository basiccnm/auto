"""로컬 eduthink.db 전체를 D1 반영용 SQL 파일로 덤프.
사용법: python sync_to_d1.py d1_sync.sql
그 다음: npx wrangler d1 execute eduthink-db --remote --file=d1_sync.sql (workers/site-renderer 안에서)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_db, ROOT_DIR

# schools는 children/meals/timetables/... 가 FK로 참조하므로 DELETE 하면 FK 위반.
# → schools는 upsert(id 유지)로 갱신하고, 나머지 데이터 테이블만 DELETE+INSERT.
UPSERT_TABLES = ["schools"]
WIPE_TABLES = [
    "meals", "timetables", "academic_schedules",
    "kindergartens", "kindergarten_disclosures",
    "school_details",
    "etl_error_log", "etl_runs",
]
# 주의: children/banners/admin_edit_log/timetable_overrides/info_reports는 여기 넣지 말 것 — 그 테이블들은 로컬이 아니라
# site-renderer 워커가 D1에 직접 쓰는 데이터라, 이 스크립트로 밀어넣으면(로컬은 비어있음)
# D1에 실제 등록된 자녀·배너·수정이력이 통째로 삭제된다.
#
# 【블록1 신규 테이블 — 절대 추가 금지 (2026-07-19)】
#   identifiers · records · activity_schedules · app_state
#   + 기존 personal_schedule · personal_events · schedule_settings · users · free_trials · payments
# 전부 워커가 D1에 직접 쓰는 사용자 데이터다. 여기 넣으면 **자녀 실명·업로드 기록·이용권 만료일이
# 통째로 삭제**되고 R2의 원본 이미지는 고아가 된다. 복구 불가.
# 이 스크립트는 화이트리스트 방식이라 목록에 없으면 안전하다 — 목록을 늘릴 때 이 경고를 먼저 볼 것.


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def main(out_path):
    conn = get_db()
    tables = UPSERT_TABLES + WIPE_TABLES
    all_rows = {t: conn.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
    conn.close()

    out = []

    # 1) schools: upsert(office_code, school_code 충돌 시 UPDATE) — id 유지 → FK 무결.
    for table in UPSERT_TABLES:
        rows = all_rows[table]
        if not rows:
            continue
        columns = list(rows[0].keys())
        col_list = ", ".join(columns)
        update_cols = [c for c in columns if c not in ("id", "office_code", "school_code")]
        set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
        for row in rows:
            values = ", ".join(sql_literal(row[c]) for c in columns)
            out.append(
                f"INSERT INTO {table} ({col_list}) VALUES ({values}) "
                f"ON CONFLICT(office_code, school_code) DO UPDATE SET {set_clause};"
            )

    # 2) 데이터 테이블: DELETE 후 재삽입(자식 테이블이라 안전).
    for table in reversed(WIPE_TABLES):
        if all_rows[table]:
            out.append(f"DELETE FROM {table};")
    for table in WIPE_TABLES:
        rows = all_rows[table]
        if not rows:
            continue
        columns = rows[0].keys()
        col_list = ", ".join(columns)
        for row in rows:
            values = ", ".join(sql_literal(row[c]) for c in columns)
            out.append(f"INSERT INTO {table} ({col_list}) VALUES ({values});")

    Path(out_path).write_text("\n".join(out), encoding="utf-8")
    print(f"{len(out)}줄 작성: {out_path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(ROOT_DIR / "d1_sync.sql")
    main(target)
