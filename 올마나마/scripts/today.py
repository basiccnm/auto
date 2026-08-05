# -*- coding: utf-8 -*-
"""오늘 들어온 사람 — **어디서 왔고, 뭘 검색해서 왔는지**. 2026-08-01

    python scripts/today.py            # 오늘
    python scripts/today.py 2026-07-31 # 특정 날짜

`stats.py` 는 «며칠 추세» 를 보는 것이고, 이건 «오늘 한 명 한 명이 어떻게 왔나» 를 본다.

🔴 검색어를 어디서 얻나
   · 구글 — 서치콘솔이 준다(쿼리별 클릭·노출). **2~3일 늦다** — 오늘 것은 대개 아직 없다.
   · 네이버 — **검색어를 주는 API가 없다.** 세션 수만 GA4 로 보이고 무슨 말로 왔는지는 못 본다.
   · GA4 는 검색어를 안 준다(구글이 2013년에 막았다). 그래서 서치콘솔을 같이 본다.

🔴 GA4 는 몇 시간 늦을 수 있다. 오늘 숫자가 0이면 «아직 안 들어온 것» 이 아니라
   «아직 집계 안 된 것» 일 수 있으니 어제와 같이 본다.
"""
import datetime
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

GA_PROPERTY = "properties/546434548"
SITE = "sc-domain:olmanama.com"


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else str(datetime.date.today())
    prev = str(datetime.date.fromisoformat(day) - datetime.timedelta(days=1))

    from auth_google import creds
    from googleapiclient.discovery import build
    c = creds()
    ga = build("analyticsdata", "v1beta", credentials=c)
    sc = build("searchconsole", "v1", credentials=c)

    def rep(dims, mets, start, end, n=25, order=None):
        body = {"dateRanges": [{"startDate": start, "endDate": end}],
                "dimensions": [{"name": d} for d in dims],
                "metrics": [{"name": m} for m in mets],
                "limit": n}
        if order:
            body["orderBys"] = [{"metric": {"metricName": order}, "desc": True}]
        return ga.properties().runReport(property=GA_PROPERTY, body=body).execute().get("rows", [])

    # ── 총계 ──────────────────────────────────────────────
    print(f"■ {day} 방문")
    for label, d in ((day, day), (f"{prev} (어제)", prev)):
        r = rep([], ["activeUsers", "screenPageViews", "sessions"], d, d)
        if r:
            v = [int(x["value"]) for x in r[0]["metricValues"]]
            print(f"   {label:<18} 방문자 {v[0]:>4} · 페이지뷰 {v[1]:>5} · 세션 {v[2]:>4}")
        else:
            print(f"   {label:<18} 집계 없음")

    # ── 어디서 왔나 ────────────────────────────────────────
    rows = rep(["sessionSource", "sessionMedium"], ["sessions"], day, day, order="sessions")
    print(f"\n■ 어디서 왔나 ({day})")
    if not rows:
        print("   아직 없음")
    for r in rows:
        s, m = r["dimensionValues"][0]["value"], r["dimensionValues"][1]["value"]
        n = int(r["metricValues"][0]["value"])
        kind = {"organic": "🔍 검색", "referral": "🔗 링크", "cpc": "💰 광고",
                "(none)": "➡️ 직접"}.get(m, m)
        print(f"   {kind:<8} {s[:28]:<30}{n:>5}")

    # ── 링크로 왔으면 어느 주소에서 ─────────────────────────
    rows = rep(["pageReferrer"], ["sessions"], day, day, order="sessions")
    print(f"\n■ 링크 경로 (그 페이지 주소)")
    got = False
    for r in rows:
        u = r["dimensionValues"][0]["value"]
        if not u or u.startswith("https://olmanama.com") or u.startswith("https://www.olmanama.com"):
            continue
        got = True
        print(f"   {u[:72]:<74}{int(r['metricValues'][0]['value']):>4}")
    if not got:
        print("   외부 링크 유입 없음")

    # ── 처음 들어온 페이지 ──────────────────────────────────
    rows = rep(["landingPage"], ["sessions"], day, day, order="sessions")
    print(f"\n■ 처음 들어온 페이지")
    for r in rows[:12]:
        print(f"   {r['dimensionValues'][0]['value'][:44]:<46}{int(r['metricValues'][0]['value']):>4}")
    if not rows:
        print("   아직 없음")

    # ── 구글 검색어 (서치콘솔) ──────────────────────────────
    #  🔴 2~3일 늦다. 오늘 것이 비면 최근 3일치를 대신 보여준다.
    def q(start, end):
        return sc.searchanalytics().query(siteUrl=SITE, body={
            "startDate": start, "endDate": end,
            "dimensions": ["query"], "rowLimit": 20,
            "orderBy": [{"field": "clicks", "descending": True}]}).execute().get("rows", [])

    rows = q(day, day)
    label = day
    if not rows:
        back = str(datetime.date.fromisoformat(day) - datetime.timedelta(days=3))
        rows = q(back, day)
        label = f"{back}~{day} (오늘 것은 아직 안 들어옴 — 구글이 2~3일 늦다)"
    print(f"\n■ 구글 검색어 · {label}")
    if not rows:
        print("   없음")
    for r in rows:
        k = r["keys"][0]
        print(f"   {k[:26]:<28} 클릭 {int(r['clicks']):>3} · 노출 {int(r['impressions']):>4}"
              f" · 순위 {r['position']:.1f}")

    print("\n※ 네이버는 검색어를 주는 API가 없다 — 세션 수만 위 «어디서 왔나» 에서 보인다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
