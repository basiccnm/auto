import json
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from common import OFFICE_CODES, normalize_row

API_KEY = "6c34a70a06154fe2ad786f9eff5fb645"
BASE_URL = "https://open.neis.go.kr/hub/acaInsTiInfo"
PAGE_SIZE = 1000
SLEEP_SEC = 1.5
DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
SCHEMA_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\schema.sql"


def fetch_page(office_code, page_index):
    url = (
        f"{BASE_URL}?KEY={API_KEY}&Type=json&pIndex={page_index}"
        f"&pSize={PAGE_SIZE}&ATPT_OFCDC_SC_CODE={office_code}"
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except urllib.error.URLError as e:
            print(f"  retry {office_code} page {page_index}: {e}")
            time.sleep(3)
    raise RuntimeError(f"failed to fetch {office_code} page {page_index} after retries")


def upsert(conn, rec, now):
    cur = conn.execute(
        "SELECT content_hash FROM academies WHERE office_code = ? AND aca_asnum = ?",
        (rec["office_code"], rec["aca_asnum"]),
    )
    existing = cur.fetchone()
    fee_parsed_json = json.dumps(rec["fee_parsed"], ensure_ascii=False) if rec["fee_parsed"] else None

    if existing is None:
        conn.execute(
            """INSERT INTO academies
            (aca_asnum, office_code, office_name, sido, sigungu, inst_type, name, status,
             closed_at, realm_raw, category_name, category_slug, course_name, course_list_raw,
             fee_raw, fee_parsed, has_fee_data, capacity_total, capacity_hourly,
             address_road, address_detail, zipcode, phone, reg_date, slug, content_hash,
             first_seen_at, last_seen_at, last_changed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec["aca_asnum"], rec["office_code"], rec["office_name"], rec["sido"], rec["sigungu"],
                rec["inst_type"], rec["name"], rec["status"],
                rec["status"] if rec["status"] == "폐원" else None,
                rec["realm_raw"], rec["category_name"], rec["category_slug"], rec["course_name"],
                rec["course_list_raw"], rec["fee_raw"], fee_parsed_json, int(rec["has_fee_data"]),
                rec["capacity_total"], rec["capacity_hourly"], rec["address_road"], rec["address_detail"],
                rec["zipcode"], rec["phone"], rec["reg_date"], rec["slug"], rec["content_hash"],
                now, now, now,
            ),
        )
        return "new"
    elif existing[0] != rec["content_hash"]:
        conn.execute(
            """UPDATE academies SET
                office_name=?, sido=?, sigungu=?, inst_type=?, name=?, status=?,
                closed_at=CASE WHEN ?='폐원' THEN ? ELSE closed_at END,
                realm_raw=?, category_name=?, category_slug=?, course_name=?, course_list_raw=?,
                fee_raw=?, fee_parsed=?, has_fee_data=?, capacity_total=?, capacity_hourly=?,
                address_road=?, address_detail=?, zipcode=?, phone=?, reg_date=?, slug=?,
                content_hash=?, last_seen_at=?, last_changed_at=?
            WHERE office_code=? AND aca_asnum=?""",
            (
                rec["office_name"], rec["sido"], rec["sigungu"], rec["inst_type"], rec["name"], rec["status"],
                rec["status"], now,
                rec["realm_raw"], rec["category_name"], rec["category_slug"], rec["course_name"],
                rec["course_list_raw"], rec["fee_raw"], fee_parsed_json, int(rec["has_fee_data"]),
                rec["capacity_total"], rec["capacity_hourly"], rec["address_road"], rec["address_detail"],
                rec["zipcode"], rec["phone"], rec["reg_date"], rec["slug"],
                rec["content_hash"], now, now,
                rec["office_code"], rec["aca_asnum"],
            ),
        )
        return "changed"
    else:
        conn.execute(
            "UPDATE academies SET last_seen_at=? WHERE office_code=? AND aca_asnum=?",
            (now, rec["office_code"], rec["aca_asnum"]),
        )
        return "unchanged"


def main():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())

    now = datetime.now(timezone.utc).isoformat()
    counts = {"new": 0, "changed": 0, "unchanged": 0}
    total_rows = 0

    for office_code, sido in OFFICE_CODES.items():
        page = 1
        office_total = None
        while True:
            data = fetch_page(office_code, page)
            arr = data.get("acaInsTiInfo")
            if not arr:
                print(f"{office_code} ({sido}): no data / error -> {data}")
                break
            head = arr[0]["head"]
            office_total = head[0]["list_total_count"]
            rows = arr[1]["row"] if len(arr) > 1 and "row" in arr[1] else []

            for row in rows:
                if not row.get("ACA_ASNUM"):
                    print(f"  skip row without ACA_ASNUM: {row.get('ACA_NM')}")
                    continue
                rec = normalize_row(row, sido)
                status = upsert(conn, rec, now)
                counts[status] += 1
                total_rows += 1

            conn.commit()
            fetched_so_far = (page - 1) * PAGE_SIZE + len(rows)
            print(f"{office_code} ({sido}) page {page}: {len(rows)} rows ({fetched_so_far}/{office_total})")

            if fetched_so_far >= office_total or not rows:
                break
            page += 1
            time.sleep(SLEEP_SEC)

        time.sleep(SLEEP_SEC)

    conn.close()
    print(f"\nTotal processed: {total_rows}")
    print(f"new={counts['new']} changed={counts['changed']} unchanged={counts['unchanged']}")


if __name__ == "__main__":
    main()
