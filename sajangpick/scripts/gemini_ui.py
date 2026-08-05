# -*- coding: utf-8 -*-
"""gemini_ui.py — 에뮬레이터 제미나이 앱을 좌표가 아니라 **이름으로** 조작한다.

왜 필요한가
    지금까지 전송·메뉴를 화면 좌표(1761,989 / 1499,989 ...)로 눌렀는데,
    사이드바가 접히거나 창 크기가 바뀌면 좌표가 통째로 어긋났다.
    실제로 요청09 는 좌표가 밀려 전송이 안 된 채 대기했다(2026-08-02).
    → uiautomator 의 content-desc 로 버튼을 찾아 그 중심을 누른다.

확인된 content-desc (2026-08-02 실측)
    보내기 · 옵션 더보기 · 복사 · 듣기 · 새 채팅 · 사이드바 열기 · 첨부파일 추가
    대답이 마음에 들어요 / 들지 않아요 · 옵션 다시 실행 · 마이크 · 대화 목록

쓰는 법
    python gemini_ui.py send                 # 입력창 내용 전송
    python gemini_ui.py export               # 마지막 답변을 구글 문서로 내보내기
    python gemini_ui.py tap "옵션 더보기"      # 이름으로 아무거나 누르기
"""
import re
import subprocess
import sys
import time

ADB = r"C:\LDPlayer\LDPlayer14\adb.exe"
DEV = "127.0.0.1:5555"


def sh(*args):
    return subprocess.run([ADB, "-s", DEV, "shell", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def dump():
    sh("uiautomator", "dump", "//sdcard/ui.xml")
    return sh("cat", "//sdcard/ui.xml").stdout


def find(desc, xml=None, last=True):
    """content-desc 또는 text 가 desc 인 노드의 중심 좌표. 없으면 None.

    last=True 면 **화면에서 가장 아래** 것을 고른다.
    ⚠ XML 순서로 마지막을 고르면 안 된다 — 「옵션 더보기」는 상단 앱바에도 있어서
      XML 마지막이 앱바 버튼(y≈98)으로 잡힌다(2026-08-02 실측).
      우리가 원하는 건 항상 **최신 답변 밑의** 버튼이라 y 가 가장 큰 것이 맞다.
    """
    xml = xml if xml is not None else dump()
    hits = []
    for node in xml.split("<node")[1:]:
        if f'content-desc="{desc}"' not in node and f'text="{desc}"' not in node:
            continue
        m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            hits.append(((x1 + x2) // 2, (y1 + y2) // 2))
    if not hits:
        return None
    hits.sort(key=lambda p: p[1])          # y 오름차순
    return hits[-1] if last else hits[0]


def tap(desc, wait=1.5, last=True):
    p = find(desc, last=last)
    if not p:
        print(f"못 찾음: {desc}")
        return False
    sh("input", "tap", str(p[0]), str(p[1]))
    time.sleep(wait)
    print(f"눌렀음: {desc} @ {p}")
    return True


def export_last():
    """마지막 답변을 구글 문서로 내보낸다.

    제미나이가 「저장했다」고 해놓고 실제로는 드라이브에 안 만들 때가 있다
    (2026-08-02 REPLY09). 그때 쓰는 확실한 우회로다.
    이 메뉴는 앱 기능이라 모델이 뭐라 하든 항상 동작한다.
    """
    if not tap("옵션 더보기", wait=2):
        return False
    # 메뉴 항목은 text 로 잡힌다
    for label in ("Docs로 내보내기", "Google Docs로 내보내기", "문서로 내보내기"):
        if tap(label, wait=3, last=False):
            return True
    print("내보내기 항목을 못 찾음 — 메뉴 문구가 바뀐 듯하다. 화면을 확인할 것")
    return False


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "send"
    if cmd == "send":
        tap("보내기")
    elif cmd == "export":
        export_last()
    elif cmd == "tap":
        tap(sys.argv[2])
    else:
        print(__doc__)
