# 앱 목업 서버 (8789) — 창 없이 도는 버전.
# 왜 이 파일인가: pythonw로 `http.server`를 그냥 돌리면 요청 로그를 쓸 콘솔이 없어서
# 요청마다 핸들러가 죽는다(2026-07-24 실측 — 리스너는 있는데 연결이 끊기던 원인).
# → 로그를 아예 안 쓰는 핸들러로 돌린다. 더블클릭해도 창이 안 뜬다.
# 종료: 작업관리자에서 pythonw 종료, 또는 스케줄러 작업("에듀싱크목업8789") 삭제.
import os
import socketserver
from http.server import SimpleHTTPRequestHandler

WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
PORT = 8789


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # 콘솔이 없으므로 어떤 로그도 쓰지 않는다
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


os.chdir(WWW)
try:
    Server(("0.0.0.0", PORT), Quiet).serve_forever()
except OSError:
    pass  # 이미 떠 있음(포트 사용 중) — 중복 기동이면 조용히 물러난다(스케줄러가 5분마다 부르므로 정상)
