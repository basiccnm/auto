"""academic_schedules를 시도별 D1 적재용 SQL로 생성 (load_seoul.sql과 같은 방식).
사용법: python gen_schedule_sql.py <출력폴더> [시도명...]
  시도명 생략 시 전 시도 생성. 파일명은 sched_<번호>.sql (한글 경로 문제 회피).
각 파일: DELETE(해당 시도만) + 500행 단위 멀티로우 INSERT.
⚠️ children/payments/users 등 다른 테이블은 절대 건드리지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_db

BATCH = 150  # D1은 구문당 100KB 제한(SQLITE_TOOBIG) — 150행 ≈ 35KB로 안전
COLS = ["school_id", "event_date", "event_name", "event_content",
        "closure_type", "grade_flags", "last_synced_at"]


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(out_dir, only_sidos):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    sidos = [r[0] for r in conn.execute("SELECT DISTINCT sido FROM schools ORDER BY sido")]
    if only_sidos:
        sidos = [s for s in sidos if s in only_sidos]
    manifest = []
    for i, sido in enumerate(sidos, 1):
        rows = conn.execute(
            f"SELECT {', '.join('a.' + c for c in COLS)} FROM academic_schedules a "
            "JOIN schools s ON s.id = a.school_id WHERE s.sido = ?", (sido,)
        ).fetchall()
        s_esc = sido.replace("'", "''")
        parts = [f"DELETE FROM academic_schedules WHERE school_id IN "
                 f"(SELECT id FROM schools WHERE sido='{s_esc}');"]
        for b in range(0, len(rows), BATCH):
            values = ",".join(
                "(" + ",".join(lit(r[c]) for c in COLS) + ")"
                for r in rows[b:b + BATCH]
            )
            parts.append(f"INSERT INTO academic_schedules ({','.join(COLS)}) VALUES {values};")
        fname = f"sched_{i:02d}.sql"
        (out_dir / fname).write_text("\n".join(parts), encoding="utf-8")
        manifest.append(f"{fname}\t{sido}\t{len(rows)}")
        print(f"{fname}  {sido}  {len(rows)}행")
    (out_dir / "manifest.tsv").write_text("\n".join(manifest), encoding="utf-8")
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
