# -*- coding: utf-8 -*-
"""네이버 발행 대기열 관리 (2026-07-09 방침 v2).

- 글 세트(제목+본문+태그+이미지 6개)를 등록해 리스트로 쌓아둔다
- 발행 선택 시 "마지막 배정 날짜 + 1일" 규칙으로 하루 1개씩 순차 배정
- 발행 시각: 고정 슬롯(기본 15시) + 매번 무작위 분 오프셋 (±45분)
- 실제 등록은 네이버 자체 "예약 발행" 기능으로 (한 세션에 최대 10개 배치)
"""

import os
import json
import random
import datetime

QUEUE_DIR = "naver_queue"
QUEUE_FILE = os.path.join(QUEUE_DIR, "queue.json")

SLOT_HOUR = 15          # 기본 발행 슬롯 (오후 3시)
SLOT_JITTER_MIN = 45    # 슬롯 기준 ±무작위 분 (매일 고정 시각 회피)
MAX_BATCH = 10          # 한 세션 최대 등록 개수


def _ensure_dir():
    os.makedirs(QUEUE_DIR, exist_ok=True)


def load_queue():
    _ensure_dir()
    if not os.path.exists(QUEUE_FILE):
        return {"posts": [], "last_assigned_date": None}
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(data):
    _ensure_dir()
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_post(title, body_html, tags, image_paths, platform="naver",
             keyword="", blogspot_url=""):
    """글 세트를 대기열에 등록한다. 본문은 파일로 저장하고 메타만 queue.json에 둔다.

    platform: "naver" 또는 "blogspot" — 저장 공간은 공유하되 플랫폼 필드로 구분 (방침 v3)
    keyword: Gems가 준 매칭키워드 (Blogspot 글 연결용)
    blogspot_url: 연결된 방구석 약국 글 URL (없으면 "연결 대기" — 발행 전에 채워야 함)
    """
    _ensure_dir()
    data = load_queue()
    post_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # 마이크로초까지 (같은 초 등록 시 ID 충돌 방지)
    body_file = os.path.join(QUEUE_DIR, f"{post_id}_body.html")
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(body_html)
    entry = {
        "id": post_id,
        "platform": platform,
        "title": title,
        "body_file": body_file,
        "tags": tags,
        "images": list(image_paths),
        "keyword": keyword,
        "blogspot_url": blogspot_url,   # 비어 있으면 연결 대기
        "status": "ready",          # ready -> scheduled
        "scheduled_at": None,       # "2026-07-10 15:23"
        "naver_url": None,
    }
    data["posts"].append(entry)
    save_queue(data)
    return entry


def get_post_body(entry):
    with open(entry["body_file"], "r", encoding="utf-8") as f:
        return f.read()


def assign_schedule_dates(post_ids):
    """선택한 글들에 발행 일시를 배정한다 (마지막 배정 날짜+1일부터 하루 1개씩).

    반환: [(entry, datetime), ...]  — queue.json에도 저장됨
    """
    data = load_queue()
    today = datetime.date.today()

    # 기준일: 실제로 배정돼 있는 글들의 마지막 날짜 (실패/취소로 저장값이 앞서 나간 경우 자가 복구)
    real_dates = [datetime.date.fromisoformat(p["scheduled_at"][:10])
                  for p in data["posts"] if p.get("scheduled_at")]
    if real_dates:
        next_date = max(max(real_dates) + datetime.timedelta(days=1), today)
    else:
        next_date = today

    now = datetime.datetime.now()

    assigned = []
    by_id = {p["id"]: p for p in data["posts"]}
    for pid in post_ids:
        entry = by_id.get(pid)
        if not entry or entry["status"] != "ready":
            continue
        minute_offset = random.randint(-SLOT_JITTER_MIN, SLOT_JITTER_MIN)
        dt = datetime.datetime.combine(next_date, datetime.time(SLOT_HOUR, 0)) \
             + datetime.timedelta(minutes=minute_offset)
        # 배정 시각이 이미 지났거나 30분 이내면 다음날로 (예약발행은 미래 시각이어야 함)
        if dt < now + datetime.timedelta(minutes=30):
            next_date += datetime.timedelta(days=1)
            dt = datetime.datetime.combine(next_date, datetime.time(SLOT_HOUR, 0)) \
                 + datetime.timedelta(minutes=minute_offset)
        entry["scheduled_at"] = dt.strftime("%Y-%m-%d %H:%M")
        assigned.append((entry, dt))
        data["last_assigned_date"] = next_date.isoformat()
        next_date += datetime.timedelta(days=1)

    save_queue(data)
    return assigned


def mark_registered(post_id, naver_url=None):
    """네이버에 예약 등록이 실제로 완료된 글을 표시한다."""
    data = load_queue()
    for p in data["posts"]:
        if p["id"] == post_id:
            p["status"] = "scheduled"
            p["naver_url"] = naver_url
    save_queue(data)


def unassign(post_id):
    """예약 등록 실패 시 배정을 되돌린다 (status는 ready 유지, 날짜만 제거)."""
    data = load_queue()
    for p in data["posts"]:
        if p["id"] == post_id and p["status"] == "ready":
            p["scheduled_at"] = None
    save_queue(data)


def update_post_content(post_id, title=None, tags=None, body_html=None):
    """저장 리스트 글의 내용을 수정한다 (로컬 저장소가 원본 — 네이버 반영은 별도 단계)."""
    data = load_queue()
    for p in data["posts"]:
        if p["id"] == post_id:
            if title is not None:
                p["title"] = title
            if tags is not None:
                p["tags"] = tags
            if body_html is not None:
                with open(p["body_file"], "w", encoding="utf-8") as f:
                    f.write(body_html)
    save_queue(data)


def delete_post(post_id):
    """대기열에서 글을 삭제한다 (본문 파일도 함께 정리).

    주의: '예약됨' 상태 글을 지워도 네이버에 이미 등록된 예약발행은 취소되지 않는다
    (그건 네이버 블로그 관리에서 직접 취소해야 함) — 여기서는 목록 기록만 지운다.
    """
    data = load_queue()
    remain = []
    for p in data["posts"]:
        if p["id"] == post_id:
            try:
                if os.path.exists(p.get("body_file", "")):
                    os.remove(p["body_file"])
            except OSError:
                pass
        else:
            remain.append(p)
    data["posts"] = remain
    save_queue(data)


def sync_published_status(log=print):
    """예약 시각이 지났는데 실제 글 주소를 못 받은 항목을 네이버 RSS로 대조해서 채운다.

    예약 등록 직후에는 글이 아직 비공개라 실제 URL을 못 받는데(2026-07-10 확인된 간극),
    시간이 지나 실제 공개된 뒤에는 RSS에 나타나므로 여기서 뒤늦게 채워준다.
    """
    import re
    import datetime
    import requests

    data = load_queue()
    now = datetime.datetime.now()
    targets = [p for p in data["posts"]
               if p["status"] == "scheduled" and not p.get("naver_url")
               and p.get("scheduled_at")
               and datetime.datetime.strptime(p["scheduled_at"], "%Y-%m-%d %H:%M") < now]
    if not targets:
        log("확인할 대상 없음 (예약 시각이 지났는데 URL 미확인인 글 없음)")
        return 0

    try:
        res = requests.get("https://rss.blog.naver.com/hardbar.xml", timeout=10)
        titles = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", res.text)
        links = re.findall(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", res.text)
        rss_map = dict(zip(titles, links))
    except Exception as e:
        log(f"RSS 조회 실패: {e}")
        return 0

    updated = 0
    for p in targets:
        url = rss_map.get(p["title"])
        if url:
            clean_url = url.split("?")[0]
            for post in data["posts"]:
                if post["id"] == p["id"]:
                    post["naver_url"] = clean_url
            updated += 1
            log(f"  확인됨: {p['title'][:30]} -> {clean_url}")
        else:
            log(f"  아직 RSS에 없음(비공개거나 더 대기 필요): {p['title'][:30]}")
    save_queue(data)
    return updated


def set_blogspot_link(post_id, blogspot_url):
    """연결 대기 상태의 글에 방구석 약국 글 URL을 나중에 연결한다."""
    data = load_queue()
    for p in data["posts"]:
        if p["id"] == post_id:
            p["blogspot_url"] = blogspot_url
    save_queue(data)
