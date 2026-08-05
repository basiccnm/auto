# -*- coding: utf-8 -*-
"""로켓 없음(skip) 재료를 **검색어를 넓혀** 다시 찾는다. 2026-07-26

대표 지시: *"다시 찾어 100프로 있으니깐 로켓으로"*
  쿠팡에 로켓으로 파는 상품이 반드시 있다. 지금 못 찾은 건 **내 검색어가 좁아서**다.
  실제로 이런 것들이 넘어갔다 — `한우곱창` `닭 장각` `마라유` `소불고기용 쇠고기` `어니언후레이크`.

검색어를 넓히는 방법 (좁은 것 → 넓은 것 순으로 시도, 로켓이 나오면 멈춤)
  ① 재료명 그대로 (브랜드·용량만 뗀 것)
  ② 품목명(마지막 토큰)
  ③ 수식어를 뗀 것 — "소불고기용 쇠고기" → "불고기용 소고기" → "소고기"
  ④ 한자·괄호를 뗀 것 — "마라유(텅죠유 藤椒油)" → "마라유"
  ⑤ 손으로 적은 동의어 표 (SYN)

⚠️ 품목 검증은 **한 토큰이라도 맞으면** 통과시킨다. 다 맞아야 한다고 하면 후보가 0이 되어
   화면에 아무것도 안 뜬다. 틀린 건 대표가 화면에서 '매칭 미인정'으로 걸러낸다.

    python scripts/retail_retry.py                # skip 전부
    python scripts/retail_retry.py --budget=200   # API 200회까지
"""
import io
import json
import os
import re
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SLEEP = 2.0                 # 분당 30회. 쿠팡 API 정지되면 복구가 어렵다

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI       # noqa: E402
import retail_fill as RF              # noqa: E402
from mealkit_run import load_env      # noqa: E402

# 재료명으로는 쿠팡에서 안 팔리는 말들 — 실제로 파는 말로 바꿔준다
SYN = {
    "한우곱창": ["소곱창", "곱창"],
    "한우대창": ["소대창", "대창"],
    "닭 장각(통다리)": ["닭다리", "닭 통다리", "닭정육"],
    "닭 윙봉(냉동 완제품)": ["윙봉", "버팔로윙", "치킨윙"],
    "마라유(텅죠유 藤椒油)": ["마라유", "산초유", "마조유"],
    "소불고기용 쇠고기": ["불고기용 소고기", "소불고기", "소고기 불고기"],
    "어니언후레이크": ["프라이드 어니언", "양파 후레이크", "튀긴 양파"],
    "멜론원단": ["멜론 시럽", "메론 시럽"],
    "애플잼": ["사과잼", "애플 잼"],
    "견과류": ["믹스넛", "구운 아몬드", "견과"],
    "포기김치": ["배추김치", "포기김치"],
    "신선 생크림": ["생크림", "휘핑크림"],
    "단과자생지": ["단과자빵 생지", "빵 생지", "냉동 생지"],
    "와플베이크믹스생지": ["와플 믹스", "와플 반죽"],
    "면사랑 김말이튀김 1kg (25g 40개입)": ["김말이 튀김", "김말이"],
    "샐러드용 채소": ["샐러드 채소", "채소 믹스", "샐러드 믹스"],
    "청정원 소불고기양념장 500g": ["소불고기 양념", "불고기 양념"],
    "청정원 베이컨앤크림 까르보나라소스 350g": ["까르보나라 소스", "크림 파스타 소스"],
    "비에이치푸드 곱창·순대 볶음양념 2kg": ["곱창 양념", "볶음 양념", "매운 양념"],
    "족발 생육": ["족발", "돼지 족발"],
    "국밥용 양념장 (춘풍접객 2kg · 국밥/순대국/해장국 겸용)": ["다진양념", "국밥 양념", "다대기"],
    "족발용 간장육수 10kg": ["족발 육수", "간장 육수"],
}

_STRIP = re.compile(r"용$|형$|류$")

# 🔴 붙여 쓴 재료명은 토큰이 1개라 넓힐 수가 없다(2026-07-26 실패).
#    `빅비엔나소시지` `냉동딸기시럽퓨레` `분쇄쿠키가루` 같은 것들이 검색어 1개만 시도되고 끝났다.
#    그래서 ①앞의 수식어를 떼고 ②뒤의 품목어로 잘라 여러 검색어를 만든다.
PREFIX = ("빅", "냉동", "냉장", "가공", "액상", "분말", "분쇄", "유기농", "업소용", "대용량",
          "신선", "생", "즉석", "수입", "국내산", "친환경", "무가당")
# 뒤에 붙는 품목어 — 긴 것부터 찾는다
TAILWORD = ("시럽퓨레", "농축시럽", "믹스시럽", "베이스퓨레", "과일퓨레", "초코퓨레", "토핑퓨레",
            "시럽", "퓨레", "파우더", "가루", "소시지", "베이컨", "치즈", "소스", "양념", "육수",
            "베이스", "믹스", "토핑", "사리", "다시", "생지", "정육", "생육", "원단", "면", "잼")


def _split_compound(w):
    """붙여 쓴 한 단어를 넓은 검색어들로 쪼갠다."""
    out = []
    base = w
    for p in PREFIX:                       # 앞 수식어 제거 (빅비엔나소시지 → 비엔나소시지)
        if base.startswith(p) and len(base) > len(p) + 1:
            base = base[len(p):]
            out.append(base)
            break
    for t in TAILWORD:                     # 뒤 품목어로 자르기
        if base.endswith(t) and len(base) > len(t):
            head = base[:-len(t)]
            if len(head) >= 2:
                out.append("%s %s" % (head, t))   # 딸기시럽 → "딸기 시럽"
                out.append(head)                  # 딸기
            out.append(t)                         # 시럽
            break
    return out


def kw_candidates(name):
    """넓은 순서로 검색어를 만든다."""
    out = []
    if name in SYN:
        out += SYN[name]
    if name in RF.KWMAP:
        out.append(RF.KWMAP[name])
    # 괄호·한자·용량 제거
    base = re.sub(r"\([^)]*\)", " ", name or "")
    base = re.sub(r"[一-鿿]+", " ", base)
    base = re.sub(r"\d+(\.\d+)?\s*(kg|g|l|ml|개입|개|매|장|봉|팩|인분)", " ", base, flags=re.I)
    base = re.sub(r"[·/]", " ", base)
    toks = [t for t in base.split() if len(t) >= 2]
    if toks:
        out.append(" ".join(toks))            # 전체
        if len(toks) >= 2:
            out.append(" ".join(toks[-2:]))
        out.append(toks[-1])                  # 품목명
        s2 = [_STRIP.sub("", t) for t in toks]   # "소불고기용" → "소불고기"
        if s2 != toks:
            out.append(" ".join(s2))
            out.append(s2[-1])
        out += _split_compound(toks[-1])       # 붙여 쓴 단어 쪼개기
        if len(toks) == 1:
            out += _split_compound(toks[0])
    seen, res = set(), []
    for k in out:
        k = re.sub(r"\s+", " ", k).strip()
        if k and len(k) >= 2 and k not in seen:
            seen.add(k)
            res.append(k)
    return res[:6]


def main():
    budget = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--budget=")), 400)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")

    rows = [r for r in c.execute("""
        SELECT x.ingredient_key k, i.name,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=x.ingredient_key) uses
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE x.status='skip' ORDER BY uses DESC""")]
    print("로켓 없음 %d종 다시 찾는다 (검색어 최대 5개씩 · %.0f초 간격)" % (len(rows), SLEEP), flush=True)
    print("", flush=True)

    cur = c.cursor()
    used = ok = still = 0
    for r in rows:
        if used >= budget:
            print("예산 %d회 소진 — 중단" % budget, flush=True)
            break
        rej = {q[0] for q in c.execute(
            "SELECT product_id FROM retail_rejected WHERE ingredient_key=?", (r["k"],))}
        found = None
        tried = []
        for kw in kw_candidates(r["name"]):
            tried.append(kw)
            fp = RF.cpath(kw)
            if os.path.exists(fp):
                try:
                    items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
                except Exception:
                    items = []
            else:
                if used >= budget:
                    break
                try:
                    d = CI.api_search(kw, ak, sk)
                except Exception as e:
                    print("  ! %-20s %s" % (kw[:20], str(e)[:40]), flush=True)
                    used += 1
                    time.sleep(SLEEP)
                    continue
                if d.get("rCode") not in (0, "0"):
                    print("  !! rCode=%s — 중단(쿠팡 한도 보호)" % d.get("rCode"), flush=True)
                    return 1
                items = (d.get("data") or {}).get("productData") or []
                io.open(fp, "w", encoding="utf-8").write(
                    json.dumps({"keyword": kw, "items": items}, ensure_ascii=False))
                used += 1
                time.sleep(SLEEP)

            cw = [t for t in kw.split() if len(t) >= 2]
            cands = []
            for p in items:
                pn, price = p.get("productName") or "", p.get("productPrice")
                if not price or not p.get("isRocket"):
                    continue
                if p.get("productId") in rej or not RF.is_food(p) or RF.JUNK.search(pn):
                    continue
                flat = re.sub(r"\s+", "", pn)
                if not any(w in flat for w in cw):       # 한 토큰이라도 맞으면 후보
                    continue
                if [b for b in CI.PROCESSED if re.search(b, pn) and not re.search(b, r["name"])]:
                    continue
                cands.append((1 if CI.PREMIUM.search(pn) else 0, price, p, kw))
            cands.sort(key=lambda x: (x[0], x[1]))
            if cands:
                found = cands[0]
                break

        if not found:
            still += 1
            print("  ⏭ %-24s 여전히 없음 (시도: %s)" % (r["name"][:24], " / ".join(tried)), flush=True)
            continue
        _, price, p, kw = found
        gv = RF.pack_g(p["productName"])
        cur.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                    (r["k"], p.get("productId"), p["productName"], price, gv,
                     p.get("productImage"), p.get("productUrl")))
        c.commit()
        ok += 1
        print("  ✅ %-24s %8s원 %7s  [%s] %s" % (
            r["name"][:24], format(price, ","), ("%gg" % gv) if gv else "용량?",
            kw, p["productName"][:36]), flush=True)

    print("", flush=True)
    print("끝. 살린 것 %d종 · 여전히 없음 %d종 · API %d회" % (ok, still, used), flush=True)
    c.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
