# -*- coding: utf-8 -*-
"""
NEIS(나이스) Open API 호출 래퍼 — 공통모듈 원본.

출처: 에듀싱크 scripts/common.py 의 neis_get/kinder_get (2026-07-15 ETL 견고화까지 반영된 검증본)을
프로젝트 종속 부분(DB, config 경로) 없이 그대로 떼어낸 것.
학원비사이트 fetch_all.py 는 같은 API를 자체 구현(재시도 3회 고정)로 따로 갖고 있음 — 새로 만들 땐 이 파일을 복사할 것.

사용: 프로젝트로 복사한 뒤 KEY는 그 프로젝트의 config에서 주입.
NEIS 키 위치: 에듀싱크 eduthink_config.json / 학원비사이트 fetch_all.py 상단(하드코딩).
"""
import json
import time

import requests

NEIS_BASE = "https://open.neis.go.kr/hub"
KINDER_BASE = "https://e-childschoolinfo.moe.go.kr/api/notice"


def neis_get(endpoint, key, _retries=4, _backoff=1.5, **params):
    """NEIS Open API 호출. head[1].RESULT.CODE가 INFO-000이 아니면 예외.
    네트워크 오류(연결 리셋·타임아웃 등)는 지수 백오프로 재시도 — 대량 배치 중 단발성
    연결 끊김(ConnectionResetError 10054)에 배치 전체가 죽지 않도록."""
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
