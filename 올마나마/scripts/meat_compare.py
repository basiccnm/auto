# -*- coding: utf-8 -*-
"""정육: 우리 DB 육류 재료 vs 식봄 카테고리 가격 비교 (읽기전용·분석). (2026-07-25)

대표 지시: 정육 전량 스크랩 금지. 우리 목록 기준으로 식봄에서 확인·비교만.
식봄 정육 트리(2026-07-25)는 부위×원산지로 잘 갈려있다:
  돼지 505: 원물국내506 / 세절국내525 / 원물수입547 / 세절수입562
  소   586: 원물수입587 / 세절수입604 / 원물육우634 / 세절육우657 / 원물한우682 / 세절한우705
  닭   733: 원물국내734 / 세절국내737 / 원물수입754 / 세절수입757
→ 부위 잎(nid)만 콕 집어 수집. 캐시(_정육비교.json)에 쌓아 재실행은 API 안 부른다.
DB 에 쓰지 않는다. 비교표만 출력.
"""
import json, io, os, re, sqlite3, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foodspring_collect as fc

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CACHE = os.path.join(BASE, "data", "research", "foodspring", "_정육비교.json")
GAP = 2.1
BAD = re.compile(r"세트|선물|증정|샘플|기획전|양념|절임|장조림|반찬|훈제|햄|소시지|만두|"
                 r"돈까스|까스|너겟|가스|볶음밥|국\b|찌개|스프|육수|다시|진액|과자|육포|"
                 r"엑기스|우거지|곰탕|사골탕|설렁탕|국밥|탕수?육|꿔바로우|샤브|"
                 r"지방|우지|주태기름|기름|염통|간\b|천엽볶음|무침|장조림")

# 원산지: nid 구간으로 판정
def origin_of_nid(nid):
    if 506 <= nid <= 524 or 525 <= nid <= 546:
        return "돼지국산" if nid <= 546 else "?"
    if 547 <= nid <= 585:
        return "돼지수입"
    if 587 <= nid <= 603 or 604 <= nid <= 633:
        return "소수입"
    if 634 <= nid <= 656 or 657 <= nid <= 681:
        return "소육우"
    if 682 <= nid <= 704 or 705 <= nid <= 732:
        return "소한우"
    if 734 <= nid <= 753:
        return "닭국산"
    if 754 <= nid <= 770:
        return "닭수입"
    return "?"

# 우리 재료명 → 식봄 잎 nid 리스트 (부위 매핑, 원산지는 우리 basis 참고)
MEAT_MAP = {
    # 돼지 (대부분 수입미국)
    "수입 삼겹살":        [564, 548],
    "돼지 등심":         [576, 559],
    "돈까스용 등심":       [576, 559],
    "탕수돈육등심":        [576, 559],
    "등심돈육":          [576, 559],
    "오돌뼈용등심살":       [576, 559],
    "제육용 돼지 앞다리살":   [572, 527, 560, 511],
    "전지돈육":          [563, 551],
    "돼지고기 다짐육":      [578, 528],
    "돈육다짐만두소":       [578, 528],
    "라이스페이퍼만두돈육":   [578, 528],
    "항정살":           [568, 553, 531, 514],
    "감자탕돈뼈":         [536, 513, 557, 577],
    "족발 생육":         [543, 582],
    "돈족/머리고기":       [542, 543, 581, 582],
    "오소리감투":         [534, 571, 517, 556],
    # 소 (수입 다수 + 한우 뼈)
    "소다짐육":          [610, 642, 665, 690],
    "소고기 다짐육":       [610, 642, 665, 690],
    "소고기 등심":        [596, 627, 654, 677, 702, 725],
    "소고기 큐브스테이크":    [594, 614, 643, 666, 691, 714],
    "소고기 양지":        [603, 609, 617, 645, 668, 693, 716],
    "우삼겹":           [603, 609, 611, 671, 696, 719],
    "차돌박이":          [611, 671, 696, 719, 599],
    "소불고기용 쇠고기":     [632, 681, 729, 611],
    "한우 갈비":         [701, 724, 653, 676],
    "사골":            [687, 710, 639, 662],
    "잡뼈":            [688, 711, 640, 663, 630],
    "우족":            [685, 708, 637, 660, 607],
    "소꼬리":           [686, 709, 638, 661, 608],
    "도가니":           [686, 709, 638, 661],
    "소곱창":           [605, 635, 658, 683],
    "소대창":           [605, 635, 658, 683],
    "한우 흑천엽":        [683, 635, 605],
    # 닭
    "닭가슴살":          [740, 758],
    "닭다리살 정육":       [741, 760],
    "닭발":            [742, 762],
    "무뼈닭발":          [742, 762],
    "닭목살":           [746],
    "절단닭 10호":       [745, 759],
    "닭 콤보육":         [745, 759],
    "통닭 8호":         [736, 756, 755],
    "염지닭 10호":       [735],
    "태국산 조각 닭정육 12kg": [759, 745],
}


def collect_leaf(nid, cache):
    ck = str(nid)
    if ck in cache:
        return cache[ck]
    try:
        total, rows = fc.cat_search(nid)
    except Exception as e:
        print("  !! nid %s %s" % (nid, e), flush=True)
        cache[ck] = {"rows": []}
        return cache[ck]
    cache[ck] = {"total": total, "rows": rows}
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(GAP)
    return cache[ck]


def main():
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    need = sorted({nid for nids in MEAT_MAP.values() for nid in nids})
    print("수집 필요 잎 %d개 (캐시 %d개 보유)" % (len(need), len(cache)), flush=True)
    for nid in need:
        collect_leaf(nid, cache)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    print("\n%-18s %9s %-22s  %10s  판정" % ("재료", "우리값", "우리기준", "식봄최저(원산지)"))
    print("-" * 96)
    for iname, nids in MEAT_MAP.items():
        row = cur.execute("select wholesale_price, coalesce(wholesale_basis,'') "
                          "from ingredients where name=?", (iname,)).fetchone()
        if not row:
            continue
        wp, basis = row
        cand = []
        for nid in nids:
            for r in cache.get(str(nid), {}).get("rows", []):
                w = r.get("won_per_kg")
                if not w or not r.get("pack_kg") or r["pack_kg"] < 1.0:
                    continue
                if BAD.search(r["name"]):
                    continue
                cand.append((origin_of_nid(nid), w, r["name"]))
        if not cand:
            print("%-18s %9s %-22s  %10s" % (iname[:18], f"{wp or 0:,}", basis[:22], "─ 식봄 커버X"))
            continue
        # 중앙값 기반 이상치 컷: 파싱오류 저측 튐(삼겹살 336)·초고측(151,000) 제거.
        ws = sorted(w for _, w, _ in cand)
        med = ws[len(ws) // 2]
        cand = [(o, w, nm) for o, w, nm in cand if med * 0.4 <= w <= med * 8]
        if not cand:
            print("%-18s %9s %-22s  %10s" % (iname[:18], f"{wp or 0:,}", basis[:22], "─ 표본이상"))
            continue
        # 원산지별 최저
        byo = {}
        for o, w, nm in cand:
            if o not in byo or w < byo[o][0]:
                byo[o] = (w, nm)
        # 종 판정(매핑 nid 구간)
        anid = nids[0]
        species = "돼지" if 505 <= anid <= 585 else "소" if 586 <= anid <= 732 else "닭"
        # 우리 품목의 실제 원산지 티어 판정
        b = basis
        if species == "소":
            if "한우" in b:
                target = "소한우"
            elif any(x in b for x in ["수입", "미국", "호주", "멕시코", "캐나다", "뉴질"]):
                target = "소수입"
            else:                       # 국산/추정/무표기 = 식당 실사용 육우
                target = "소육우"
            order = ["소수입", "소육우", "소한우"]
        elif species == "돼지":
            target = "돼지수입" if any(x in b for x in ["수입", "미국", "스페인", "독일", "칠레"]) else "돼지국산"
            order = ["돼지수입", "돼지국산"]
        else:
            target = "닭수입" if any(x in b for x in ["수입", "태국", "브라질"]) else "닭국산"
            order = ["닭국산", "닭수입"]
        summ = " · ".join("%s %s" % (o.replace("소", "").replace("돼지", "").replace("닭", ""),
                                     f"{byo[o][0]:,}") for o in order if o in byo) or "─"
        tgtv = byo.get(target)
        if tgtv and wp:
            pct = (tgtv[0] - wp) / wp * 100
            judg = "[%s] 식봄 %+d%%" % (target.replace("소", "").replace("돼지", "").replace("닭", ""), pct) + \
                   ("↓쌈" if pct < -5 else "↑비쌈" if pct > 5 else "≈")
        elif not tgtv:
            judg = "[%s] 식봄 데이터없음" % target.replace("소", "").replace("돼지", "").replace("닭", "")
        else:
            judg = ""
        print("%-16s %8s %-16s 식봄> %-26s %s" % (
            iname[:16], f"{wp or 0:,}", basis[:16], summ[:26], judg))


main()
