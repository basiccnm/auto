# -*- coding: utf-8 -*-
"""로그인된 안드로이드 주문 앱의 «메뉴 화면»에서 카테고리·메뉴명·가격을 읽는 범용 모듈.

원본은 여기(공통모듈). 프로젝트에서는 **복사해서** 쓴다(CLAUDE.md 방침).

읽는 방식은 앱마다 셋 중 하나 — 이 모듈이 **자동 판정**한다:
  ① uiautomator 에 글자가 잡힘   → 텍스트 노드 직접(제일 싸고 정확). 이디야·공차·투썸
  ② 글자 0 이지만 웹뷰 DevTools 열림 → DOM innerText (미구현 훅만)
  ③ 글자 0 · DevTools 잠김(캔버스) → 스크린샷 OCR 필요(이 모듈 범위 밖)

⛔ 앱의 로그인 토큰을 꺼내지 않는다. 화면에 이미 그려진 것만 읽는다.
⛔ 장바구니·주문·결제·매장변경 버튼은 누르지 않는다.

사람이 앱을 «매장 선택 끝난 메뉴 목록» 화면에 띄운 상태에서 실행한다.

사용 (래퍼에서):
    r = AppMenuReader("127.0.0.1:5555")
    method = r.detect()                    # 'uiauto' / 'devtools' / 'canvas'
    data = r.collect(tops=None)            # {카테고리경로: [{name, price}, ...]}
"""
import re
import subprocess
import time

ADB_DEFAULT = r"D:\Android\Sdk\platform-tools\adb.exe"
RX_WON = re.compile(r"^([\d]{1,3}(?:,[\d]{3})*)\s*원$")
RX_WON_INLINE = re.compile(r"([\d]{1,3}(?:,[\d]{3})+)\s*원")
# 메뉴가 아닌 UI 글자(범용). 브랜드별 추가는 래퍼에서 skip 로 넘긴다.
UI_NOISE = {"매장주문", "변경", "장바구니", "전체", "더보기", "닫기", "검색", "0",
            "메인으로 가기", "뒤로가기", "나만의 메뉴", "목록", "홈", "주문", "결제",
            "담기", "선택", "추가", "옵션"}
BADGE = re.compile(r"^(ICED Only|HOT Only|ICED|HOT|NEW|BEST|품절|이벤트|New|Best|"
                   r"신메뉴|추천|인기|1\+1)$", re.I)


class AppMenuReader:
    def __init__(self, device, adb=ADB_DEFAULT):
        self.dev = device
        self.adb = adb

    # ── adb 기본 ────────────────────────────────────────────
    def sh(self, *a, t=60):
        return subprocess.run([self.adb, "-s", self.dev, *a],
                              capture_output=True, timeout=t)

    def dump(self):
        self.sh("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        return self.sh("shell", "cat", "/sdcard/ui.xml").stdout.decode("utf-8", "replace")

    def nodes(self):
        """(글자, 중심x, 중심y) 목록. 화면 순서 유지. base64/빈 값 제외."""
        x = self.dump()
        out = []
        for m in re.finditer(
                r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
            t = m.group(1).replace("&amp;", "&").strip()
            if not t or len(t) > 70 or t.startswith("&#"):
                continue
            if re.fullmatch(r"[A-Za-z0-9+/=]{20,}", t):     # base64 조각
                continue
            out.append((t, (int(m.group(2)) + int(m.group(4))) // 2,
                        (int(m.group(3)) + int(m.group(5))) // 2))
        return out

    def webview_socket(self):
        x = self.sh("shell", "cat", "/proc/net/unix").stdout.decode("utf-8", "replace")
        m = re.findall(r"webview_devtools_remote_\d+", x)
        return m[0] if m else None

    # ── 방식 판정 ───────────────────────────────────────────
    def detect(self):
        ns = self.nodes()
        n_text = len([t for t, _, _ in ns if len(t) >= 2])
        n_price = len([t for t, _, _ in ns
                       if RX_WON.match(t) or RX_WON_INLINE.search(t)])
        if n_text >= 8:
            return "uiauto"                 # 글자 잡힘 — 제일 쌈
        if self.webview_socket():
            return "devtools"               # 캔버스지만 DOM 시도 가능
        return "canvas"                     # OCR 필요

    # ── 제스처 ──────────────────────────────────────────────
    def tap(self, cx, cy, wait=2.6):
        self.sh("shell", "input", "tap", str(cx), str(cy))
        time.sleep(wait)

    def to_top(self):
        for _ in range(5):
            self.sh("shell", "input", "swipe", "450", "560", "450", "1450", "260")
            time.sleep(0.45)

    def swipe_up(self):
        self.sh("shell", "input", "swipe", "450", "1350", "450", "560", "420")
        time.sleep(1.1)

    def chip_scroll_left(self, y):
        self.sh("shell", "input", "swipe", "150", str(y), "850", str(y), "300")
        time.sleep(0.55)

    def chip_scroll_right(self, y):
        self.sh("shell", "input", "swipe", "820", str(y), "150", str(y), "350")
        time.sleep(0.55)

    # ── 탭 자동 발견 ────────────────────────────────────────
    def find(self, ns, name):
        return [n for n in ns if n[0] == name]

    def top_tabs(self, ns):
        """화면 상단(y<520)의 짧은 탭 후보를 좌→우 순서로. 브랜드별 지정이 없을 때."""
        band = [(t, cx, cy) for t, cx, cy in ns
                if cy < 520 and 1 <= len(t) <= 12 and t not in UI_NOISE
                and not RX_WON.match(t) and not t.isdigit()]
        if not band:
            return []
        # 가장 촘촘한 y 줄 하나 = 탭 줄
        band.sort(key=lambda n: n[2])
        rows = {}
        for t, cx, cy in band:
            key = min(rows, key=lambda k: abs(k - cy)) if rows else cy
            if not rows or abs(key - cy) > 35:
                rows[cy] = []
                key = cy
            rows[key].append((t, cx, cy))
        best = max(rows.values(), key=len)
        return [t for t, cx, cy in sorted(best, key=lambda n: n[1])]

    def sub_row(self, ns, top_y):
        """메인탭 아래 40~150px 밴드의 하위칩(좌→우)."""
        band = [(t, cx, cy) for t, cx, cy in ns
                if top_y + 40 <= cy <= top_y + 150 and t not in UI_NOISE
                and len(t) >= 1 and not RX_WON.match(t) and not t.isdigit()]
        return sorted(band, key=lambda n: n[1])

    # ── 수집 ────────────────────────────────────────────────
    def harvest(self, ns, bag, order, y0, skip):
        """y0(카드영역 시작) 아래에서 가격줄 기준으로 «같은 x열 위쪽 이름»을 잇는다.
        인라인('아메리카노 4,500원')도 처리."""
        cards = [(t, cx, cy) for t, cx, cy in ns if cy > y0]
        # 1) 인라인
        for t, cx, cy in cards:
            mi = RX_WON_INLINE.search(t)
            if mi and not RX_WON.match(t):
                nm = t[:mi.start()].strip(" ·")
                if len(nm) >= 2 and nm not in bag and nm not in skip:
                    bag[nm] = int(mi.group(1).replace(",", ""))
                    order.append(nm)
        # 2) 이름/가격 분리형(그리드)
        for t, cx, cy in cards:
            m = RX_WON.match(t)
            if not m:
                continue
            price = int(m.group(1).replace(",", ""))
            cand = [(c[2], c[0]) for c in cards
                    if abs(c[1] - cx) <= 70 and c[2] < cy
                    and not RX_WON.match(c[0]) and not RX_WON_INLINE.search(c[0])
                    and not BADGE.match(c[0]) and c[0] not in UI_NOISE
                    and c[0] not in skip and len(c[0]) >= 2]
            if cand:
                name = max(cand)[1]         # 가장 가까운 위쪽 줄
                if name not in bag:
                    bag[name] = price
                    order.append(name)

    def scroll_collect(self, top_name, skip, y_pad=170, max_scroll=60):
        bag, order, same = {}, [], 0
        for _ in range(max_scroll):
            ns = self.nodes()
            pos = self.find(ns, top_name)
            top_y = pos[0][1] if pos else 379
            before = len(bag)
            self.harvest(ns, bag, order, top_y + y_pad, skip)
            if len(bag) == before:
                same += 1
                if same >= 3:
                    break
            else:
                same = 0
            self.swipe_up()
        return [{"name": n, "price": bag[n]} for n in order]

    def collect(self, tops=None, skip=None):
        """{카테고리경로: [{name, price}]}. tops 미지정 시 상단에서 자동 발견."""
        skip = set(skip or []) | UI_NOISE
        if not tops:
            self.to_top()
            tops = self.top_tabs(self.nodes())
        skip |= set(tops)
        result = {}
        for top in tops:
            self.to_top()
            pos = self.find(self.nodes(), top)
            if not pos:
                result["__miss__/" + top] = []
                continue
            self.tap(pos[0][1], pos[0][2])
            ns = self.nodes()
            pos = self.find(ns, top) or pos
            top_y = pos[0][1]

            # 하위칩 전량 발견(가로 스크롤)
            subs, seen = [], set()
            for _ in range(8):
                for t, cx, cy in self.sub_row(self.nodes(), top_y):
                    if t not in seen:
                        seen.add(t)
                        subs.append(t)
                self.chip_scroll_right(top_y + 90)
                if all(t in seen for t, _, _ in self.sub_row(self.nodes(), top_y)):
                    break
            sk = skip | seen

            if not subs:
                result[top] = self.scroll_collect(top, sk)
                continue
            for sub in subs:
                self.to_top()
                # 칩 왼쪽 끝으로 되돌린 뒤 찾는다(오른쪽까지 밀렸을 수 있음)
                pos = self.find(self.nodes(), top)
                ty = pos[0][1] if pos else top_y
                for _ in range(3):
                    self.chip_scroll_left(ty + 90)
                found = None
                for _ in range(6):
                    ns = self.nodes()
                    pos = self.find(ns, top)
                    ty = pos[0][1] if pos else ty
                    hit = [n for n in self.sub_row(ns, ty) if n[0] == sub]
                    if hit:
                        found = hit[0]
                        break
                    self.chip_scroll_right(ty + 90)
                if not found:
                    result["%s/%s" % (top, sub)] = []
                    continue
                self.tap(found[1], found[2])
                result["%s/%s" % (top, sub)] = self.scroll_collect(top, sk)
        return result
