"""
카카오 로컬 API로 주소 -> 좌표 배치 변환.
사용법: KAKAO_REST_KEY 환경변수 또는 아래 상수에 REST API 키를 넣고 실행.
  python scripts/geocode_batch.py academies
  python scripts/geocode_batch.py dojos
  python scripts/geocode_batch.py both
"""
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY", "")  # REST API 키 필요 (JS 키와 다름)
GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
DB_PATH = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\academies.db"
SLEEP_SEC = 0.08  # 카카오 로컬 API 기본 쿼터 여유있게: 초당 약 12건


def geocode(address: str):
    if not address or not address.strip():
        return None
    url = f"{GEOCODE_URL}?query={urllib.parse.quote(address)}"
    req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for '{address}': {e.read().decode('utf-8', 'ignore')}")
        return None
    docs = data.get("documents", [])
    if not docs:
        return None
    d = docs[0]
    return float(d["y"]), float(d["x"])  # 위도(lat), 경도(lng)


def run(table, addr_col_primary, addr_col_fallback=None, sido_list=None):
    if not KAKAO_REST_KEY:
        print("KAKAO_REST_KEY 환경변수가 설정되지 않았습니다. 실행 중단.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    where = ["lat IS NULL"]
    params = []
    if sido_list:
        placeholders = ",".join("?" * len(sido_list))
        where.append(f"sido IN ({placeholders})")
        params.extend(sido_list)

    rows = conn.execute(
        f"SELECT id, {addr_col_primary}"
        + (f", {addr_col_fallback}" if addr_col_fallback else "")
        + f" FROM {table} WHERE " + " AND ".join(where),
        params,
    ).fetchall()
    print(f"{table}: {len(rows)}건 지오코딩 대상")

    ok, fail = 0, 0
    now = datetime.now(timezone.utc).isoformat()
    for i, row in enumerate(rows):
        row_id = row[0]
        addr = row[1] or (row[2] if addr_col_fallback else None)
        result = geocode(addr)
        if result:
            lat, lng = result
            conn.execute(
                f"UPDATE {table} SET lat=?, lng=?, geocoded_at=? WHERE id=?",
                (lat, lng, now, row_id),
            )
            ok += 1
        else:
            fail += 1

        if (i + 1) % 200 == 0:
            conn.commit()
            print(f"  {i+1}/{len(rows)} (ok={ok} fail={fail})")

        time.sleep(SLEEP_SEC)

    conn.commit()
    conn.close()
    print(f"{table} 완료: ok={ok} fail={fail}")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    sido_list = sys.argv[2:] or None
    if target in ("academies", "both"):
        run("academies", "address_road", "address_detail", sido_list)
    if target in ("dojos", "both"):
        run("dojos", "address_road", "address_lot", sido_list)


if __name__ == "__main__":
    main()
