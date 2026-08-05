import sqlite3

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
OUT_SQL = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\fix_sigungu.sql"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, sido, address_road FROM academies WHERE sigungu = '미상'").fetchall()

    fixed = []
    still_unknown = []
    for id_, sido, addr in rows:
        parts = (addr or "").split()
        recovered = None
        if len(parts) >= 2:
            candidate = parts[1]
            if candidate.endswith(("구", "시", "군")):
                recovered = candidate
        if recovered:
            fixed.append((id_, sido, recovered))
        else:
            still_unknown.append((id_, addr))

    for id_, sido, sigungu in fixed:
        conn.execute("UPDATE academies SET sigungu = ? WHERE id = ?", (sigungu, id_))
    conn.commit()

    with open(OUT_SQL, "w", encoding="utf-8") as f:
        for id_, sido, sigungu in fixed:
            if sido in ("서울", "경기", "인천"):
                f.write(f"UPDATE academies SET sigungu = '{sigungu}' WHERE id = {id_};\n")

    print(f"total 미상: {len(rows)}, fixed: {len(fixed)}, still unknown: {len(still_unknown)}")
    for id_, addr in still_unknown[:10]:
        print(f"  unresolved id={id_}: {addr!r}")


if __name__ == "__main__":
    main()
