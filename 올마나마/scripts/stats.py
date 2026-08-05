# -*- coding: utf-8 -*-
"""하루 성적표 — 유튜브 + GA4 + 클라우드플레어를 한 장으로. 2026-07-27

    python scripts/stats.py            최근 7일
    python scripts/stats.py --days 14

🔴 **숫자 셋이 다 다르다. 뭘 세는지가 달라서다.** 헷갈리지 말 것:
     · 클라우드플레어 = 서버에 들어온 요청. **봇·크롤러·우리 배포 확인까지 다 들어간다.**
       2026-07-27 실측 811 vs GA4 11 — 사실상 전부 사람이 아니었다.
     · GA4 = 자바스크립트가 돈 것만. 사람 수는 이쪽이 맞다.
     · 유튜브 = 영상 조회수. 사이트 유입과는 별개다.
   **사람 수를 말할 땐 GA4를 쓴다.** 클라우드플레어는 추세·서버 부하용으로만 본다.

🔴 인증
     · 구글(GA4·애드센스) → scripts/google_token.json  (없으면 python scripts/auth_google.py)
     · 유튜브            → _shorts/uploader/yt_token.json
     · 클라우드플레어     → **wrangler 로그인 토큰을 그대로 쓴다.** zone:read 가 들어 있어서
                          분석용 API 토큰을 따로 만들 필요가 없었다(2026-07-27 확인).
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

GA_PROPERTY = "properties/546434548"   # 올마나마
WRANGLER = os.path.expanduser("~/AppData/Roaming/xdg.config/.wrangler/config/default.toml")


def env():
    d = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                d[k.strip()] = v.strip()
    return d


def cf(days):
    """클라우드플레어 — 서버 요청 기준. 봇이 섞여 있다."""
    try:
        cfg = io.open(WRANGLER, encoding="utf-8").read()
        tok = re.search(r'oauth_token\s*=\s*"([^"]+)"', cfg).group(1)
    except Exception:
        return None
    zone = env().get("OLMANAMA_CF_ZONE_ID")
    if not zone:
        return None
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days - 1)
    q = {"query": """query($zone:String!,$s:Date!,$e:Date!){viewer{zones(filter:{zoneTag:$zone}){
           httpRequests1dGroups(limit:60, filter:{date_geq:$s, date_leq:$e}, orderBy:[date_ASC]){
             dimensions{date} sum{requests pageViews} uniq{uniques}}}}}""",
         "variables": {"zone": zone, "s": str(start), "e": str(end)}}
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql",
                                 data=json.dumps(q).encode(),
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        rows = r["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
        return {x["dimensions"]["date"]: x["uniq"]["uniques"] for x in rows}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()

    from googleapiclient.discovery import build
    from auth_google import creds
    g = creds()

    # ── 사이트 (GA4) ──
    ga = build("analyticsdata", "v1beta", credentials=g)
    rep = ga.properties().runReport(property=GA_PROPERTY, body={
        "dateRanges": [{"startDate": f"{a.days-1}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "date"}],
        "metrics": [{"name": "activeUsers"}, {"name": "screenPageViews"}],
        "orderBys": [{"dimension": {"dimensionName": "date"}}]}).execute()
    cfd = cf(a.days) or {}
    print("■ 사이트")
    print(f"  {'날짜':<9}{'방문자':>7}{'페이지뷰':>9}{'CF(봇포함)':>12}")
    for row in rep.get("rows", []):
        d = row["dimensionValues"][0]["value"]
        m = [int(x["value"]) for x in row["metricValues"]]
        key = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        print(f"  {d[4:6]}-{d[6:]:<6}{m[0]:>7,}{m[1]:>9,}{cfd.get(key, 0):>12,}")

    # ── 유입 ──
    src = ga.properties().runReport(property=GA_PROPERTY, body={
        "dateRanges": [{"startDate": f"{a.days-1}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "sessionSource"}],
        "metrics": [{"name": "sessions"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 8}).execute()
    print("\n■ 유입 경로 (세션)")
    for row in src.get("rows", []):
        print(f"  {row['dimensionValues'][0]['value'][:24]:<24}{int(row['metricValues'][0]['value']):>6,}")

    # ── 많이 본 글 ──
    pg = ga.properties().runReport(property=GA_PROPERTY, body={
        "dateRanges": [{"startDate": f"{a.days-1}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [{"name": "screenPageViews"}],
        "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
        "limit": 8}).execute()
    print("\n■ 많이 본 페이지")
    for row in pg.get("rows", []):
        print(f"  {row['dimensionValues'][0]['value'][:34]:<34}{int(row['metricValues'][0]['value']):>6,}")

    # ── 유튜브 ──
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    yp = os.path.join(BASE, "_shorts", "uploader", "yt_token.json")
    yc = Credentials.from_authorized_user_file(yp)
    if yc.expired:
        yc.refresh(Request())
    yt = build("youtube", "v3", credentials=yc)
    up = yt.channels().list(part="contentDetails,statistics", mine=True).execute()["items"][0]
    ch = up["statistics"]
    pl = up["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="snippet", playlistId=pl, maxResults=8).execute()["items"]
    ids = [i["snippet"]["resourceId"]["videoId"] for i in items]
    vids = {v["id"]: v for v in yt.videos().list(part="snippet,statistics", id=",".join(ids)).execute()["items"]}
    print(f"\n■ 유튜브  구독 {int(ch['subscriberCount']):,}명 · 누적 {int(ch['viewCount']):,}회")
    for vid in ids:
        v = vids.get(vid)
        if not v:
            continue
        s = v["statistics"]
        print(f"  {v['snippet']['publishedAt'][5:10]} {v['snippet']['title'][:26]:<26}"
              f"{int(s.get('viewCount', 0)):>7,}회  👍{s.get('likeCount', '0'):>3}  💬{s.get('commentCount', '0'):>2}")


if __name__ == "__main__":
    main()
