# -*- coding: utf-8 -*-
"""주간 가격 갱신 — 식봄·쿠팡·브랜드API 를 12시간에 걸쳐 천천히 돌고, 끝나면 배포까지. (2026-08-14 신설)

    python scripts/weekly_price_update.py             # 12시간 분산 (일요일 03:00 스케줄이 이걸 부른다)
    python scripts/weekly_price_update.py --fast      # 분산 없이 최소 간격으로 (테스트·수동 급행)
    python scripts/weekly_price_update.py --no-deploy # 가격 갱신까지만, 재계산·배포 생략

## 대표 확정 사항 (2026-08-14)
  · **갱신이지 재선정이 아니다.** 사람이 확정한 상품(decided_at)의 «현재 가격»만 다시 읽는다.
    상품을 새로 고르지 않는다 — `never-auto-overwrite-human-decisions`.
  · **품절·소실은 덮지 않고 보고한다.** 검색 결과에서 그 상품이 사라졌으면 값은 그대로 두고
    `data/weekly_update_report.json` 의 확인목록에 쌓는다. 사람이 보고 결정한다.
  · **12시간 분산.** 일요일 03:00 시작 → 15:00 안팎 완료. 쿠팡 분당 50회 제한(실제로는
    분당 1회도 안 되게 간다) · 식봄도 몰아치지 않는다.
  · **끝나면 배포까지.** `daily_update.py` 를 그대로 부른다 — 재계산→생성→빌드→헬스체크→배포가
    거기 다 있고 이미 검증된 경로다. 헬스체크 미통과면 거기서 알아서 배포를 멈춘다.

## 세 단계
  0. 브랜드 API 메뉴가 — `brand_api_collect.py --apply` (뚫린 브랜드 전부, 몇 분이면 끝)
  1. 쿠팡 소매가 — `ingredient_retail(status='ok')` 287행. name_raw 로 검색해서
     **같은 product_id** 를 찾아 가격만 갱신. 못 찾으면 품절 후보로 보고.
  2. 식봄 도매가 — `ingredients.wholesale_basis` 에서 nid 를 파싱해 카테고리를 다시 받고,
     **basis 에 적힌 그 상품명**이 여전히 있으면 원/kg 갱신. 없으면 소실 후보로 보고.
     nid 가 없거나 base_unit 이 kg 이 아니면 «수동확인» 으로 넘긴다 — 억지로 붙이지 않는다.

## 상태 파일 (관리자 페이지가 읽는다)
  · data/weekly_update.lock          — 실행 중 표시 {pid, started}. 14시간 넘으면 낡은 것으로 본다
  · data/weekly_update_progress.json — 진행률 {phase, done, total, updated, missing, last_item, ...}
  · data/weekly_update_report.json   — 결과 보고 (변경 목록 · 품절/소실 · 수동확인)
"""
import argparse
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

DB = os.path.join(BASE, "data", "eolmanama.db")
LOCK = os.path.join(BASE, "data", "weekly_update.lock")
PROG = os.path.join(BASE, "data", "weekly_update_progress.json")
REPORT = os.path.join(BASE, "data", "weekly_update_report.json")
LOGDIR = os.path.join(BASE, "logs")
PY = sys.executable

TOTAL_SECONDS = 12 * 3600      # 12시간에 걸쳐 편다
STALE_LOCK_H = 14              # 락이 이보다 오래됐으면 죽은 실행으로 본다

# 식봄 카테고리 호출 — wholesale_recat.py 의 검증된 호출을 복사(공용모듈 규칙: import 말고 복사)
FS_API = "https://api.foodspring.co.kr/v2/graphql"
KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
G = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I)
MULT = re.compile(r"[x*×]\s*(\d+)|(\d+)\s*[팩입개]")


def log(msg):
    line = "%s  %s" % (datetime.now().strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    os.makedirs(LOGDIR, exist_ok=True)
    with io.open(os.path.join(LOGDIR, "weekly_%s.log" % datetime.now().strftime("%Y-%m")),
                 "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_json(path, obj):
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ── 락 ───────────────────────────────────────────────────────────
def acquire_lock():
    if os.path.exists(LOCK):
        age_h = (time.time() - os.path.getmtime(LOCK)) / 3600
        if age_h < STALE_LOCK_H:
            log("이미 실행 중이다 (락 %.1f시간 전) — 중복 실행 안 함" % age_h)
            return False
        log("낡은 락(%.1f시간) 무시하고 진행" % age_h)
    save_json(LOCK, {"pid": os.getpid(), "started": datetime.now().isoformat(timespec="seconds")})
    return True


def release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        pass


# ── 진행률 ────────────────────────────────────────────────────────
class Progress:
    def __init__(self, total_items, fast):
        self.d = {"started": datetime.now().isoformat(timespec="seconds"),
                  "fast": fast, "phase": "", "done": 0, "total": total_items,
                  "updated": 0, "changed": 0, "missing": 0, "manual": 0,
                  "last_item": "", "finished": None, "ok": None}

    def set(self, **kw):
        self.d.update(kw)
        save_json(PROG, self.d)

    def bump(self, **kw):
        self.d["done"] += 1
        self.d.update(kw)
        save_json(PROG, self.d)


# ── 0. 브랜드 API 메뉴가 ─────────────────────────────────────────
def phase_brand(report):
    log("── 0단계 브랜드 API 메뉴가 ──")
    p = subprocess.run([PY, os.path.join(BASE, "scripts", "brand_api_collect.py"), "--apply"],
                       cwd=BASE, capture_output=True, timeout=1800)
    out = (p.stdout or b"").decode("utf-8", "replace")
    tail = "\n".join(out.strip().splitlines()[-12:])
    report["brand_api"] = {"rc": p.returncode, "tail": tail}
    log("브랜드 API rc=%d\n%s" % (p.returncode, tail))
    # 실패해도 계속 간다 — 브랜드 하나 때문에 재료 갱신을 버리지 않는다


# ── 1. 쿠팡 소매가 ────────────────────────────────────────────────
def phase_coupang(report, prog, gap):
    from coupang_api import keys, search
    ak, sk = keys()
    c = sqlite3.connect(DB)
    rows = c.execute("SELECT ingredient_key, product_id, price, COALESCE(name_raw, name) "
                     "FROM ingredient_retail WHERE status='ok' AND product_id IS NOT NULL "
                     "ORDER BY ingredient_key").fetchall()
    log("── 1단계 쿠팡 %d행 (간격 %.0f초) ──" % (len(rows), gap))
    prog.set(phase="쿠팡 소매가")
    today = datetime.now().strftime("%Y-%m-%d")

    for key, pid, old_price, kw in rows:
        prog.bump(last_item="쿠팡 %s" % key)
        try:
            r = search(kw, ak, sk, limit=30)
            items = (r.get("data") or {}).get("productData") or []
            hit = next((it for it in items if str(it.get("productId")) == str(pid)), None)
            if hit is None:
                report["coupang_missing"].append(
                    {"key": key, "product_id": pid, "kw": kw, "old_price": old_price})
                prog.set(missing=prog.d["missing"] + 1)
            else:
                new_price = hit.get("productPrice")
                if new_price and new_price > 0:
                    c.execute("UPDATE ingredient_retail SET price=? WHERE ingredient_key=?",
                              (new_price, key))
                    c.commit()
                    prog.set(updated=prog.d["updated"] + 1)
                    if int(new_price) != int(old_price or 0):
                        report["coupang_changed"].append(
                            {"key": key, "old": old_price, "new": new_price})
                        prog.set(changed=prog.d["changed"] + 1)
        except Exception as e:
            report["errors"].append({"phase": "coupang", "key": key, "err": str(e)[:200]})
        time.sleep(gap)
    c.close()
    log("쿠팡 끝 — 갱신 %d · 변동 %d · 품절후보 %d"
        % (prog.d["updated"], prog.d["changed"], prog.d["missing"]))


# ── 2. 식봄 도매가 ────────────────────────────────────────────────
def _fs_pack_kg(name):
    m = KG.search(name)
    kg = None
    if m:
        kg = float(m.group(1))
    else:
        m2 = G.search(name)
        if m2:
            kg = float(m2.group(1)) / 1000
    if kg is None:
        return None
    # "5kg*2" · "1kg x 10팩" 같은 배수 — 07-25 «5kg2팩» 사고의 재발 방지
    tail = name[m.end():] if m else name
    m3 = MULT.search(tail)
    if m3:
        mult = int(m3.group(1) or m3.group(2))
        if 1 < mult <= 30:
            kg *= mult
    return kg


def _fs_cat(nid, first=100):
    import urllib.request
    q = ("query($nid:Int!,$sort:GoodsSortKind!,$first:Int!){"
         "goodsCategory(nid:$nid){name goodsList(sort:$sort,first:$first){"
         "totalCount edges{node{name price{salePrice}}}}}}")
    body = json.dumps({"query": q, "variables": {"nid": nid, "sort": "POPULAR_DESC",
                                                 "first": first}}).encode()
    req = urllib.request.Request(FS_API, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Device-Type": "pc",
        "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
        "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())["data"]["goodsCategory"]
    return [(e["node"]["name"], (e["node"].get("price") or {}).get("salePrice"))
            for e in d["goodsList"]["edges"]]


def _norm(s):
    return re.sub(r"\s+", "", s or "")


def phase_sikbom(report, prog, gap):
    c = sqlite3.connect(DB)
    rows = c.execute(
        "SELECT ingredient_key, wholesale_price, wholesale_basis, base_unit FROM ingredients "
        "WHERE wholesale_basis LIKE '%식봄%' AND wholesale_price > 0 "
        "ORDER BY ingredient_key").fetchall()
    log("── 2단계 식봄 %d행 (간격 %.0f초) ──" % (len(rows), gap))
    prog.set(phase="식봄 도매가")
    today = datetime.now().strftime("%Y-%m-%d")
    cat_cache = {}    # nid → rows (한 카테고리를 여러 재료가 쓴다 — 호출 아낀다)

    for key, old_price, basis, base_unit in rows:
        prog.bump(last_item="식봄 %s" % key)
        nids = re.findall(r"nid[\s:]*(\d+)", basis or "")
        if not nids or (base_unit or "kg") != "kg":
            report["sikbom_manual"].append(
                {"key": key, "why": "nid 없음" if not nids else "base_unit=%s" % base_unit,
                 "basis": (basis or "")[:120]})
            prog.set(manual=prog.d["manual"] + 1)
            continue
        try:
            found = None
            for nid in nids[:3]:
                nid = int(nid)
                if nid not in cat_cache:
                    cat_cache[nid] = _fs_cat(nid)
                    time.sleep(gap)
                # basis 안에 상품명이 통째로 들어있다 — 카테고리 행 이름이 basis 에 있으면 그 상품
                for name, sp in cat_cache[nid]:
                    if sp and len(_norm(name)) >= 8 and _norm(name) in _norm(basis):
                        found = (nid, name, sp)
                        break
                if found:
                    break
            if found is None:
                report["sikbom_missing"].append(
                    {"key": key, "old_price": old_price, "basis": (basis or "")[:120]})
                prog.set(missing=prog.d["missing"] + 1)
            else:
                nid, name, sp = found
                kg = _fs_pack_kg(name)
                if not kg:
                    report["sikbom_manual"].append(
                        {"key": key, "why": "용량 파싱 불가", "basis": name[:120]})
                    prog.set(manual=prog.d["manual"] + 1)
                else:
                    per_kg = round(sp / kg)
                    new_basis = "식봄 (nid %d) %s %s %s원 = %s원/kg (주간자동갱신)" % (
                        nid, today, name, format(sp, ","), format(per_kg, ","))
                    c.execute("UPDATE ingredients SET wholesale_price=?, wholesale_basis=?, "
                              "updated_at=? WHERE ingredient_key=?",
                              (per_kg, new_basis, today, key))
                    c.commit()
                    prog.set(updated=prog.d["updated"] + 1)
                    if int(per_kg) != int(old_price or 0):
                        report["sikbom_changed"].append(
                            {"key": key, "old": old_price, "new": per_kg, "name": name[:80]})
                        prog.set(changed=prog.d["changed"] + 1)
        except Exception as e:
            report["errors"].append({"phase": "sikbom", "key": key, "err": str(e)[:200]})
            time.sleep(gap)
    c.close()


# ── 3. 재계산·생성·배포 ──────────────────────────────────────────
def phase_finish(report):
    log("── 3단계 재계산→생성→빌드→헬스체크→배포 (daily_update.py) ──")
    p = subprocess.run([PY, os.path.join(BASE, "scripts", "daily_update.py")],
                       cwd=BASE, capture_output=True, timeout=3600)
    out = (p.stdout or b"").decode("utf-8", "replace")
    tail = "\n".join(out.strip().splitlines()[-15:])
    report["finish"] = {"rc": p.returncode, "tail": tail}
    log("마무리 rc=%d\n%s" % (p.returncode, tail))
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="12시간 분산 없이 최소 간격")
    ap.add_argument("--no-deploy", action="store_true", help="가격 갱신까지만")
    a = ap.parse_args()

    if not acquire_lock():
        return 1
    report = {"started": datetime.now().isoformat(timespec="seconds"),
              "coupang_changed": [], "coupang_missing": [],
              "sikbom_changed": [], "sikbom_missing": [], "sikbom_manual": [],
              "errors": []}
    try:
        c = sqlite3.connect(DB)
        n_cp = c.execute("SELECT COUNT(*) FROM ingredient_retail "
                         "WHERE status='ok' AND product_id IS NOT NULL").fetchone()[0]
        n_fs = c.execute("SELECT COUNT(*) FROM ingredients "
                         "WHERE wholesale_basis LIKE '%식봄%' AND wholesale_price > 0").fetchone()[0]
        c.close()
        total = n_cp + n_fs
        gap = 1.5 if a.fast else max(1.5, TOTAL_SECONDS / max(total, 1))
        log("시작 — 쿠팡 %d + 식봄 %d = %d건, 간격 %.0f초 (%s)"
            % (n_cp, n_fs, total, gap, "급행" if a.fast else "12시간 분산"))

        prog = Progress(total, a.fast)
        prog.set(phase="브랜드 API")
        phase_brand(report)
        phase_coupang(report, prog, gap)
        phase_sikbom(report, prog, gap)

        ok = True
        if a.no_deploy:
            log("--no-deploy — 재계산·배포 생략")
        else:
            ok = phase_finish(report)

        report["finished"] = datetime.now().isoformat(timespec="seconds")
        report["ok"] = ok
        save_json(REPORT, report)
        prog.set(phase="완료", finished=report["finished"], ok=ok)
        log("전체 완료 — 변동 쿠팡 %d · 식봄 %d / 품절·소실 %d / 수동확인 %d"
            % (len(report["coupang_changed"]), len(report["sikbom_changed"]),
               len(report["coupang_missing"]) + len(report["sikbom_missing"]),
               len(report["sikbom_manual"])))
        return 0 if ok else 1
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
