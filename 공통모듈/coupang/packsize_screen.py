# -*- coding: utf-8 -*-
"""쿠팡 상품 **용량**을 화면에서 읽는다 — 안드로이드 크롬 + uiautomator. (2026-08-02 공통모듈 편입)

🔴 **왜 화면인가 — 다른 경로가 다 막혔다**
   · 쿠팡 파트너스 API : 용량 필드를 안 준다. 상품명에 적힌 것만 나온다
   · WebFetch / curl   : `403 Forbidden` (Akamai 가 브라우저 아닌 요청을 막는다)
   · in-app 브라우저    : 정책상 coupang.com 차단
   · 쿠팡 **앱**        : 로딩이 안 끝나 uiautomator 가 idle 을 못 얻는다
   ✅ **안드로이드 크롬**(실기기·에뮬레이터 둘 다) — 이것만 열린다

🔴 **에뮬레이터도 된다**(2026-08-02 확인). 옛 주석에 「에뮬은 차단」이라고 **뭉뚱그려**
   적혀 있어서 이 경로를 6일간 안 썼다. 막힌 건 **쿠팡 앱**이고 **크롬은 정상**이다.
   LDPlayer + `com.android.chrome` 으로 75건을 읽었고 차단은 한 번도 없었다.

🔴 **크롬 컴포넌트를 `-n` 으로 직접 지정한다.** 안 그러면 안드로이드 앱링크가
   coupang.com 을 **쿠팡 앱으로 넘겨버린다**(실제로 그렇게 앱이 떴다).

🔴 **상품을 바꾸지 않는다.** `product_id` 는 그대로 두고 용량만 읽는다.
   자동으로 상품을 다시 고르면 다른 물건이 붙는다(포마스 혼합유·리코타 치즈·알룰로스).

🔴 **남의 페이지를 읽지 않게 상품명을 검사한다.** 상품 페이지엔 추천 상품이 잔뜩 섞여 있다.
   ⚠️ 「하나라도 겹치면 통과」로 두면 **브랜드명 두 글자로 뚫린다** —
      「곰곰 저당 시저 드레싱」 자리에 「곰곰 냉동 애플망고」가 붙었다(2026-08-02).
      그래서 `STOP_TOK`(곰곰·로켓프레시·초특가…)을 빼고 **2개 이상** 겹치게 했다.

## 쓰는 법

```python
from packsize_screen import read_pack, set_device
set_device("emulator-5556")            # 생략하면 adb devices 첫 기기
kg, why = read_pack(8085593611, "곰곰 저당 시저 드레싱", 2850)
#   → (0.235, "상품명: 곰곰 저당 시저 드레싱, 235g, 1개")
#   → (None, "용량 표기 없음(스크롤12)") · (None, "차단")
```

⚠️ **속도는 1건당 6초.** 3초로 돌렸다가 11건에서 차단됐다(2026-07-27). 연속 3회 실패면 멈출 것.
⚠️ 호출부가 **한 건 읽을 때마다 저장**해야 한다. 마지막에 몰아 저장하면 끊길 때 다 날아간다.
"""
import os
import re
import subprocess
import time

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


def set_device(serial):
    """쓸 기기를 바꾼다. `adb devices` 의 serial (예: emulator-5556)."""
    global DEV
    DEV = serial


def read_pack(product_id, our_name, price):
    """상품 페이지를 열어 **총 중량(kg)** 을 읽는다. (kg, 근거) 튜플.

    못 읽으면 (None, 이유). 이유가 "차단" 이면 **즉시 멈출 것** — 계속 두드리면 IP 가 막힌다.
    """
    return read_one(product_id, our_name, price)
