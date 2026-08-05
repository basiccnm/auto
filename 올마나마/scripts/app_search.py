# -*- coding: utf-8 -*-
"""식자재 앱 검색 자동화 — 재료명으로 검색해 상시가/쿠폰가를 뽑는다.

🔑 한글 입력 방법 — 이게 이 스크립트의 핵심이다.

  `adb shell input text "양파"` 는 **안 된다.** ASCII만 되고 한글은
  NullPointerException 을 뱉는다. 설치된 IME도 pinyin 하나뿐이라 한글 자판이 없다.

  Windows 클립보드 + KEYCODE_PASTE(279) 도 **믿을 수 없다.** LDPlayer는 창이 포커스를
  받을 때만 클립보드를 게스트로 동기화해서, 창이 뒤에 있으면 **예전 값이 그대로 붙는다**
  (실제로 5건 연속 '대파'로 검색됐다). 매번 포커스를 뺏으면 되지만 사용자가 일을 못 한다.

  → **LDPlayer 자체 명령을 쓴다.** 포커스도 클립보드도 건드리지 않는다:
        ldconsole.exe action --index 0 --key call.input --value "양파"
"""
import subprocess, re, json, io, os, sys, time

LD = r"C:\LDPlayer\LDPlayer14"
ADB = os.path.join(LD, "adb.exe")
LDC = os.path.join(LD, "ldconsole.exe")
DEV = "emulator-5554"
S = os.path.dirname(os.path.abspath(__file__))

BOX_X, BOX_Y = 400, 176      # 검색 입력창
CLR_X, CLR_Y = 666, 176      # 키워드 삭제(X)


def adb(*args, binary=False):
    r = subprocess.run([ADB, "-s", DEV] + list(args), capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def type_ko(word):
    subprocess.run([LDC, "action", "--index", "0", "--key", "call.input",
                    "--value", word], capture_output=True)


def dump():
    adb("shell", "uiautomator", "dump", "/sdcard/q.xml")
    xml = adb("shell", "cat", "/sdcard/q.xml")
    return [t for t in re.findall(r'text="([^"]*)"', xml) if t.strip()]


WON = re.compile(r"[\d,]+원")
PCT = re.compile(r"\d+%")


def parse(texts):
    """상품코드 블록에서 (코드, 이름, 정가, 할인율, 판매가, 쿠폰여부)를 뽑는다.

    ⚠️ 순서로 집으면 틀린다. 카드에 따라 값이 하나 더 끼어든다:
         9,660원 | 2,500원 | 28%     ← 이 경우 '2,500원'은 판매가가 아니다
    할인율(%)을 기준점으로 잡고 **그 바로 앞의 원 = 정가, 바로 뒤의 원 = 판매가**로 읽는다.
    """
    out, i = [], 0
    while i < len(texts) - 3:
        if re.fullmatch(r"C\d{6}(_\d)?", texts[i]):
            code, name = texts[i], texts[i + 1]
            win = texts[i + 2:i + 9]
            coupon = "쿠폰가" in win
            pi = next((j for j, x in enumerate(win) if PCT.fullmatch(x)), None)
            if pi is not None:
                before = [x for x in win[:pi] if WON.fullmatch(x)]
                after = [x for x in win[pi + 1:] if WON.fullmatch(x)]
                if before and after:
                    out.append({"code": code, "name": name, "list": before[-1],
                                "rate": win[pi], "price": after[0], "coupon": coupon})
                    i += 4
                    continue
        i += 1
    return out


def find_total(t):
    for j, x in enumerate(t):
        if x == "총" and j + 1 < len(t) and t[j + 1].isdigit():
            return t[j + 1]
    return ""


def search(word, tries=6):
    adb("shell", "input", "tap", str(CLR_X), str(CLR_Y)); time.sleep(0.7)
    adb("shell", "input", "tap", str(BOX_X), str(BOX_Y)); time.sleep(0.7)
    type_ko(word); time.sleep(0.9)
    adb("shell", "input", "keyevent", "66")
    # 고정 대기 대신 폴링한다. 조건 두 가지를 **둘 다** 만족해야 한다:
    #   ① 총 건수가 그려졌을 것 (인기 검색어는 결과가 많아 렌더가 느리다)
    #   ② 상품 목록이 직전 읽기와 같을 것 — 총 건수만 보면 **앞 검색의 상품이 그대로 남은
    #      화면**을 그대로 읽는다. ('삼겹살'인데 판두부·알배기배추가 잡혔다)
    t, total, prev = [], "", None
    for _ in range(tries):
        time.sleep(1.4)
        t = dump()
        total = find_total(t)
        codes = [x for x in t if re.fullmatch(r"C\d{6}(_\d)?", x)][:5]
        if total and codes and codes == prev:
            break
        prev = codes
    got = t[6] if len(t) > 6 else ""
    items = parse(t)
    # ⚠️ 검색 결과가 0이면 앱이 "추천 상품"을 대신 깔아준다 —
    #    그대로 두면 엉뚱한 상품이 그 재료의 시세로 둔갑한다. 반드시 버릴 것.
    if total in ("", "0"):
        items = []
    return {"kw": word, "typed": got, "total": total, "items": items}


if __name__ == "__main__":
    words = json.loads(io.open(sys.argv[1], encoding="utf-8").read())
    res = []
    for n, w in enumerate(words, 1):
        r = search(w)
        ok = "OK " if r["typed"] == w else "!! "
        print("%s%2d/%d %-14s 총%-5s %d건 파싱" % (ok, n, len(words), w, r["total"], len(r["items"])),
              flush=True)
        res.append(r)
        io.open(os.path.join(S, "app_prices.json"), "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
    print("저장: app_prices.json")
