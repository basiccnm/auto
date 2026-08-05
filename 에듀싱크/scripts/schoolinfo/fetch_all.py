"""학교알리미 학교정보 전국 수집 — sgg_codes.json의 256개 시군구 × 초/중/고 순회.

fetch_details.main()을 지역별로 반복 호출한다. 전국 768회(256×3) 호출이라 수십 분 걸리므로:
  - 진행상황을 progress 파일에 기록 → 중단해도 이어받기(--resume)
  - 호출 간 간격을 둬서 서버 부담·차단 위험 최소화(축평원 WAF 차단 전례)
  - 한 지역이 실패해도 전체가 죽지 않게 개별 try

사용 예:
    python fetch_all.py auto              # 전국 전 학교급 (이어받기 자동)
    python fetch_all.py auto --sido 11    # 서울만
    python fetch_all.py auto --restart    # 진행파일 무시하고 처음부터
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fetch_details import main as fetch_one, current_school_year

ROOT = Path(__file__).resolve().parent.parent.parent
CODES = ROOT / "scripts" / "sgg_codes.json"
PROGRESS = ROOT / "scripts" / ".fetch_all_progress.json"
KINDS = ["02", "03", "04"]  # 초/중/고
KIND_LABEL = {"02": "초", "03": "중", "04": "고"}
SLEEP_SEC = 0.6  # 지역·학교급 사이 간격


def load_progress(restart):
    if restart or not PROGRESS.exists():
        return set()
    try:
        return set(json.loads(PROGRESS.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_progress(done):
    PROGRESS.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")


def run(pban_yr, only_sido=None, restart=False):
    codes = json.loads(CODES.read_text(encoding="utf-8"))
    if only_sido:
        codes = [c for c in codes if c["sido_code"] == only_sido]
    done = load_progress(restart)

    tasks = [(c, k) for c in codes for k in KINDS]
    todo = [(c, k) for c, k in tasks if f"{c['sgg_code']}-{k}" not in done]
    print(f"대상: {len(codes)}개 시군구 × {len(KINDS)}개 학교급 = {len(tasks)}건")
    print(f"완료: {len(done)}건 / 남음: {len(todo)}건\n")

    failed = []
    for i, (c, kind) in enumerate(todo, 1):
        tag = f"{c['sgg_code']}-{kind}"
        label = f"[{i}/{len(todo)}] {c['sido']} {c['sgg']} {KIND_LABEL[kind]}"
        try:
            print(f"{label} ...")
            fetch_one(pban_yr, kind, c["sido_code"], c["sgg_code"])
            done.add(tag)
            save_progress(done)
        except Exception as e:
            # 지역 단위 실패는 기록만 하고 계속 — 나중에 --resume으로 재시도
            print(f"  [실패] {label}: {e}")
            failed.append((tag, str(e)[:80]))
        time.sleep(SLEEP_SEC)

    print(f"\n=== 종료: 성공 {len(done)}건, 실패 {len(failed)}건 ===")
    if failed:
        print("실패 목록(재실행하면 자동 재시도):")
        for tag, err in failed[:20]:
            print(f"  {tag}: {err}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    yr = current_school_year() if sys.argv[1] == "auto" else sys.argv[1]
    sido = None
    if "--sido" in sys.argv:
        sido = sys.argv[sys.argv.index("--sido") + 1]
    run(yr, only_sido=sido, restart="--restart" in sys.argv)
