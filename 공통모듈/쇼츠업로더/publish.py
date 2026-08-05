# -*- coding: utf-8 -*-
"""쇼츠 한 편을 유튜브·틱톡·인스타에 **한 줄로** 올린다. (2026-07-31 신설)

    python publish.py --id <편id>                 미리보기 (아무것도 안 올림)
    python publish.py --id <편id> --go            실제 업로드 (3곳 전부)
    python publish.py --id <편id> --go --only yt  유튜브만
    python publish.py --id <편id> --go --skip ig  인스타만 빼고

🔴 **왜 만들었나 (2026-07-31 대표 지시)**
   편마다 사람이 3개 명령을 따로 조립하고 있었다. 절차는 매번 똑같은데 그걸
   매번 다시 짜느라 시간·토큰이 나갔다. **내용(제목·설명·댓글)은 사람이 쓰고,
   올리는 절차는 이 스크립트가 한다** — 그게 이 파일의 존재 이유다.

🔴 **큐는 queue.json 하나만 쓴다.**
   전엔 queue.json(유튜브·틱톡) + queue_reels.json(인스타) 둘로 나뉘어 있어서
   같은 편의 문구를 두 군데 각각 적어야 했다. 이제 queue.json 에 `ig` 블록을 두고,
   이 스크립트가 실행 시점에 queue_reels.json 을 **자동으로 만들어 준다.**
   (post_ig_reel.py 를 안 고치려고 이렇게 했다 — 검증된 스크립트는 건드리지 않는다)

🔴 **인스타는 로컬 파일을 못 받는다.** mp4 가 공개 HTTPS 주소에 있어야 한다.
   그래서 인스타를 올릴 땐 «영상 복사 → 사이트 빌드 → 배포» 가 먼저 돈다.
   이 세 단계는 프로젝트마다 다르므로 `publish_config.json` 으로 뺐다.

🔴 **손으로 남는 것 2개** — 스크립트가 못 한다:
     · 유튜브 첫 댓글 «고정» (API에 그 기능이 없다)
     · 인스타 첫 댓글 «고정» (폰에서만 된다)

── queue.json 항목 형식 ────────────────────────────────────────────────
{
  "id": "순대국1",
  "brand": "이거 얼마남아 6 — 순대국 한 그릇",
  "file_yt": "../업로드/순대국1편_한그릇/순대국1편_한그릇.mp4",
  "title": "...", "desc": "...", "desc_tt": "...", "comment": "...",
  "tags": [...],
  "playlist": "음식 원가 해부",          // 없으면 제목으로 판별
  "ig": {                                // 인스타용. 없으면 인스타는 건너뛴다
    "slug": "keunmam-1",                 // https://<site>/reels/<slug>.mp4
    "caption": "...",                    // 없으면 desc_tt 를 쓴다
    "comment": "...",                    // 없으면 comment 를 쓴다
    "tags": [...]                        // 없으면 tags 를 쓴다
  },
  "status": {"yt": "", "tt": "", "ig": "", "nv": "skip"}
}
"""
import argparse
import json
import io
import os
import shutil
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue.json")
QUEUE_REELS = os.path.join(HERE, "queue_reels.json")
CONFIG = os.path.join(HERE, "publish_config.json")
sys.stdout.reconfigure(encoding="utf-8")

ORDER = ["yt", "tt", "ig"]
NAME = {"yt": "유튜브", "tt": "틱톡", "ig": "인스타"}


def log(msg):
    print("[{}] {}".format(datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def load(path):
    return json.loads(io.open(path, encoding="utf-8").read())


def save(path, data):
    io.open(path, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))


def cfg():
    """프로젝트마다 다른 것만 여기 있다. 없으면 인스타는 못 올린다(다른 곳은 됨)."""
    if not os.path.exists(CONFIG):
        return {}
    return load(CONFIG)


def run(cmd, cwd=None):
    """자식 프로세스를 그대로 흘려보낸다. 출력이 실시간으로 보여야 어디서 막혔는지 안다.

    🔴 **PYTHONIOENCODING=utf-8 을 강제한다.** 안 하면 윈도우 콘솔(cp949)에서
       이모지·«—» 하나에 UnicodeEncodeError 로 죽는다(2026-07-29 실제로 당함).
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    log("$ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, env=env)
    return r.returncode == 0


# ── 인스타 준비 — 영상을 공개 주소에 올린다 ─────────────────────────────────
def prepare_ig(item, c):
    """mp4 를 사이트로 복사하고 빌드·배포한다. 성공하면 공개 URL 을 돌려준다.

    🔴 인스타 Graph API 는 **로컬 파일을 안 받는다.** 공개 HTTPS 주소만 받는다.
       그래서 이 단계가 필요하다. 발행되면 인스타가 자기 서버로 복사해 가므로
       나중에 원본을 지워도 게시물은 안 깨진다.
    """
    ig = item.get("ig") or {}
    slug = ig.get("slug") or item["id"]
    site = c.get("site_url")
    reels_dir = c.get("reels_dir")
    if not (site and reels_dir):
        log("⚠️ publish_config.json 에 site_url·reels_dir 이 없다 — 인스타 건너뜀")
        return None

    src = os.path.join(HERE, item["file_yt"])
    if not os.path.exists(src):
        log("❌ 영상 파일이 없다: " + src)
        return None

    dst_dir = os.path.join(HERE, reels_dir)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, slug + ".mp4")
    shutil.copy(src, dst)
    log("영상 복사 → {} ({:.1f}MB)".format(dst, os.path.getsize(dst) / 1e6))

    for step in c.get("deploy_steps", []):
        if not run(step["cmd"], cwd=os.path.join(HERE, step.get("cwd", "."))):
            log("❌ 배포 단계 실패: " + " ".join(step["cmd"]))
            return None

    return "{}/reels/{}.mp4".format(site.rstrip("/"), slug)


def sync_reels_queue(item, url):
    """queue.json 의 내용으로 queue_reels.json 항목을 만든다(있으면 갱신).

    🔴 문구를 두 군데 적지 않게 하려는 것이다. 인스타 전용 문구가 필요하면
       queue.json 의 `ig.caption` / `ig.comment` 에만 적으면 된다.
    """
    ig = item.get("ig") or {}
    q = load(QUEUE_REELS) if os.path.exists(QUEUE_REELS) else {"reels": []}
    rid = ig.get("slug") or item["id"]
    entry = {
        "id": rid,
        "video": url,
        "caption": ig.get("caption") or item.get("desc_tt") or item.get("desc", ""),
        "tags": ig.get("tags") or item.get("tags", []),
        "comment": ig.get("comment") or item.get("comment", ""),
        "status": "",
    }
    hit = [x for x in q["reels"] if x["id"] == rid]
    if hit:
        hit[0].update({k: v for k, v in entry.items() if k != "status"})
    else:
        q["reels"].append(entry)
    save(QUEUE_REELS, q)
    return rid


# ── 플랫폼별 업로드 ────────────────────────────────────────────────────────
def do_yt(item, c):
    cmd = [sys.executable, "upload_yt_api.py", "--id", item["id"], "--publish", "--comment"]
    if c.get("yt_public", True):
        cmd.append("--public")
    if item.get("playlist"):
        cmd += ["--playlist", item["playlist"]]
    return run(cmd, cwd=HERE)


def do_tt(item, c):
    return run([sys.executable, "upload_tt.py", "--id", item["id"], "--publish"], cwd=HERE)


def do_ig(item, c):
    url = prepare_ig(item, c)
    if not url:
        return False
    rid = sync_reels_queue(item, url)
    log("인스타 영상 주소: " + url)
    return run([sys.executable, "post_ig_reel.py", "--id", rid, "--publish", "--comment"], cwd=HERE)


DO = {"yt": do_yt, "tt": do_tt, "ig": do_ig}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="queue.json 의 편 id")
    ap.add_argument("--go", action="store_true", help="실제로 올린다 (없으면 미리보기)")
    ap.add_argument("--only", help="yt,tt,ig 중 이것만")
    ap.add_argument("--skip", help="yt,tt,ig 중 이건 빼고")
    ap.add_argument("--force", action="store_true", help="이미 done 인 것도 다시 올린다")
    a = ap.parse_args()

    q = load(QUEUE)
    hit = [x for x in q["videos"] if x["id"] == a.id]
    if not hit:
        log("❌ 그런 id 가 없다: " + a.id)
        log("   있는 id: " + ", ".join(x["id"] for x in q["videos"]))
        return 1
    item = hit[0]
    c = cfg()

    targets = ORDER
    if a.only:
        targets = [t for t in ORDER if t in a.only.split(",")]
    if a.skip:
        targets = [t for t in targets if t not in a.skip.split(",")]

    st = item.setdefault("status", {})
    todo = [t for t in targets if a.force or st.get(t) not in ("done", "skip")]

    mp4 = os.path.join(HERE, item["file_yt"])
    log("편: {} — {}".format(item["id"], item.get("brand", "")))
    log("영상: {}".format("있음 ({:.1f}MB)".format(os.path.getsize(mp4) / 1e6)
                          if os.path.exists(mp4) else "❌ 없음 " + mp4))
    log("제목({}자): {}".format(len(item.get("title", "")), item.get("title", "")))
    log("올릴 곳: {}".format(", ".join(NAME[t] for t in todo) if todo else "없음(전부 done)"))
    for t in ORDER:
        if t in targets and t not in todo:
            log("  · {} 는 이미 {} — 건너뜀".format(NAME[t], st.get(t)))

    if not a.go:
        log("⏸ 미리보기만. 실제로 올리려면 --go")
        return 0
    if not todo:
        return 0
    if not os.path.exists(mp4):
        return 1

    result = {}
    for t in todo:
        log("──── {} ────".format(NAME[t]))
        try:
            ok = DO[t](item, c)
        except Exception as e:
            log("❌ {} 실패: {}".format(NAME[t], str(e)[:200]))
            ok = False
        result[t] = ok
        # 🔴 각 스크립트가 자기 큐에 done 을 적으므로 여기서 또 적지 않는다.
        #    두 곳에서 쓰면 어긋난다. 실패만 기록해둔다.
        if not ok:
            st[t] = "fail"

    save(QUEUE, q)
    log("──── 결과 ────")
    for t in todo:
        log("  {} {}".format("✅" if result[t] else "❌", NAME[t]))
    log("손으로 남은 것: 유튜브·인스타 **첫 댓글 고정** (API로 안 된다)")
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
