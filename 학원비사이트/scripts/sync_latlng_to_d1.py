import sqlite3
import sys

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\latlng_sync.sql"


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main():
    sido_list = sys.argv[1:] or ["서울", "경기", "인천"]
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(sido_list))

    with open(OUT, "w", encoding="utf-8") as out:
        for table in ("academies", "dojos"):
            rows = conn.execute(
                f"SELECT id, lat, lng FROM {table} WHERE sido IN ({placeholders}) AND lat IS NOT NULL",
                sido_list,
            ).fetchall()
            for i in range(0, len(rows), 50):
                chunk = rows[i : i + 50]
                stmts = "\n".join(
                    f"UPDATE {table} SET lat={sql_val(lat)}, lng={sql_val(lng)} WHERE id={id_};"
                    for id_, lat, lng in chunk
                )
                out.write(stmts + "\n")
            print(f"{table}: {len(rows)} rows queued")


if __name__ == "__main__":
    main()
