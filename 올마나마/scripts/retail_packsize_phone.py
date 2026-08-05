# -*- coding: utf-8 -*-
"""폰 크롬으로 쿠팡 상품 페이지를 열어 **용량만** 읽는다. 2026-07-27

🔴 왜 폰인가 — 다른 경로가 다 막혔다
   · 쿠팡 API : 용량 필드를 안 준다 (상품명에 적힌 것만)
   · 헤드리스 크롬 : `Access Denied`
   · in-app 브라우저 : 정책상 쿠팡 차단
   · 쿠팡 앱(딥링크) : 로딩이 안 끝나 uiautomator 가 idle 을 못 얻음
   · 에뮬레이터 **앱** : 차단됨(대표 확인)
   ✅ **에뮬레이터 크롬은 열린다**(2026-08-02 확인). LDPlayer + com.android.chrome 으로
      상품 페이지가 정상 로딩되고 uiautomator 로 용량을 읽었다. `PACK_DEV=emulator-5556`.
      「에뮬은 차단」이라고 뭉뚱그려 적어놔서 이 경로를 6일간 안 썼다 — 앱과 크롬은 다르다.
   · **폰의 `curl` 도 Access Denied** — Akamai 가 브라우저 아닌 요청을 막는다(IP 무관)
   ✅ **실제 폰의 크롬**만 열린다.

🔴 상품을 바꾸지 않는다 (대표 지시). `product_id` 그대로 두고 `pack_g` 만 채운다.
   자동으로 상품을 다시 고르면 다른 물건이 붙는다 — 오늘 세 번 그랬다
   (포마스 혼합유 · 리코타 치즈 · 알룰로스).

🔴 이름 파싱은 못 믿는다 (2026-07-27 시험에서 5개 중 2개 오독)
   상품 페이지에 **추천 상품**이 섞여 있어 첫 상품명을 잡으면 남의 상품을 읽는다 —
   모차렐라 치즈 자리에 "앵커 체다치즈 960g×4", 튀김가루 자리에 "곰표 부침가루 500g×20개".
   ✅ 쿠팡이 화면에 **단위당 가격**을 직접 써 준다. 그게 가장 확실하다:
        곰곰 98.3% 모짜렐라 피자치즈 / 5,520원 / (10g당 184원) / 개당 중량: 300g
        → 5,520 ÷ 184 × 10 = 300g
   그리고 **우리 상품명이 화면에 있는지 먼저 확인**한다. 없으면 남의 페이지이므로 버린다.

⚠️ 첫 화면에 없으면 **스크롤해서 찾는다**(대표 지시) — 상세 스펙은 아래쪽에 있다.
⚠️ 탭이 쌓이면 안 된다(대표 지시). 크롬은 `application_id` 를 줘도 새 탭을 만든다(시험 확인).
   그래서 **시작·20개마다·끝날 때 크롬을 종료**해 탭을 비운다.
⚠️ 속도는 1개당 약 6초. **3초로 돌렸다가 11개에서 차단됐다**(2026-07-27) — 2배로 늘렸다.
   간격을 조금씩 흔든다. 연속 3회 실패면 즉시 멈춘다(차단 신호).
   차단되면 폰 IP 가 막힌다. USB + LTE 로 바꾸면 IP 가 바뀌어 풀린다.

    python scripts/retail_packsize_phone.py --limit 6
    python scripts/retail_packsize_phone.py --limit 120 --apply
"""
import io
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "retail_packsize_phone.json")
TMP = os.path.join(os.environ.get("TEMP", "."), "cp_pack.xml")
ADB = r"C:\LDPlayer\LDPlayer14\adb.exe"
def _pick_dev():
    """연결된 기기를 고른다. USB(시리얼) 우선, 없으면 무선, 에뮬레이터는 제외."""
    out = subprocess.run([ADB, "devices"], capture_output=True).stdout.decode("utf-8", "replace")
    devs = [l.split()[0] for l in out.splitlines()[1:] if "	device" in l]
    real = [d for d in devs if not d.startswith("emulator-")]
    usb = [d for d in real if ":" not in d]
    return (usb or real or devs or [""])[0]


DEV = os.environ.get("PACK_DEV") or _pick_dev()
CHROME_ACT = "com.android.chrome/com.google.android.apps.chrome.Main"
MAX_SCROLL = 12         # 첫 화면에 없으면 이만큼 내려가며 찾는다
#  🔴 3 이었는데 12 로 늘렸다(2026-08-02 대표 지시: "용량은 스크롤로 내리면 확인할수 있어").
#     쿠팡 상품 페이지는 길어서 상세 스펙이 한참 아래에 있다 — 3번으로는 못 닿는다.
TAB_CLEAR = 50          # 50개마다 크롬 종료로 탭 한 번에 정리(대표 지시)

RX_UNITPRICE = re.compile(r"\(\s*([\d,.]+)\s*(kg|g|l|ml)\s*당\s*([\d,]+)\s*원\s*\)", re.I)
RX_PERITEM = re.compile(r"개당\s*중량\s*[:：]\s*([\d,.]+)\s*(kg|g|l|ml)", re.I)
RX_COMBO = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*[x×]\s*(\d+)\s*개입(?:\s*[x×]\s*(\d+)\s*개)?", re.I)
RX_TOTALW = re.compile(r"(?:총\s*)?(?:내용량|중량)\s*[:：]\s*([\d,.]+)\s*(kg|g|l|ml)", re.I)
RX_NAMEVOL = re.compile(r",\s*([\d,.]+)\s*(kg|g|l|ml)\b", re.I)
RX_CNT = re.compile(r",\s*(\d+)\s*(?:개|입|팩|병|봉|매)\b")
RX_BLOCK = re.compile(r"Access Denied|접근이 거부|비정상|잠시 후 다시|로봇|일시적으로|"
                      r"서버에서 오류|서비스 이용이|요청이 많아")


def gof(v, u):
    v = float(str(v).replace(",", ""))
    return v * 1000 if u.lower() in ("kg", "l") else v


def norm(s):
    return re.sub(r"[\s,.()\[\]/%·]+", "", (s or "")).lower()


def sh(*args, timeout=40):
    try:
        r = subprocess.run([ADB, "-s", DEV] + list(args), capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def clear_tabs():
    """크롬을 종료해 탭을 비운다 — 안 하면 탭이 계속 쌓인다."""
    sh("shell", "am", "force-stop", "com.android.chrome")
    time.sleep(0.8)


def dump():
    for _ in range(2):
        sh("shell", "uiautomator", "dump", "/sdcard/cp_pack.xml")
        sh("pull", "/sdcard/cp_pack.xml", TMP)
        try:
            root = ET.parse(TMP).getroot()
        except Exception:
            time.sleep(1)
            continue
        return [t for t in ((n.get("text") or "").strip() for n in root.iter("node")) if t]
    return []


def open_product(pid):
    sh("shell", "am", "start", "-n", CHROME_ACT, "-a", "android.intent.action.VIEW",
       "-d", "https://m.coupang.com/vm/products/%s" % pid)


def scroll():
    sh("shell", "input", "swipe", "480", "1800", "480", "700", "300")


# 광고·알림 팝업이 페이지를 덮으면 용량을 못 읽는다(대표 확인 2026-07-27).
# 닫기 버튼을 찾아 누른다. ⛔ '확인'·'동의'·'허용'은 절대 누르지 않는다.
POPUP_CLOSE = ("닫기", "닫음", "취소", "나중에", "다음에", "괜찮아요", "건너뛰기", "X")


def close_popup():
    """팝업이 있으면 닫는다. 닫았으면 True."""
    sh("shell", "uiautomator", "dump", "/sdcard/cp_pack.xml")
    sh("pull", "/sdcard/cp_pack.xml", TMP)
    try:
        root = ET.parse(TMP).getroot()
    except Exception:
        return False
    import re as _re
    for n in root.iter("node"):
        blob = ((n.get("text") or "") + " " + (n.get("content-desc") or "")).strip()
        if not blob or not any(w == blob or w in blob for w in POPUP_CLOSE):
            continue
        if _re.search(r"확인|동의|허용|구매|주문|결제|담기", blob):
            continue
        m = _re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds") or "")
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if (x2 - x1) > 700 or (y2 - y1) > 400:      # 너무 큰 건 닫기 버튼이 아니다
            continue
        sh("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(0.8)
        return True
    return False


#  🔴 **판정에 쓰면 안 되는 낱말** — 아무 상품에나 붙어 있다(2026-08-02 신설).
#     「곰곰 저당 시저 드레싱」 자리에 「곰곰 냉동 애플망고」가 붙었다.
#     PB 브랜드명·배송표시·홍보문구가 겹쳐서 «우리 상품 맞다» 로 통과해버린 것이다.
STOP_TOK = {
    "곰곰", "로켓프레시", "로켓배송", "로켓", "초특가", "특가", "무료배송", "대용량",
    "업소용", "국내산", "수입산", "냉동", "냉장", "실온", "무항생제", "프리미엄",
    "이벤트", "기획", "묶음", "세트", "정품", "당일출고", "무료", "행사", "신상품",
}


def ours_tokens(our_name):
    """상품명에서 그 상품을 가리키는 낱말. 긴 것 위주로 본다 —
    짧은 토큰(1kg·1개 같은 것)은 아무 페이지에나 있어 판정에 쓸 수 없다.
    브랜드·배송·홍보 낱말(STOP_TOK)도 뺀다 — 그게 겹쳐서 남의 페이지를 통과시켰다."""
    raw = [t for t in re.split(r"[\s,\[\]()]+", our_name or "") if len(t) >= 2]
    raw = [t for t in raw if not re.fullmatch(r"[\d.,]+(kg|g|l|ml|개|입|팩|매)?", t, re.I)]
    raw = [t for t in raw if norm(t) not in {norm(x) for x in STOP_TOK}]
    raw.sort(key=len, reverse=True)
    return raw[:4]


def ours_hit(line, toks):
    """그 줄이 **우리 상품**을 가리키나. 겹치는 낱말이 2개 이상이어야 한다.
    쓸 낱말이 1개뿐이면 그 1개로 판정한다(그 이상 조일 수가 없다)."""
    if not toks:
        return False
    n = sum(1 for t in toks if norm(t) in norm(line))
    return n >= min(2, len(toks))


def find_pack(lines, price, toks):
    """(용량 g, 근거). 화면에 적힌 것만 쓴다 — 추측하지 않는다.

    🔴 순서를 바꿨다 (2026-07-27, 6건 중 최소 1건이 틀려서 확인됨)
       예전엔 '쿠팡 단위가'를 1순위로 봤다. 그런데 **본 상품의 단위가 줄이 쿠폰 때문에
       `(100ml당 0원)` 으로 나오는 경우**가 있고, 그러면 그 줄을 건너뛰고
       **스크롤하다 만난 추천 상품의 단위가**를 집는다.
       곰곰 해바라기유(4,980원)가 `(100ml당 2,864원)` 을 물어 **174ml** 로 저장됐다.
       정답은 상품명 줄에 그대로 있었다 — `곰곰 해바라기유, 1L, 1개`.
       ✅ 그래서 **우리 상품명 줄이 1순위**다. 그리고 나머지 규칙은
          **상품명 줄 주변 창(window)** 안에서만 본다 — 남의 상품이 섞이지 않게."""
    # ⓪ 우리 상품명이 몇 번째 줄인지 — 여기가 본 상품 영역의 시작이다
    at = -1
    for i, l in enumerate(lines):
        if toks and all(norm(t) in norm(l) for t in toks[:2]):
            at = i
            break
    if at < 0:
        for i, l in enumerate(lines):
            if ours_hit(l, toks):
                at = i
                break
    win = lines[at:at + 45] if at >= 0 else lines[:45]

    # ① **우리 상품명 줄**의 용량 — 가장 확실하다(그 줄이 곧 우리 상품이다)
    for l in ([lines[at]] if at >= 0 else []) + win:
        if not ours_hit(l, toks):
            continue
        m = RX_NAMEVOL.search(l)
        if m:
            cm = RX_CNT.search(l)
            n = int(cm.group(1)) if cm else 1
            g = gof(m.group(1), m.group(2)) * n
            if 5 <= g <= 60000:
                return round(g), "상품명: %s" % l.strip()[:36]
    # ② 개당 중량 명시
    for l in win:
        m = RX_PERITEM.search(l)
        if m:
            g = gof(m.group(1), m.group(2))
            if 5 <= g <= 60000:
                return round(g), "개당 중량: %s" % l.strip()[:28]
    # ③ "75g × 4개입 × 1개"
    for l in win:
        m = RX_COMBO.search(l)
        if m:
            g = gof(m.group(1), m.group(2)) * int(m.group(3)) * int(m.group(4) or 1)
            if 5 <= g <= 60000:
                return round(g), "구성: %s" % l.strip()[:28]
    # ④ 내용량·중량 표기
    for l in win:
        m = RX_TOTALW.search(l)
        if m:
            g = gof(m.group(1), m.group(2))
            if 5 <= g <= 60000:
                return round(g), "중량 표기: %s" % l.strip()[:28]
    # ⑤ 쿠팡이 계산해 준 단위당 가격 — **상품명 줄 주변에서만**. 0원 줄은 쿠폰 표시라 건너뛴다
    for l in win:
        m = RX_UNITPRICE.search(l)
        if not m:
            continue
        per = float(m.group(3).replace(",", ""))
        if per <= 0:
            continue
        base = gof(m.group(1), m.group(2))
        g = price / per * base
        if 5 <= g <= 60000:
            return round(g), "쿠팡 단위가 %s" % l.strip()[:22]
    return None, ""


def wait_loaded(timeout=26):
    """상품 페이지가 다 뜰 때까지 기다린다. 뜬 줄 수로 판정한다.

    🔴 2026-07-27: 4~5초만 기다리고 읽어서 **첫 건부터 '차단'으로 오판**했다.
       실제로는 화면이 주소줄 하나(1줄)뿐인 로딩 중이었고, 17초쯤 지나니 2,279줄이 떴다.
       ('없다/막혔다'를 단정하기 전에 내 코드를 먼저 의심한다 — `assume-my-filter-is-wrong-first`)"""
    t0 = time.time()
    last = []
    while time.time() - t0 < timeout:
        lines = dump()
        if len(lines) > 60:            # 상품 상세가 뜨면 수백~수천 줄이다
            return lines
        if any(RX_BLOCK.search(l) for l in lines):
            return lines               # 진짜 차단/오류 문구 → 호출부가 판단
        last = lines
        time.sleep(2.0)
    return last


def dismiss_dialog():
    """'서버에서 오류' 같은 일회성 알림창을 뒤로가기로 닫는다.
    ⛔ '확인'·'동의'·'허용' 버튼은 누르지 않는다 — 무엇에 동의하는지 알 수 없다."""
    sh("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(1.0)


def read_one(pid, our_name, price):
    toks = ours_tokens(our_name)
    lines = []
    for attempt in (1, 2):             # 오류창은 한 번 다시 열어본다(차단 오판 방지)
        open_product(pid)
        time.sleep(random.uniform(2.5, 3.5))
        lines = wait_loaded()
        if not any(RX_BLOCK.search(l) for l in lines):
            break
        if attempt == 1:
            dismiss_dialog()
            clear_tabs()
            time.sleep(random.uniform(2.0, 3.0))
    if any(RX_BLOCK.search(l) for l in lines) and len(lines) < 60:
        return None, "차단"
    close_popup()          # 광고 팝업이 덮고 있으면 닫는다
    seen = []
    for step in range(MAX_SCROLL + 1):
        lines = dump() if step else lines   # step0 은 wait_loaded() 가 읽어둔 것을 그대로 쓴다
        seen += lines
        if step == 0 and toks and not any(norm(t) in norm("\n".join(seen)) for t in toks):
            # 아직 로딩 중일 수 있으니 한 번 더 본다
            time.sleep(1.5)
            seen += dump()
            if not any(norm(t) in norm("\n".join(seen)) for t in toks):
                return None, "다른 상품 페이지(우리 상품명 없음)"
        g, why = find_pack(seen, price, toks)
        if g:
            return g, why + ("" if step == 0 else "  [스크롤%d]" % step)
        if step < MAX_SCROLL:
            scroll()
            time.sleep(random.uniform(1.0, 1.5))
    return None, "용량 표기 없음(스크롤%d)" % MAX_SCROLL


def main():
    apply = "--apply" in sys.argv
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 20
    # 🔴 브랜드 한 곳씩 한다(`brand-one-at-a-time-workflow`). 몰아서 돌리면 차단된다 —
    #    2026-07-27 에 3초 간격으로 몰다가 11건에서 막혔다. 브랜드당 5~10건이면 안 막힌다.
    brand = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cond, args = "", []
    if brand:
        cond = """ AND EXISTS (SELECT 1 FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                    JOIN brands b ON b.id=m.brand_id
                   WHERE mi.ingredient_key=x.ingredient_key AND b.name LIKE ?)"""
        args = ["%" + brand + "%"]
    rows = [dict(r) for r in c.execute("""
        SELECT x.ingredient_key k, i.name, x.product_id pid, x.name pn, x.price price,
               (SELECT COUNT(*) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=x.ingredient_key AND b.published=1) nm,
               (SELECT COUNT(*) FROM dish_ingredients d WHERE d.ingredient_key=x.ingredient_key) nd
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE (x.pack_g IS NULL OR x.pack_g = 0) AND x.price > 0 AND x.product_id IS NOT NULL
          AND COALESCE(x.status,'') NOT IN ('store','none')""" + cond + """
        ORDER BY (nm + nd) DESC LIMIT ?""", args + [lim])]
    print("용량 없는 소매 상품 %d건%s — 폰 크롬으로 용량만 읽는다" % (
        len(rows), (" (%s)" % brand) if brand else ""), flush=True)
    print("", flush=True)
    clear_tabs()

    res, fails = [], 0
    try:
        _run(c, rows, apply, res)
    except KeyboardInterrupt:
        print("중단됨 — 읽은 것까지 저장돼 있습니다", flush=True)
    _finish(c, res, apply)
    return


def _run(c, rows, apply, res):
    fails = 0
    for i, r in enumerate(rows, 1):
        if i > 1 and (i - 1) % TAB_CLEAR == 0:
            clear_tabs()
            print("     … 탭 비움", flush=True)
        g, why = read_one(r["pid"], r["pn"], r["price"])
        if why == "차단":
            print("!! 차단 신호 — 즉시 중단", flush=True)
            break
        res.append(dict(r, pack_g=g, why=why))
        if g:
            fails = 0
            # 한 건 읽는 즉시 저장한다 — 중간에 끊겨도 남는다
            if apply:
                c.execute("UPDATE ingredient_retail SET pack_g=? WHERE ingredient_key=?",
                          (g, r["k"]))
                c.commit()
            io.open(OUT, "w", encoding="utf-8").write(
                json.dumps(res, ensure_ascii=False, indent=1))
            print("  %3d ✅ %-20s %8s원 %8s  %s" % (
                i, r["name"][:20], format(round(r["price"]), ","),
                ("%gg" % g) if g < 1000 else ("%gkg" % (g / 1000.0)), why[:44]), flush=True)
        else:
            if why not in ("상품명 확인 안 됨",):
                fails += 1        # 차단이 아닌 실패는 세지 않는다
            print("  %3d ✗  %-20s %8s원  %s" % (
                i, r["name"][:20], format(round(r["price"]), ","), why), flush=True)
            if fails >= 3:
                print("!! 연속 3회 실패 — 중단(차단 의심)", flush=True)
                break
        time.sleep(random.uniform(0.8, 1.6))

def _finish(c, res, apply):
    clear_tabs()      # 끝나면 열어둔 탭 전부 정리
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    got = [r for r in res if r["pack_g"]]
    # (한 건씩 이미 반영했다. 여기서는 다시 쓰지 않는다)
    print("", flush=True)
    print("읽음 %d / %d%s → %s" % (len(got), len(res),
                                 "  (DB 반영)" if apply else "  (미반영 — --apply)", OUT), flush=True)


if __name__ == "__main__":
    main()
