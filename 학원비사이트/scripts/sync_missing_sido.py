"""전국 확장: 로컬 DB에는 이미 있지만 원격 D1에는 없는 시도(서울/경기/인천 외 14개)를 INSERT.
진행률을 progress.json에 기록해 백그라운드 실행 중에도 확인 가능하게 한다."""
import json
import sqlite3
import time

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT_DIR = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api"
PROGRESS_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\scripts\sync_progress.json"
EXISTING_SIDO = ("서울", "경기", "인천")
MAX_STMT_BYTES = 80_000  # D1 statement-too-long(SQLITE_TOOBIG) 방지 — 실측상 286KB는 실패했음


def sql_val(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def write_progress(**kw):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), **kw}, f, ensure_ascii=False, indent=2)


def gen_inserts(conn, table, cols):
    placeholders = ",".join("?" * len(EXISTING_SIDO))
    rows = conn.execute(
        f"SELECT {','.join(cols)} FROM {table} WHERE sido NOT IN ({placeholders})", EXISTING_SIDO
    ).fetchall()
    return rows


def write_batched(f, table, cols, rows):
    """행 크기가 들쭉날쭉해도(수강료 JSON 등) 문장 하나가 MAX_STMT_BYTES를 넘지 않게 누적 flush."""
    col_list = ",".join(cols)
    prefix = f"INSERT INTO {table} ({col_list}) VALUES "
    buf = []
    buf_bytes = len(prefix.encode("utf-8"))
    written = 0
    for row in rows:
        tup = "(" + ",".join(sql_val(v) for v in row) + ")"
        tup_bytes = len(tup.encode("utf-8"))
        if buf and buf_bytes + tup_bytes + 1 > MAX_STMT_BYTES:
            f.write(prefix + ",".join(buf) + ";\n")
            written += len(buf)
            buf = []
            buf_bytes = len(prefix.encode("utf-8"))
        buf.append(tup)
        buf_bytes += tup_bytes + 1
    if buf:
        f.write(prefix + ",".join(buf) + ";\n")
        written += len(buf)
    return written


def main():
    conn = sqlite3.connect(DB_PATH)

    a_cols = [r[1] for r in conn.execute("PRAGMA table_info(academies)") if r[1] != "id"]
    d_cols = [r[1] for r in conn.execute("PRAGMA table_info(dojos)") if r[1] != "id"]

    write_progress(stage="counting")
    a_rows = gen_inserts(conn, "academies", a_cols)
    d_rows = gen_inserts(conn, "dojos", d_cols)
    total = len(a_rows) + len(d_rows)
    write_progress(stage="writing_sql", academies_total=len(a_rows), dojos_total=len(d_rows), total=total, written=0)

    with open(f"{OUT_DIR}\\insert_academies_national.sql", "w", encoding="utf-8") as f:
        a_written = write_batched(f, "academies", a_cols, a_rows)

    with open(f"{OUT_DIR}\\insert_dojos_national.sql", "w", encoding="utf-8") as f:
        d_written = write_batched(f, "dojos", d_cols, d_rows)

    write_progress(stage="sql_ready", academies_total=len(a_rows), dojos_total=len(d_rows), total=total, written=a_written + d_written)
    print(f"academies INSERT {len(a_rows)}건, dojos INSERT {len(d_rows)}건 -> SQL 파일 생성 완료 (문장당 최대 {MAX_STMT_BYTES}바이트)")


if __name__ == "__main__":
    main()
