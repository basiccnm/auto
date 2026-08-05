"""fee_raw를 고친 parse_fee로 재파싱해서 academies.fee_parsed / has_fee_data 갱신.
그 다음 sync_fees_to_d1.py로 remote D1에 반영한다."""
import json
import sqlite3
import sys

sys.path.insert(0, "scripts")
from common import parse_fee

DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, fee_raw FROM academies").fetchall()
    changed = 0
    has = 0
    for id_, fee_raw in rows:
        parsed = parse_fee(fee_raw)
        fee_parsed = json.dumps(parsed, ensure_ascii=False) if parsed else None
        has_fee = 1 if parsed else 0
        if has_fee:
            has += 1
        conn.execute(
            "UPDATE academies SET fee_parsed = ?, has_fee_data = ? WHERE id = ?",
            (fee_parsed, has_fee, id_),
        )
        changed += 1
    conn.commit()
    print(f"재파싱 완료: {changed}행 갱신, has_fee_data=1 {has}행")


if __name__ == "__main__":
    main()
