# -*- coding: utf-8 -*-
"""네이버쇼핑 검색 인기순 위젯 데이터 갱신 (Blogspot 전용).

방침 (2026-07-09):
- 라벨은 "판매순위"가 아니라 "검색 인기순" (API가 실제 판매량 정렬을 지원하지 않음)
- 실시간 아님 — 하루 1회 배치로 갱신하는 정적 JSON 방식
- 위젯 항목은 클릭해도 쇼핑몰로 연결하지 않음 (순수 정보성 표시)
- 사이드바 가젯이 현재 글의 라벨에 따라 해당 키워드 순위를 자동 표시

실행: python naver_widget.py  (또는 웹 GUI/스케줄러에서 호출)
결과: GitHub images/widget_ranking.json 업로드
"""

import io
import re
import sys
import json
import time
import datetime

import requests

from manager import load_github_config, upload_bytes_to_github

# 위젯 항목 정의: (표시 이름, 매칭에 필요한 라벨들, 네이버쇼핑 검색어)
# - 글의 라벨이 match를 전부 포함하면 해당 항목 표시
# - 여러 개 맞으면 match 개수가 많은(더 구체적인) 것이 우선, 같으면 위쪽이 우선
# - 예: 유산균+여성건강 글 -> "질건강 유산균" 순위 (그냥 "유산균"이 아니라)
WIDGET_ENTRIES = [
    # ── 세부 조합 (구체적일수록 위에) ──
    ("갱년기 유산균",        ["유산균", "갱년기"],     "갱년기 유산균"),
    ("질건강 유산균",        ["유산균", "여성건강"],   "질건강 유산균"),
    ("어린이 유산균",        ["유산균", "키즈"],       "어린이 유산균"),
    ("청소년 유산균",        ["유산균", "청소년"],     "청소년 유산균"),
    ("성인 유산균",          ["유산균", "성인"],       "성인 유산균"),
    ("시니어 유산균",        ["유산균", "시니어"],     "시니어 유산균"),
    ("임산부 유산균",        ["유산균", "임산부"],     "임산부 유산균"),
    ("다이어트 유산균",      ["유산균", "다이어트"],   "다이어트 유산균"),
    ("남성 유산균",          ["유산균", "남성건강"],   "남성 유산균"),
    ("면역 유산균",          ["유산균", "특수목적"],   "면역 유산균"),
    ("어린이 츄어블 오메가3", ["오메가3", "어린이"],    "어린이 츄어블 오메가3"),
    ("청소년 오메가3",       ["오메가3", "청소년"],    "청소년 오메가3"),
    ("임산부 오메가3",       ["오메가3", "임산부"],    "임산부 오메가3"),
    ("여성 오메가3",         ["오메가3", "여성건강"],  "여성 오메가3"),
    ("오메가3 밀크씨슬",     ["오메가3", "남성건강"],  "오메가3 밀크씨슬"),
    ("시니어 오메가3",       ["오메가3", "시니어"],    "시니어 오메가3"),
    ("다이어트 오메가3",     ["오메가3", "다이어트"],  "다이어트 오메가3"),
    ("루테인 오메가3",       ["오메가3", "눈건강"],    "루테인 오메가3"),
    # ── 성분 단독 ──
    ("유산균",               ["유산균"],               "유산균"),
    ("오메가3",              ["오메가3"],              "오메가3"),
    ("루테인",               ["루테인"],               "루테인"),
    ("갱년기 영양제",        ["갱년기"],               "갱년기 영양제"),
    ("단백질 보충제",        ["단백질"],               "단백질 보충제"),
    ("마그네슘",             ["마그네슘"],             "마그네슘"),
    # ── 연령·성별 허브 ──
    ("어린이 영양제",        ["영유아·어린이"],        "어린이 영양제"),
    ("청소년 영양제",        ["청소년·수험생"],        "청소년 영양제"),
    ("여성 영양제",          ["우먼 케어"],            "여성 영양제"),
    ("남성 영양제",          ["맨즈 케어"],            "남성 영양제"),
    ("시니어 영양제",        ["시니어 건강"],          "시니어 영양제"),
    ("다이어트 보조제",      ["다이어트·체형"],        "다이어트 보조제"),
    ("종합비타민",           ["면역·기초건강"],        "종합비타민"),
    ("피로회복 영양제",      ["피로·활력"],            "피로회복 영양제"),
]
TOP_N = 5


def _load_naver_config():
    with open("naver_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_ranking(keyword, display=TOP_N):
    """네이버쇼핑 검색 인기순(기본 정렬 sim) 상위 상품을 가져온다."""
    cfg = _load_naver_config()
    res = requests.get(
        "https://openapi.naver.com/v1/search/shop.json",
        params={"query": keyword, "display": display, "sort": "sim"},
        headers={"X-Naver-Client-Id": cfg["client_id"],
                 "X-Naver-Client-Secret": cfg["client_secret"]},
        timeout=15,
    )
    if res.status_code != 200:
        raise RuntimeError(f"네이버쇼핑 API 오류 ({res.status_code}): {res.text[:150]}")
    items = []
    for it in res.json().get("items", []):
        title = re.sub(r"</?b>", "", it.get("title", ""))
        items.append({
            "title": title[:60],
            "lprice": int(it.get("lprice") or 0),
            "brand": it.get("brand") or it.get("maker") or "",
        })
    return items


def update_widget_data(log=print):
    """전체 항목의 순위 데이터를 만들어 GitHub에 업로드한다 (하루 1회 배치용)."""
    data = {
        "updated": datetime.date.today().isoformat(),
        "label": "전날 검색 인기순",  # 실시간으로 오인되지 않게
        "entries": [],
    }
    query_cache = {}
    for name, match, query in WIDGET_ENTRIES:
        try:
            if query not in query_cache:
                query_cache[query] = fetch_ranking(query)
                time.sleep(0.5)  # API 예의상 간격
            data["entries"].append({
                "name": name, "match": match, "items": query_cache[query]})
            log(f"  {name} ({query}): {len(query_cache[query])}개")
        except Exception as e:
            log(f"  {name} 실패: {e}")

    payload = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
    github_cfg = load_github_config()
    url = upload_bytes_to_github(payload, "widget_ranking.json", github_cfg)
    log(f"업로드 완료: {url}")
    return url


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    update_widget_data()
