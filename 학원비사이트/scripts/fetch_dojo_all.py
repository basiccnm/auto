import json
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from dojo_common import normalize_item

SERVICE_KEY = "01d41ee31954bf8a99a618c1c206dd53aff2ce5fe2e53cec92fd3bd371e70dda"
BASE_URL = "https://apis.data.go.kr/1741000/martial_arts_dojo/info"
PAGE_SIZE = 100
SLEEP_SEC = 1.5
DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
SCHEMA_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\schema.sql"


def fetch_page(page_index):
    url = (
        f"{BASE_URL}?serviceKey={SERVICE_KEY}&pageNo={page_index}"
        f"&numOfRows={PAGE_SIZE}&resultType=json"
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  retry page {page_index}: {e}")
            time.sleep(3)
    raise RuntimeError(f"failed to fetch page {page_index} after retries")


def upsert(conn, rec, now):
    cur = conn.execute(
        "SELECT content_hash FROM dojos WHERE opn_atmy_grp_cd = ? AND mng_no = ?",
        (rec["opn_atmy_grp_cd"], rec["mng_no"]),
    )
    existing = cur.fetchone()

    if existing is None:
        conn.execute(
            """INSERT INTO dojos
            (mng_no, opn_atmy_grp_cd, name, sport_name, sido, sigungu, status_code, status_name,
             detail_status_name, is_open, license_ymd, closed_ymd, address_road, address_lot,
             zipcode, phone, leader_count, member_capacity, category_name, category_slug,
             slug, content_hash, first_seen_at, last_seen_at, last_changed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec["mng_no"], rec["opn_atmy_grp_cd"], rec["name"], rec["sport_name"],
                rec["sido"], rec["sigungu"], rec["status_code"], rec["status_name"],
                rec["detail_status_name"], int(rec["is_open"]), rec["license_ymd"], rec["closed_ymd"],
                rec["address_road"], rec["address_lot"], rec["zipcode"], rec["phone"],
                rec["leader_count"], rec["member_capacity"], rec["category_name"], rec["category_slug"],
                rec["slug"], rec["content_hash"], now, now, now,
            ),
        )
        return "new"
    elif existing[0] != rec["content_hash"]:
        conn.execute(
            """UPDATE dojos SET
                name=?, sport_name=?, sido=?, sigungu=?, status_code=?, status_name=?,
                detail_status_name=?, is_open=?, license_ymd=?, closed_ymd=?, address_road=?,
                address_lot=?, zipcode=?, phone=?, leader_count=?, member_capacity=?,
                category_name=?, category_slug=?, slug=?, content_hash=?, last_seen_at=?, last_changed_at=?
            WHERE opn_atmy_grp_cd=? AND mng_no=?""",
            (
                rec["name"], rec["sport_name"], rec["sido"], rec["sigungu"], rec["status_code"],
                rec["status_name"], rec["detail_status_name"], int(rec["is_open"]), rec["license_ymd"],
                rec["closed_ymd"], rec["address_road"], rec["address_lot"], rec["zipcode"], rec["phone"],
                rec["leader_count"], rec["member_capacity"], rec["category_name"], rec["category_slug"],
                rec["slug"], rec["content_hash"], now, now,
                rec["opn_atmy_grp_cd"], rec["mng_no"],
            ),
        )
        return "changed"
    else:
        conn.execute(
            "UPDATE dojos SET last_seen_at=? WHERE opn_atmy_grp_cd=? AND mng_no=?",
            (now, rec["opn_atmy_grp_cd"], rec["mng_no"]),
        )
        return "unchanged"


def main():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())

    now = datetime.now(timezone.utc).isoformat()
    counts = {"new": 0, "changed": 0, "unchanged": 0}
    skipped_no_addr = 0
    total_rows = 0

    page = 1
    total_count = None
    while True:
        data = fetch_page(page)
        body = data.get("response", {}).get("body", {})
        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "0":
            print(f"page {page}: API error -> {header}")
            break
        total_count = body.get("totalCount")
        items = body.get("items", {}).get("item", []) or []

        for item in items:
            rec = normalize_item(item)
            if rec is None:
                skipped_no_addr += 1
                continue
            status = upsert(conn, rec, now)
            counts[status] += 1
            total_rows += 1

        conn.commit()
        fetched_so_far = (page - 1) * PAGE_SIZE + len(items)
        print(f"page {page}: {len(items)} rows ({fetched_so_far}/{total_count})")

        if fetched_so_far >= total_count or not items:
            break
        page += 1
        time.sleep(SLEEP_SEC)

    conn.close()
    print(f"\nTotal processed: {total_rows} (skipped no-address: {skipped_no_addr})")
    print(f"new={counts['new']} changed={counts['changed']} unchanged={counts['unchanged']}")


if __name__ == "__main__":
    main()
