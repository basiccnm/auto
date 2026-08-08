#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
D1 마이그레이션을 **한 문장씩** 붓는다.

  python scripts/d1_apply.py scripts/migrate_xxx.sql            # 로컬
  python scripts/d1_apply.py scripts/migrate_xxx.sql --remote   # 원격
  python scripts/d1_apply.py scripts/migrate_xxx.sql --keep-going

왜 필요한가 — 두 가지 함정을 한꺼번에 피한다.

  ① `wrangler d1 execute --file` 은 문장이 여러 개면
     "contains several transactions" 로 **통째로 거부**한다(2026-08-08 실측).
  ② `--command "..."` 로 넘기면 윈도우가 인자를 ANSI 로 바꿔 **한글이 깨진다**.
     그래서 명령줄이 아니라 «문장 하나짜리 임시 .sql 파일»로 넘긴다.

그리고 결과를 `"success": true` 로 판정한다 — wrangler 는 실패해도 종료코드가
0 일 때가 있어서 exit code 만 보면 «조용한 실패»를 놓친다.

⚠ 문자열 리터럴 안에 세미콜론이 있으면 쪼개진다. 마이그레이션엔 안 쓴다.
"""
import io, os, re, subprocess, sys, tempfile

DB = "eduthink-db"
HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, "..", "workers", "site-renderer")


def statements(sql_text):
    """`--` 주석을 걷고 세미콜론으로 쪼갠다. 빈 문장은 버린다."""
    out = []
    for raw in sql_text.split("\n"):
        line = re.sub(r"--.*$", "", raw)
        out.append(line)
    body = "\n".join(out)
    return [s.strip() for s in body.split(";") if s.strip()]


def run_one(stmt, remote):
    """문장 하나를 임시 파일로 넘긴다 — 명령줄 인코딩을 타지 않으려고."""
    fd, path = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        io.open(path, "w", encoding="utf-8", newline="\n").write(stmt + ";\n")
        cmd = ["npx", "wrangler", "d1", "execute", DB,
               "--remote" if remote else "--local", "--file", path, "-y"]
        p = subprocess.run(cmd, cwd=WORKER, capture_output=True, shell=True)
        text = (p.stdout or b"").decode("utf-8", "replace") + \
               (p.stderr or b"").decode("utf-8", "replace")
        return ('"success": true' in text or '"success":true' in text), text
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    remote = "--remote" in sys.argv
    keep = "--keep-going" in sys.argv
    if not args:
        print(__doc__)
        return 2

    sql = io.open(args[0], encoding="utf-8").read()
    sts = statements(sql)
    where = "원격" if remote else "로컬"
    print("── %s · %s · 문장 %d개 ────────────────" % (os.path.basename(args[0]), where, len(sts)))

    ok_n = bad_n = 0
    for i, st in enumerate(sts, 1):
        head = " ".join(st.split())[:78]
        ok, text = run_one(st, remote)
        if ok:
            ok_n += 1
            print("  [%2d] OK   %s" % (i, head))
        else:
            bad_n += 1
            # 이미 있는 칼럼·표는 실패가 아니라 «이미 적용됨»이다
            already = ("duplicate column" in text) or ("already exists" in text)
            print("  [%2d] %s %s" % (i, "SKIP" if already else "FAIL", head))
            if not already:
                for ln in text.strip().split("\n"):
                    if "ERROR" in ln or "Error" in ln:
                        print("        %s" % ln.strip()[:160])
                if not keep:
                    print("\n  중단 — --keep-going 을 붙이면 계속 간다")
                    return 1
    print("──────────────────────────────────────")
    print("  성공 %d · 실패/건너뜀 %d" % (ok_n, bad_n))
    return 0 if bad_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
