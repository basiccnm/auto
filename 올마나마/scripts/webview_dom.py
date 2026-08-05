# -*- coding: utf-8 -*-
"""webview_dom — 안드로이드 Chrome/웹뷰의 렌더된 DOM 을 DevTools 로 읽는다.

토큰을 꺼내지 않는다 — 앱/브라우저가 **이미 렌더한 화면**의 innerText·페이지 전역데이터를
Runtime.evaluate 로 읽을 뿐이다. 네이버 플레이스 `__APOLLO_STATE__`(매장 등록 메뉴가) 나
스마트오더 화면 등 «화면엔 있는데 API 는 못 뚫는» 값을 가져올 때 쓴다.

의존성 0 (표준 라이브러리만). adb 경로만 있으면 된다.

CLI:
    python webview_dom.py <device> [출력파일] [--expr "JS식"]
      device  : "127.0.0.1:5555"(에뮬) / "172.30.1.35:40241"(폰) 등
      기본 동작: 첫 page 타깃의 document.body.innerText 를 저장
      --expr   : 대신 실행할 JS (예: 'JSON.stringify(window.__APOLLO_STATE__)')

import:
    from webview_dom import WebviewDOM
    w = WebviewDOM("127.0.0.1:5555")           # 자동으로 chrome_devtools_remote 우선
    txt   = w.body_text()                       # 화면 전체 innerText
    state = w.apollo_state()                    # __APOLLO_STATE__ (dict) 또는 None
    val   = w.evaluate("document.title")        # 임의 JS 한 줄

⚠️ 앱 로그인 토큰 추출·보안설정 변경 금지. **DOM 읽기 전용**이다.
"""
import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

ADB_DEFAULT = r"D:\Android\Sdk\platform-tools\adb.exe"


class WebviewDOM:
    def __init__(self, device, adb=ADB_DEFAULT, port=9333, socket_name=None):
        self.device = device
        self.adb = adb
        self.port = port
        self.socket_name = socket_name   # None 이면 자동 탐지

    # ---- adb ----
    def _sh(self, *a, t=60):
        return subprocess.run([self.adb, "-s", self.device, *a],
                              capture_output=True, timeout=t)

    def find_socket(self):
        """DevTools 유닉스 소켓 이름을 찾는다. Chrome=chrome_devtools_remote,
        웹뷰=webview_devtools_remote_<pid>. Chrome 을 우선한다."""
        x = self._sh("shell", "cat", "/proc/net/unix").stdout.decode("utf-8", "replace")
        socks = re.findall(r"(chrome_devtools_remote|webview_devtools_remote_\d+)", x)
        if not socks:
            return None
        for s in socks:                       # Chrome 우선
            if s == "chrome_devtools_remote":
                return s
        return socks[0]

    def _forward(self):
        sock = self.socket_name or self.find_socket()
        if not sock:
            raise RuntimeError("DevTools 소켓 없음 — 앱이 웹뷰/Chrome 화면이 아니거나 USB디버깅 꺼짐")
        subprocess.run([self.adb, "forward", "--remove-all"], capture_output=True)
        self._sh("forward", "tcp:%d" % self.port, "localabstract:%s" % sock)
        time.sleep(0.5)
        return sock

    # ---- DevTools HTTP ----
    def _http(self, path):
        r = urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                   headers={"Host": "localhost"}), timeout=12)
        return r.read().decode("utf-8", "replace")

    def _pages(self):
        for p in ("/json/list", "/json"):
            try:
                txt = self._http(p)
            except Exception:
                continue
            try:
                arr = json.loads(txt)
            except Exception:
                continue
            pages = [x for x in arr if x.get("type") == "page" and x.get("webSocketDebuggerUrl")]
            if pages:
                return pages
        return []

    # ---- 미니 WebSocket 클라이언트 (Runtime.evaluate 한 번) ----
    @staticmethod
    def _ws_eval(ws_url, expr):
        m = re.match(r"ws://([^:/]+):(\d+)(/.*)", ws_url)
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        s = socket.create_connection((host, port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        s.send(("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
                "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key)).encode())
        time.sleep(0.3)
        s.recv(4096)  # 핸드셰이크 응답
        msg = json.dumps({"id": 1, "method": "Runtime.evaluate",
                          "params": {"expression": expr, "returnByValue": True}}).encode()
        mask = os.urandom(4)
        ln = len(msg)
        hdr = bytearray([0x81])
        if ln < 126:
            hdr.append(0x80 | ln)
        elif ln < 65536:
            hdr += bytes([0x80 | 126, ln >> 8 & 255, ln & 255])
        else:
            hdr += bytes([0x80 | 127]) + ln.to_bytes(8, "big")
        hdr += mask
        s.send(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(msg)))
        buf = b""
        s.settimeout(15)
        for _ in range(400):
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if b'"id":1' in buf and buf.rstrip().endswith(b"}"):
                break
        s.close()
        out, i = b"", 0
        while i < len(buf):
            b2 = buf[i + 1]; ln = b2 & 127; i += 2
            if ln == 126:
                ln = int.from_bytes(buf[i:i + 2], "big"); i += 2
            elif ln == 127:
                ln = int.from_bytes(buf[i:i + 8], "big"); i += 8
            out += buf[i:i + ln]; i += ln
        try:
            return json.loads(out.decode("utf-8", "replace").split("\x00")[0])
        except Exception:
            return {"raw": out[:500].decode("utf-8", "replace")}

    # ---- 공개 API ----
    def evaluate(self, expr, page_index=0):
        """현재 화면의 첫 page(또는 page_index) 에서 JS 한 줄을 실행하고 값(returnByValue)을 돌려준다."""
        self._forward()
        pages = self._pages()
        if not pages:
            raise RuntimeError("DevTools page 타깃 없음 — 대상 화면에 들어가 있는지 확인")
        p = pages[min(page_index, len(pages) - 1)]
        r = self._ws_eval(p["webSocketDebuggerUrl"], expr)
        return ((r.get("result") or {}).get("result") or {}).get("value") if isinstance(r, dict) else None

    def body_text(self, limit=200000, page_index=0):
        return self.evaluate(
            "(function(){var t=document.body?document.body.innerText:'';return t.slice(0,%d);})()"
            % limit, page_index)

    def apollo_state(self, page_index=0):
        """네이버 플레이스 등의 window.__APOLLO_STATE__ 를 dict 로. 없으면 None."""
        raw = self.evaluate(
            "(function(){try{return JSON.stringify(window.__APOLLO_STATE__||null)}catch(e){return null}})()",
            page_index)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def page_url(self, page_index=0):
        pages = self._pages()
        return (pages[page_index].get("url") if pages else "") or ""


def _main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("사용: python webview_dom.py <device> [출력파일] [--expr \"JS\"]"); return
    dev = sys.argv[1]
    out = None
    expr = None
    rest = sys.argv[2:]
    if "--expr" in rest:
        i = rest.index("--expr")
        expr = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    if rest:
        out = rest[0]
    w = WebviewDOM(dev)
    try:
        val = w.evaluate(expr) if expr else w.body_text()
    except Exception as e:
        print("🔴", e); return
    if val is None:
        print("🔴 값이 비었음 (화면/식 확인)"); return
    txt = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(txt)
        prices = re.findall(r"[\d]{1,3}(?:,[\d]{3})+\s*원?", txt)
        print("✅ %d자 저장 → %s · 가격패턴 %d개" % (len(txt), out, len(prices)))
        print("앞부분:\n", txt[:500])
    else:
        print(txt[:2000])


if __name__ == "__main__":
    _main()
