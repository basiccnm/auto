# 공정위 가맹점 통계 API(241) 전체 브랜드 fetch → 로컬 JSON 캐시
# 11,167개 브랜드 (yr=2023). 페이지네이션. 한 번만 받아두고 매칭은 별도 스크립트에서.
import urllib.request, ssl, json, os, time

KEY = os.environ.get("FFTC_KEY", "01d41ee31954bf8a99a618c1c206dd53aff2ce5fe2e53cec92fd3bd371e70dda")
YR = os.environ.get("FFTC_YR", "2023")
BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
OUT = os.path.join(BASE, "data", f"fftc_{YR}.json")

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(page, rows=1000):
    url = ("http://apis.data.go.kr/1130000/FftcBrandFrcsStatsService/getBrandFrcsStats"
           f"?serviceKey={KEY}&yr={YR}&pageNo={page}&numOfRows={rows}&resultType=json")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            body = urllib.request.urlopen(req, timeout=40, context=ctx).read().decode("utf-8")
            d = json.loads(body)
            if str(d.get("resultCode")) not in ("00", "0"):
                raise RuntimeError(f"resultCode={d.get('resultCode')} {d.get('resultMsg')}")
            return d
        except Exception as e:
            print(f"  page {page} 재시도 {attempt+1}: {e}")
            time.sleep(2)
    raise RuntimeError(f"page {page} 실패")

def main():
    first = fetch(1)
    total = int(first["totalCount"])
    rows = int(first["numOfRows"])
    pages = (total + rows - 1) // rows
    items = list(first["items"])
    print(f"총 {total}개 / {rows}개씩 / {pages}페이지")
    for p in range(2, pages + 1):
        d = fetch(p)
        got = d.get("items") or []
        items.extend(got)
        print(f"  page {p}/{pages}: +{len(got)} (누적 {len(items)})")
    json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"저장: {OUT} ({len(items)}건)")

if __name__ == "__main__":
    main()
