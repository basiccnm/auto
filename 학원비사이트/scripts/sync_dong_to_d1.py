import sqlite3
import sys

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\dong_sync.sql"


def sql_val(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def main():
    sido_list = sys.argv[1:] or ["서울", "경기", "인천"]
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(sido_list))

    with open(OUT, "w", encoding="utf-8") as out:
        for table in ("academies", "dojos"):
            # dong IS NOT NULL 조건을 빼서, 오탐이라 NULL로 바뀐 값도 D1에 반영되게 함
            rows = conn.execute(
                f"SELECT id, dong FROM {table} WHERE sido IN ({placeholders})",
                sido_list,
            ).fetchall()
            for i in range(0, len(rows), 50):
                chunk = rows[i : i + 50]
                stmts = "\n".join(f"UPDATE {table} SET dong={sql_val(dong)} WHERE id={id_};" for id_, dong in chunk)
                out.write(stmts + "\n")
            print(f"{table}: {len(rows)} rows queued")


if __name__ == "__main__":
    main()
