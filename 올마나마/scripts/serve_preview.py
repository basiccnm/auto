# -*- coding: utf-8 -*-
# 로컬 프리뷰 서버 (포트 8792) — 확장자 없는 주소 지원 (2026-07-19)
#
#  왜: 정식 URL을 /menu_6 처럼 확장자 없이 통일했는데(라이브 Cloudflare Assets가 이렇게 서빙),
#      python -m http.server 는 /menu_6 을 404로 낸다 → 로컬에서 링크 클릭이 다 깨짐.
#      이 서버는 /menu_6 → menu_6.html 로 매핑해 라이브와 동일하게 동작한다.
#
#  사용법: python scripts/serve_preview.py   (기본 127.0.0.1:8792, _preview 서빙)
import http.server, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "_preview")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8792


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def translate_path(self, path):
        # /menu_6 → menu_6.html (라이브 auto-trailing-slash와 동일 규칙)
        p = super().translate_path(path)
        if not os.path.exists(p) and "." not in os.path.basename(p) and os.path.isfile(p + ".html"):
            return p + ".html"
        return p

    def log_message(self, *a):
        pass  # 조용히


if __name__ == "__main__":
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H) as srv:
        print(f"프리뷰: http://127.0.0.1:{PORT}  (확장자 없는 주소 → .html 매핑)")
        srv.serve_forever()
