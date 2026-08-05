import sqlite3
import sys

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\d1_seed.sql"


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def dump_table(conn, table, sido_list, out):
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    placeholders = ",".join("?" * len(sido_list))
    rows = conn.execute(
        f"SELECT {','.join(cols)} FROM {table} WHERE sido IN ({placeholders})", sido_list
    ).fetchall()

    col_list = ",".join(cols)
    BATCH = 20
    for i in range(0, len(rows), BATCH):
        chunk = rows[i : i + BATCH]
        values_sql = ",\n".join(
            "(" + ",".join(sql_val(v) for v in row) + ")" for row in chunk
        )
        out.write(f"INSERT INTO {table} ({col_list}) VALUES\n{values_sql};\n")
    return len(rows)


def main():
    sido_list = sys.argv[1:] or ["서울", "경기", "인천"]
    conn = sqlite3.connect(DB_PATH)
    with open(OUT, "w", encoding="utf-8") as out:
        n_a = dump_table(conn, "academies", sido_list, out)
        n_d = dump_table(conn, "dojos", sido_list, out)
    print(f"wrote {n_a} academies + {n_d} dojos to {OUT}")


if __name__ == "__main__":
    main()
