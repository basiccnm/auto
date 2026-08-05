# 공정위 가맹점 통계(API 241) → brands 테이블 매장수·평균매출 컬럼 채우기
#   1) data/fftc_{2023,2022,2021}.json (fetch_fftc_raw.py FFTC_YR=... 로 미리 확보)
#   2) 우리 122개 브랜드와 brandNm 매칭 (정규화 exact + 수기 별칭)
#   3) 연도 폴백: 최신(2023)에 없거나 매장 0건이면 2022→2021 순으로 실데이터 채택
#      (브랜드별 실제 연도를 fftc_yr에 저장 → 페이지에 "(YYYY 공정위)" 정직 표기)
#
# 사용법: python collect_fftc.py
import sqlite3, json, os, re

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
YEARS = ["2023", "2022", "2021"]   # 우선순위(최신 먼저)

# 수기 별칭: 우리 brand_id → 공정위 정확한 brandNm 후보들(연도별 표기차 포함)
# 정규화 exact로 안 잡히거나 오탐 위험이 있는 것만. 법인명까지 대조 완료(2026-07-16).
MANUAL = {
    1:  ["비비큐(bbq)", "비비큐"],          # BBQ치킨 (제너시스비비큐, 2023 누락→2022)
    3:  ["비에이치씨(BHC)"],                # bhc치킨
    8:  ["60계"],                          # 60계치킨
    9:  ["푸라닭"],                         # 푸라닭치킨
    14: ["호식이두마리치킨"],                # 호식이지두마리치킨(오탈자 our측)
    15: ["멕시카나"],                       # 멕시카나치킨 (2023 누락→2022)
    16: ["보드람치킨"],                     # 보드람치킨 (2023 누락→2022)
    17: ["지코바양념치킨"],                  # 지코바치킨 (코바치 오탐 방지)
    20: ["훌랄라"],                         # 훌랄라참숯바베큐
    26: ["파파존스피자"],                   # 파파존스
    31: ["오구쌀피자"],                     # 59쌀피자 (동일법인 오구본가, 쌀피자 후신)
    37: ["롯데리아"],                       # 롯데리아 (2023 누락→2022)
    43: ["GTS BURGER"],                    # GTS버거
    49: ["태리로제떡볶이&닭강정"],           # 태리로제떡볶이
    50: ["우리할매 떡볶이"],                # 우리할매떡볶이
    57: ["고봉민김밥人"],                   # 고봉민김밥인
    59: ["마녀김밥"],                       # 청담동마녀김밥 (동일법인 멘토푸디즘)
    62: ["원할머니"],                       # 원할머니보쌈 (원앤원)
    63: ["놀부보쌈족발"],                   # 놀부보쌈
    69: ["한솥"],                          # 한솥도시락
    71: ["큰맘할매순대국"],                 # 큰맘할매순대국 (2023 누락→2022)
    74: ["백채"],                          # 백채김치찌개
    77: ["행복가마솥밥&알솥밥"],             # 채선당행복가마솥밥
    80: ["땅스부대찌개"],                   # 땅스부대찌개 (2023 누락→2022)
    89: ["노량진의 전설 미스사이공(miss420)"],  # 미스사이공
    90: ["Emoi(에머이)"],                  # 에머이
    94: ["코코이찌방야"],                   # 코코이찌방야 (2023 누락→2022, 농심)
    99: ["명랑시대쌀핫도그"],               # 명랑핫도그
    101: ["슬로우캘리"],                    # 슬로우캘리 (2023 누락→2022)
    103: ["메가엠지씨커피(MEGA MGC COFFEE)", "메가엠지씨커피(MEGAMGC COFFEE)"],  # 메가MGC커피
    112: ["던킨/던킨도너츠"],               # 던킨
    119: ["와플대학"],                      # 와플대학 (2023 누락→2022)
    122: ["투썸플레이스"],                  # 투썸플레이스 (2023 누락→2022)
}

# 어느 연도에도 실질 데이터 없음(직영/미등록) 또는 동명이 다른 브랜드 → NULL 확정
#  44 동대문엽기떡볶이: 유사명 '불닭발땡초동대문엽기떡볶이'(핫시즈너)는 별개 → 미매칭 유지
KNOWN_ABSENT = {42: "쉐이크쉑(직영)", 44: "동대문엽기떡볶이(원브랜드 미등록)",
                102: "샐러드판다", 105: "스타벅스(직영)"}

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[\s\-_.·’'\"!]", "", s)
    return s

def ensure_columns(cur):
    cols = {r[1] for r in cur.execute("PRAGMA table_info(brands)")}
    add = {"fftc_yr": "TEXT", "fftc_brand_nm": "TEXT", "fftc_corp_nm": "TEXT",
           "frcs_cnt": "INTEGER", "avrg_sls_amt": "INTEGER", "ar_unit_avrg_sls": "INTEGER"}
    for c, t in add.items():
        if c not in cols:
            cur.execute(f"ALTER TABLE brands ADD COLUMN {c} {t}")
            print(f"  + 컬럼 추가: brands.{c}")

def pick(rows):  # 동일명 여러 법인 → 가맹점수 최다(대표)
    return max(rows, key=lambda x: x.get("frcsCnt", 0))

def main():
    # 연도별 인덱스 로드
    by_norm, by_name = {}, {}
    for yr in YEARS:
        items = json.load(open(os.path.join(BASE, "data", f"fftc_{yr}.json"), encoding="utf-8"))
        bn, bnm = {}, {}
        for it in items:
            bn.setdefault(norm(it["brandNm"]), []).append(it)
            bnm.setdefault(it["brandNm"], []).append(it)
        by_norm[yr], by_name[yr] = bn, bnm

    def match_year(bid, name, yr):
        if bid in KNOWN_ABSENT:
            return None
        if bid in MANUAL:                       # 수기 지정 시 그 이름들만 신뢰(오탐 차단)
            for nm in MANUAL[bid]:
                if nm in by_name[yr]:
                    return pick(by_name[yr][nm])
            return None
        rows = by_norm[yr].get(norm(name))      # 그 외는 정규화 exact
        return pick(rows) if rows else None

    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
    ensure_columns(cur)
    brands = cur.execute("SELECT id,name FROM brands ORDER BY id").fetchall()

    matched, zero, miss = [], [], []
    for b in brands:
        bid, name = b["id"], b["name"]
        cand = []                               # (yr, row) 매칭된 것 전부
        for yr in YEARS:
            r = match_year(bid, name, yr)
            if r:
                cand.append((yr, r))
        # 매장 >0 인 것 중 최신연도 우선, 없으면 매칭된 것 중 최신연도(0건)
        pos = [(yr, r) for yr, r in cand if (r.get("frcsCnt") or 0) > 0]
        chosen = pos[0] if pos else (cand[0] if cand else None)
        if chosen is None:
            cur.execute("UPDATE brands SET fftc_yr=NULL,fftc_brand_nm=NULL,fftc_corp_nm=NULL,"
                        "frcs_cnt=NULL,avrg_sls_amt=NULL,ar_unit_avrg_sls=NULL WHERE id=?", (bid,))
            miss.append((bid, name))
            continue
        yr, r = chosen
        cur.execute("UPDATE brands SET fftc_yr=?,fftc_brand_nm=?,fftc_corp_nm=?,"
                    "frcs_cnt=?,avrg_sls_amt=?,ar_unit_avrg_sls=? WHERE id=?",
                    (yr, r["brandNm"], r["corpNm"], r.get("frcsCnt") or 0,
                     r.get("avrgSlsAmt") or 0, r.get("arUnitAvrgSlsAmt") or 0, bid))
        if (r.get("frcsCnt") or 0) > 0:
            matched.append((yr, name, r["brandNm"], r["frcsCnt"], r["avrgSlsAmt"]))
        else:
            zero.append((yr, name, r["brandNm"]))
    con.commit()

    yrcnt = {}
    for yr, *_ in matched: yrcnt[yr] = yrcnt.get(yr, 0) + 1
    print(f"\n=== 유효 {len(matched)} / 0건 {len(zero)} / 미매칭 {len(miss)} (연도별 유효: {yrcnt}) ===")
    print("\n[유효 매칭]")
    for yr, nm, fn, fc, av in sorted(matched, key=lambda x: -x[3]):
        print(f"  {nm:<16} → {fn:<20} 매장{fc:>5}  {av*1000/1e8:>5.1f}억  ({yr})")
    print("\n[0건 데이터(전 연도 0 → 미표시)]")
    for yr, nm, fn in zero:
        print(f"  {nm} → {fn} ({yr})")
    print("\n[미매칭(전 연도 없음 → 미표시)]")
    print("  " + ", ".join(nm for _, nm in miss))
    con.close()

if __name__ == "__main__":
    main()
