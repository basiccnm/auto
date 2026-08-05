# 공용 HTTP 헬퍼 (표준 라이브러리만 사용 — Workers 크론 이식 시 의존성 0)
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from .config import HTTP_TIMEOUT, SSL_CTX, USER_AGENT


class FetchError(Exception):
    pass


def fetch_text(url, timeout=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT, context=SSL_CTX) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # URLError/HTTPError/timeout 전부 동일 취급
        raise FetchError(f"{type(e).__name__}: {e}") from e


def fetch_json(url, timeout=None):
    body = fetch_text(url, timeout)
    try:
        return json.loads(body)
    except ValueError as e:
        raise FetchError(f"JSON 파싱 실패: {body[:200]}") from e


def fetch_xml(url, timeout=None):
    body = fetch_text(url, timeout)
    try:
        return ET.fromstring(body)
    except ET.ParseError as e:
        raise FetchError(f"XML 파싱 실패: {body[:200]}") from e
