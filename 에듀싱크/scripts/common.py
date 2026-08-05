import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "eduthink_config.json"
DB_PATH = ROOT_DIR / "eduthink.db"

NEIS_BASE = "https://open.neis.go.kr/hub"
KINDER_BASE = "https://e-childschoolinfo.moe.go.kr/api/notice"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def neis_get(endpoint, key, _retries=4, _backoff=1.5, **params):
    """NEIS Open API 호출. head[1].RESULT.CODE가 INFO-000이 아니면 예외.
    네트워크 오류(연결 리셋·타임아웃 등)는 지수 백오프로 재시도 — 대량 배치 중 단발성
    연결 끊김(ConnectionResetError 10054)에 배치 전체가 죽지 않도록(§ETL 견고화 2026-07-15)."""
    query = {"KEY": key, "Type": "json", **params}
    last_err = None
    for attempt in range(_retries):
        try:
            resp = requests.get(f"{NEIS_BASE}/{endpoint}", params=query, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.Timeout,
                json.JSONDecodeError) as e:
            last_err = e
            if attempt < _retries - 1:
                time.sleep(_backoff * (2 ** attempt))  # 1.5s, 3s, 6s
                continue
            raise RuntimeError(f"NEIS {endpoint} 네트워크 재시도 실패: {e}")

        if "RESULT" in data:
            code = data["RESULT"]["CODE"]
            if code == "INFO-200":
                return []
            raise RuntimeError(f"NEIS {endpoint} 오류: {data['RESULT']}")

        body = data[endpoint]
        result_code = body[0]["head"][1]["RESULT"]["CODE"]
        if result_code != "INFO-000":
            raise RuntimeError(f"NEIS {endpoint} 오류: {body[0]['head'][1]['RESULT']}")
        return body[1]["row"]
    raise RuntimeError(f"NEIS {endpoint} 실패: {last_err}")


def kinder_get(endpoint, key, sido_code, sgg_code, **params):
    """유치원알리미 OpenAPI 호출. status가 SUCCESS가 아니면 예외."""
    query = {"key": key, "sidoCode": sido_code, "sggCode": sgg_code, **params}
    resp = requests.get(f"{KINDER_BASE}/{endpoint}.do", params=query, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "SUCCESS":
        raise RuntimeError(f"유치원알리미 {endpoint} 오류: {data}")
    return data.get("kinderInfo", [])


_DISH_ALLERGEN_RE = re.compile(r"^(.*?)\s*\(([\d.]+)\)\s*$")


def parse_dishes(dishes_raw):
    """급식 원문("옥수수밥 <br/>근대된장국 (5.6.18)<br/>...")을
    [{"name": "옥수수밥", "allergens": []}, {"name": "근대된장국", "allergens": [5,6,18]}, ...]로 구조화.
    자녀 알레르기 하이라이트(유료, 클라이언트 매칭)용 — 서버는 번호만 다루고 실제 알레르기 정보는 저장 안 함.
    """
    if not dishes_raw:
        return []
    items = []
    for chunk in dishes_raw.split("<br/>"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _DISH_ALLERGEN_RE.match(chunk)
        if m:
            name = m.group(1).strip()
            allergens = [int(n) for n in m.group(2).split(".") if n]
        else:
            name = chunk
            allergens = []
        if name:
            items.append({"name": name, "allergens": allergens})
    return items


def log_etl_error(conn, source, error_message, target_school_id=None):
    """관리자 페이지 모니터링용 실패 로그. NEIS/유치원알리미 호출 실패 시 fetch_*.py에서 호출."""
    conn.execute(
        "INSERT INTO etl_error_log (source, target_school_id, error_message, occurred_at) VALUES (?, ?, ?, ?)",
        (source, target_school_id, str(error_message), now_iso()),
    )
    conn.commit()


def slugify(name, code):
    """검색용 slug. 학교/유치원명은 중복이 흔해 코드를 붙여 유일성 보장."""
    cleaned = "".join(ch for ch in name if ch.isalnum())
    return f"{cleaned}-{code}"
