# -*- coding: utf-8 -*-
"""배포 후 구글에 «사이트맵 다시 읽어라» 알리기. 2026-07-28

    python scripts/gsc_ping.py

🔴 왜 필요한가 — 2026-07-28 실제 상황
   사이트맵을 07-19에 제출한 뒤 구글이 **9일간 다시 읽지 않았다.**
   그 사이 만든 재료 326장·브랜드 49장·지역 17장이 구글 목록에 없었고,
   서치콘솔에는 «발견됨 - 현재 색인이 생성되지 않음» 456장으로 잡혔다.
   → 배포할 때마다 재제출하면 이 일이 안 생긴다.

🔴 스코프는 `webmasters`(쓰기)가 필요하다. `webmasters.readonly` 로는 403 이 난다.
   `scripts/auth_google.py` 에 이미 들어 있다.

🔴 ⛔ 라이브 주소를 여러 개 동시에 부르지 마라. 700장을 10병렬로 확인했다가
   **429 레이트리밋**에 걸렸다(2026-07-28). 사이트맵 검증은 `_dist` 의 파일로 한다.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

SITE = "sc-domain:olmanama.com"
SITEMAP = "https://olmanama.com/sitemap.xml"


def main():
    from auth_google import creds
    from googleapiclient.discovery import build
    sc = build("searchconsole", "v1", credentials=creds())
    sc.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
    print("✅ 사이트맵 재제출:", SITEMAP)
    for s in sc.sitemaps().list(siteUrl=SITE).execute().get("sitemap", []):
        for c in s.get("contents", []):
            print(f"   제출 {c.get('submitted')}개 · 색인 {c.get('indexed', '-')}"
                  f" · 다운로드 {s.get('lastDownloaded', '-')[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
