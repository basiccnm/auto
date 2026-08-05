# -*- coding: utf-8 -*-
"""검색어 갱신 → 홈 재생성 → 배포 를 자동으로. 작업 스케줄러가 3일마다 부른다. (2026-07-31 신설)

    python scripts/auto_gsc_update.py           전체 (갱신 → 생성 → 빌드 → 배포 → 퍼지)
    python scripts/auto_gsc_update.py --dry     무엇을 할지만 보고 아무것도 안 함
    python scripts/auto_gsc_update.py --no-deploy   생성까지만 (배포 안 함)

🔴 **왜 배포까지 하나**
   `gsc_keywords.py` 만 돌리면 JSON 만 바뀌고 화면은 그대로다. 홈 우측 「많이 찾는 검색어」는
   **페이지를 다시 만들어야** 반영된다. 그래서 배포까지 한 묶음으로 돈다.

🔴 **왜 3일인가**
   서치콘솔이 2~3일 지연이라 더 자주 돌려도 값이 안 바뀐다(대표 지시 2026-07-31).

🔴 **왜 새벽인가 — 빌드 충돌**
   `build_dist` 가 두 개 동시에 돌면 `_dist` 가 무너진다(2026-07-31에 실제로 두 번, 파일 1개까지 떨어졌다).
   사람이 안 만지는 시간에 돌려야 한다. 그래도 `deploy.py` 의 파일 수 검사가 마지막 방어선이다.

🔴 로그는 `logs/auto_gsc_YYYY-MM.log` 에 쌓인다. 실패해도 조용히 죽지 않게 전부 남긴다.
"""
import argparse
import io
import os
import subprocess
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(BASE, "logs")
sys.stdout.reconfigure(encoding="utf-8")

# 🔴 **`"python"` 이라고 쓰지 말 것 — `sys.executable` 을 쓴다.**
#    작업 스케줄러에서 돌면 PATH 가 달라 다른 파이썬이 잡힌다. 실제로 2026-07-31에
#    스케줄러가 부른 python 에서 `pyparsing has no attribute 'DelimitedList'` 로 죽었다
#    (httplib2 와 버전이 안 맞는 다른 설치본이었다). 손으로 돌릴 땐 멀쩡해서 더 헷갈린다.
PY = sys.executable

# 순서가 중요하다 — 검색어를 받아야 홈에 넣을 게 생기고, 만들어야 배포할 게 생긴다
STEPS = [
    ("검색어 갱신", [PY, "scripts/gsc_keywords.py"]),
    ("홈·전체 재생성", [PY, "scripts/gen_preview_html.py"]),
    ("_dist 빌드", [PY, "scripts/build_dist.py"]),
    ("배포", [PY, "scripts/deploy.py"]),
    # 홈은 빈 경로여야 지워진다 — index.html 로는 안 지워진다(2026-07-31 확인)
    ("캐시 퍼지", [PY, "scripts/cf_purge.py", ""]),
]


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    os.makedirs(LOGDIR, exist_ok=True)
    p = os.path.join(LOGDIR, "auto_gsc_%s.log" % datetime.now().strftime("%Y-%m"))
    with io.open(p, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-deploy", action="store_true", help="생성까지만")
    a = ap.parse_args()

    steps = STEPS[:2] if a.no_deploy else STEPS
    log("=" * 56)
    log("자동 갱신 시작 (%d단계)" % len(steps))

    if a.dry:
        for n, c in steps:
            log("  [예정] %s — %s" % (n, " ".join(c)))
        return 0

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for name, cmd in steps:
        log("── %s" % name)
        r = subprocess.run(cmd, cwd=BASE, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = [x for x in (r.stdout or "").strip().split("\n") if x.strip()][-4:]
        for t in tail:
            log("   " + t[:160])
        if r.returncode != 0:
            err = (r.stderr or "").strip().split("\n")[-3:]
            for e in err:
                log("   ! " + e[:160])
            log("❌ %s 에서 멈춤 (코드 %d) — 뒷단계는 건너뛴다" % (name, r.returncode))
            return 1

    log("✅ 전부 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
