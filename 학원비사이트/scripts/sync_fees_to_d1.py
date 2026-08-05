"""재파싱된 fee_parsed를 remote D1에 반영. has_fee_data=1인 행만(fee_parsed 있는 행)."""
import sqlite3

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\fee_sync.sql"


def sql_val(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, fee_parsed FROM academies WHERE has_fee_data = 1"
    ).fetchall()
    with open(OUT, "w", encoding="utf-8") as out:
        for id_, fee_parsed in rows:
            out.write(
                f"UPDATE academies SET fee_parsed={sql_val(fee_parsed)} WHERE id={id_};\n"
            )
    print(f"{len(rows)}개 UPDATE 생성 -> {OUT}")


if __name__ == "__main__":
    main()
