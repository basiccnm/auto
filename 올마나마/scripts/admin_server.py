# -*- coding: utf-8 -*-
"""관리자 뒷단 서버 (포트 8803) — 밀키트·냉동 완제품 검수. 2026-07-25

왜 서버가 필요한가:
  검수 결과를 localStorage에 두면 브라우저 지우면 날아가고, 수동 다운로드는 번거롭다.
  결정은 **DB(menu_mealkit)** 에 바로 저장한다. 재생성·재배포에도 살아남는다.

  자동매칭은 폐기했다 — 421건 중 50%가 중복 매칭이었다(키워드 폴백 때문).
  사람이 메뉴 하나씩 고른 것만 정본으로 쓴다.

사용법: python scripts/admin_server.py   → http://127.0.0.1:8803/mealkit
"""
import base64, hashlib, hmac, http.server, json, io, os, re, sqlite3, sys, time, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import admin_store as st  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
ADMIN_DIR = os.path.join(BASE, "_admin")
REVIEW_JSON = os.path.join(BASE, "data", "research", "mealkit_strict.json")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8803
STAMP_TODAY = "2026-07-25"

# ── 로그인 (2026-07-26 신설) ─────────────────────────────────────────
#  🔴 이 서버는 **프로덕션 DB(data/eolmanama.db)에 직접 쓴다.** 그리고 도매가 조사값
#     — 우리 사업 자산 — 을 전부 노출한다. 그래서 밖으로 뚫으려면 반드시 잠근다.
#
#  비밀번호는 `.env` 의 OLMANAMA_ADMIN_PW (없으면 0303). 4자리 숫자는 1만 가지라
#  그것만으로는 초당 수천 번 시도에 뚫린다. 그래서 세 겹으로 막는다:
#    ① 실패 5회면 그 IP를 5분 잠금 (LOCK_AFTER / LOCK_SEC)
#    ② 비교는 hmac.compare_digest — 타이밍 공격 방지
#    ③ 쿠키는 서버 기동 시 만든 임의 키로 서명. 재시작하면 전부 로그아웃된다
#  ⚠️ 그래도 4자리는 약하다. 인터넷에 그냥 뚫지 말고 Cloudflare Tunnel + Access 뒤에 둘 것.
ADMIN_PW = (st.load_env().get("OLMANAMA_ADMIN_PW") if hasattr(st, "load_env") else None) or \
           os.environ.get("OLMANAMA_ADMIN_PW") or "0303"
_SECRET = os.urandom(32)              # 기동마다 새로 — 재시작 = 전원 로그아웃
COOKIE = "olma_admin"
SESSION_SEC = 12 * 3600
LOCK_AFTER, LOCK_SEC = 5, 300
_fails = {}                           # ip -> [실패횟수, 잠금해제시각]

# 로그인 없이 열어주는 경로 (로그인 화면 자체와 그 처리)
OPEN_PATHS = ("/login", "/api/login")


def _token(exp):
    msg = str(int(exp)).encode()
    sig = hmac.new(_SECRET, msg, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(msg + b"." + sig).decode()


def _token_ok(tok):
    try:
        raw = base64.urlsafe_b64decode(tok.encode())
        msg, sig = raw.rsplit(b".", 1)
        if not hmac.compare_digest(sig, hmac.new(_SECRET, msg, hashlib.sha256).digest()[:16]):
            return False
        return int(msg) > time.time()
    except Exception:
        return False


LOGIN_HTML = """<!doctype html><meta charset="utf-8"><title>올마나마 관리</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;height:100vh;display:grid;place-items:center;background:#fafafa;
 font:14px/1.5 -apple-system,"Segoe UI",system-ui,sans-serif;color:#18181b}
form{background:#fff;border:1px solid #e4e4e7;border-radius:14px;padding:26px 24px;width:280px;
 box-shadow:0 1px 3px rgba(0,0,0,.04)}
h1{font-size:15px;margin:0 0 4px;font-weight:800}
p{margin:0 0 16px;font-size:12.5px;color:#71717a}
input{width:100%;box-sizing:border-box;font:inherit;font-size:18px;letter-spacing:.3em;
 text-align:center;border:1px solid #e4e4e7;border-radius:9px;padding:11px}
button{width:100%;margin-top:10px;font:inherit;font-weight:700;cursor:pointer;color:#fff;
 background:#18181b;border:0;border-radius:9px;padding:11px}
.err{margin-top:10px;font-size:12.5px;color:#dc2626;font-weight:700;min-height:18px}
</style>
<form id="f">
  <h1>올마나마 관리</h1>
  <p>비밀번호를 입력하세요.</p>
  <input id="pw" type="password" inputmode="numeric" autocomplete="current-password" autofocus>
  <button>들어가기</button>
  <div class="err" id="e">__ERR__</div>
</form>
<script>
document.getElementById('f').addEventListener('submit',async e=>{
  e.preventDefault();
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({pw:document.getElementById('pw').value})}).then(r=>r.json());
  if(r.ok){location.href='/';return;}
  document.getElementById('e').textContent=r.error||'틀렸습니다';
  document.getElementById('pw').value='';document.getElementById('pw').focus();
});
</script>"""

# 브랜드 정품 판정용 — 상품명에 브랜드 핵심어가 있으면 '정품'
_SUFFIX = re.compile(r"(치킨|피자|버거|분식|떡볶이|샐러드|김밥|설렁탕|국밥)$")


def brand_core(b):
    return _SUFFIX.sub("", (b or "").replace(" ", ""))


def is_official(brand, product_name):
    bc = brand_core(brand)
    return bool(bc) and len(bc) >= 2 and bc.lower() in (product_name or "").replace(" ", "").lower()


def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    return c


def load_menus():
    """검수 대상 = **DB의 전 메뉴** + 후보 JSON + 결정/거부 상태.

    🔴 후보 JSON에 있는 것만 보여주면 "이쪽 메뉴를 저기 붙여야 하는데 저쪽엔 없는" 경우가
       목록에서 아예 안 보인다(2026-07-25 대표 지적). 그래서 전 메뉴를 다 싣고,
       후보가 없으면 '후보없음'으로 표시한다.
    """
    try:
        raw = json.load(io.open(REVIEW_JSON, encoding="utf-8"))
    except FileNotFoundError:
        raw = {}
    c = conn()
    # DB 전 메뉴가 기준
    allm = [dict(r) for r in c.execute(
        """SELECT m.id AS menu_id, m.name AS menu, b.name AS brand, c2.name AS category
           FROM menus m JOIN brands b ON b.id=m.brand_id
           LEFT JOIN categories c2 ON c2.id=b.category_id
           ORDER BY c2.name, b.name, m.id""")]
    data = []
    for m in allm:
        got = raw.get(str(m["menu_id"])) or {}
        m = dict(m)
        m["candidates"] = got.get("candidates") or []
        m["fetched"] = bool(got)          # 수집을 돌렸는지(돌렸는데 0개면 진짜 없는 것)
        data.append(m)
    decided = {r["menu_id"]: dict(r) for r in c.execute("SELECT * FROM menu_mealkit")}
    rejected = {}
    for r in c.execute("SELECT menu_id, product_id FROM mealkit_rejected"):
        rejected.setdefault(r["menu_id"], set()).add(r["product_id"])
    c.close()
    out = []
    for m in data:
        mid = m["menu_id"]
        rej = rejected.get(mid, set())
        cands = []
        for cd in m.get("candidates", []):
            if cd["id"] in rej:
                continue
            cd = dict(cd)
            cd["official"] = is_official(m.get("brand"), cd["name"])
            cands.append(cd)
        # 4단 우선순위(2026-07-25 확정):
        #   ① 정품+로켓  ② 정품+일반  ③ 대체+로켓  ④ 대체+일반
        #   그 안에서 앵커(카테고리 핵심어) 일치 → 저가 순.
        cands.sort(key=lambda c: (not c["official"], not bool(c.get("rocket")),
                                  -c.get("anchored", 0), c.get("price") or 0))
        d = decided.get(mid)
        out.append({
            "menu_id": mid, "brand": m.get("brand"), "menu": m.get("menu"),
            "category": m.get("category"), "candidates": cands,
            "rejected": len(rej),      # ×로 지운 개수 — 복구 버튼 노출용
            "fetched": m.get("fetched", True),
            "decision": ({"product_id": d["product_id"], "status": d["status"]} if d else None),
        })
    return out


def _retail_cands(key, name, rejected=()):
    """이 재료의 쿠팡 후보 목록. 대표가 화면에서 **매칭을 직접 골라 바꾸도록** 내려준다.

    🔴 소매에서 kg 단가를 쓰지 않는다(대표 지시 2026-07-26). 상품 가격 그 자체가 소매값이다.
       "쌈장 12,667원/kg" 같은 숫자는 실제로 낼 돈과 무관하다 — 7,500원짜리 한 통을 사는 것이다.
    """
    try:
        sys.path.insert(0, os.path.join(BASE, "scripts"))
        import retail_fill as RF
    except Exception:
        return []
    out, seen = [], set()
    for kw in RF.kw_list(name):
        fp = RF.cpath(kw)
        if not os.path.exists(fp):
            continue
        try:
            items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
        except Exception:
            continue
        cw = RF.cores(kw)
        for p in items:
            pid, pn, price = p.get("productId"), p.get("productName") or "", p.get("productPrice")
            if not price or pid in seen or pid in rejected:
                continue
            if not p.get("isRocket"):          # 로켓이 1순위 (대표 지시)
                continue
            if not RF.is_food(p) or RF.JUNK.search(pn):
                continue
            if not any(w in re.sub(r"\s+", "", pn) for w in cw):
                continue
            seen.add(pid)
            out.append({"product_id": pid, "name": pn, "price": price,
                        "pack_g": RF.pack_g(pn), "image": p.get("productImage"),
                        "url": p.get("productUrl"), "keyword": kw,
                        "premium": 1 if RF.CI.PREMIUM.search(pn) else 0})
    # 프리미엄 후순위 → **가격 최저** (소매는 총 지출이 기준)
    out.sort(key=lambda x: (x["premium"], x["price"]))
    return out[:6]


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ADMIN_DIR, **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    # ── 로그인 검사 ───────────────────────────────────────────────
    def _ip(self):
        # Cloudflare Tunnel 뒤에서는 실제 방문자 IP가 CF-Connecting-IP 로 온다.
        # 그걸 안 보면 모든 요청이 127.0.0.1 로 뭉쳐 잠금이 서로를 막는다.
        return (self.headers.get("CF-Connecting-IP")
                or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or self.client_address[0])

    def _logged_in(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE and _token_ok(v):
                return True
        return False

    def _send_login(self):
        b = LOGIN_HTML.replace("__ERR__", "").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _need_login(self, p):
        """로그인 화면을 내보냈으면 True. 호출한 쪽은 즉시 return 해야 한다."""
        if p in OPEN_PATHS or self._logged_in():
            return False
        if p.startswith("/api/"):
            self._json({"ok": False, "error": "로그인이 필요합니다"}, 401)
            return True
        self._send_login()
        return True

    def _login(self, body):
        ip = self._ip()
        n, until = _fails.get(ip, (0, 0))
        if until > time.time():
            return {"ok": False, "error": "시도가 많아 %d초 잠겼습니다" % int(until - time.time())}
        pw = str(body.get("pw") or "")
        if not hmac.compare_digest(pw, ADMIN_PW):
            n += 1
            _fails[ip] = (n, time.time() + LOCK_SEC if n >= LOCK_AFTER else 0)
            left = LOCK_AFTER - n
            return {"ok": False, "error": ("틀렸습니다 (%d번 더 틀리면 잠깁니다)" % left
                                           if left > 0 else "잠겼습니다. 5분 뒤 다시")}
        _fails.pop(ip, None)
        tok = _token(time.time() + SESSION_SEC)
        b = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d"
                         % (COOKIE, tok, SESSION_SEC))
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
        return None      # 응답을 직접 보냈다

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p, qs = u.path, urllib.parse.parse_qs(u.query)
        if p == "/login":
            return self._send_login()
        if self._need_login(p):
            return
        if p == "/api/mealkit":
            try:
                return self._json({"ok": True, "menus": load_menus()})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 500)
        if p == "/api/stats":
            return self._json({"ok": True, **self._stats()})
        if p == "/api/menus":
            return self._json({"ok": True, "menus": self._menus(qs.get("q", [""])[0])})
        if p == "/api/menu":
            return self._json({"ok": True, **self._menu_detail(int(qs["id"][0]))})
        if p == "/api/ingredients":
            return self._json({"ok": True, "rows": self._ingredients(
                qs.get("q", [""])[0], qs.get("f", [""])[0])})
        if p == "/api/ingredient":
            return self._json({"ok": True, **self._ing_detail(qs["key"][0])})
        if p == "/api/retail":
            return self._json({"ok": True, "rows": self._retail(qs.get("f", [""])[0])})
        if p == "/api/retail/live":
            # 수집기(retail_fill.py)가 넣는 pending 을 실시간으로 읽는다.
            #  화면이 3초마다 폴링한다 — 대표가 새로고침을 누르지 않아도 올라온다.
            return self._json({"ok": True, **self._retail_live()})
        # 페이지 라우팅 (확장자 없는 주소 → .html)
        if p == "/":
            self.path = "/index.html"
        elif p in ("/mealkit", "/menus", "/ingredients", "/retail", "/live"):
            self.path = p + ".html"
        return super().do_GET()

    # ── 조회 API ──
    def _stats(self):
        c = conn()
        g = lambda q: c.execute(q).fetchone()[0]
        s = {
            "menus": g("SELECT COUNT(*) FROM menus"),
            "brands": g("SELECT COUNT(DISTINCT brand_id) FROM menus"),
            "ingredients": g("SELECT COUNT(*) FROM ingredients WHERE wholesale_price>0"),
            "mk_done": g("SELECT COUNT(*) FROM menu_mealkit"),
            "mk_ok": g("SELECT COUNT(*) FROM menu_mealkit WHERE status='ok'"),
            "mk_official": g("SELECT COUNT(*) FROM menu_mealkit WHERE match_type='정품'"),
            "mk_rejected": g("SELECT COUNT(*) FROM mealkit_rejected"),
            "audit_open": g("SELECT COUNT(*) FROM menu_name_audit WHERE status='open'"),
            "audit_fix": g("SELECT COUNT(*) FROM menu_name_audit "
                           "WHERE status='open' AND suggest IS NOT NULL"),
            "audit_applied": g("SELECT COUNT(*) FROM menu_name_audit WHERE status='applied'"),
        }
        try:
            s["mk_total"] = len(json.load(io.open(REVIEW_JSON, encoding="utf-8")))
        except Exception:
            s["mk_total"] = 0
        c.close()
        return s

    def _menus(self, q=""):
        c = conn()
        sql = """SELECT m.id, m.name, m.sell_price, m.est_cost, m.cost_ratio,
                        m.store_cost, m.store_ratio,
                        b.name AS brand, c2.name AS cat,
                        (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.menu_id=m.id) AS ings,
                        (SELECT COUNT(*) FROM menu_mealkit k WHERE k.menu_id=m.id) AS mk,
                        a.verdict AS a_verdict, a.suggest AS a_suggest,
                        a.note AS a_note, a.confidence AS a_conf, a.status AS a_status,
                        v.verified_at AS ok_at, v.note AS ok_note
                 FROM menus m JOIN brands b ON b.id=m.brand_id
                 LEFT JOIN categories c2 ON c2.id=b.category_id
                 LEFT JOIN menu_name_audit a ON a.menu_id=m.id AND a.status='open'
                 LEFT JOIN menu_verified v ON v.menu_id=m.id"""
        args = []
        if q:
            sql += " WHERE m.name LIKE ? OR b.name LIKE ?"
            args = ["%%%s%%" % q, "%%%s%%" % q]
        sql += " ORDER BY b.name, m.name"
        rows = [dict(r) for r in c.execute(sql, args)]
        c.close()
        return rows

    def _ingredients(self, q="", f=""):
        """재료 목록. f=est(추정근거만) · f=unused(메뉴 미사용) · f=tier(원산지티어 있음)"""
        c = conn()
        sql = """SELECT i.ingredient_key AS k, i.name, i.subcat, i.base_unit AS unit,
                        i.wholesale_price AS wp, i.wholesale_basis AS basis, i.updated_at,
                        (SELECT COUNT(DISTINCT mi.menu_id) FROM menu_ingredients mi
                           WHERE mi.ingredient_key=i.ingredient_key) AS uses,
                        (SELECT COUNT(*) FROM ingredient_price p
                           WHERE p.ingredient_key=i.ingredient_key) AS tiers
                 FROM ingredients i WHERE i.wholesale_price>0"""
        args = []
        if q:
            sql += " AND (i.name LIKE ? OR i.wholesale_basis LIKE ?)"
            args += ["%%%s%%" % q, "%%%s%%" % q]
        if f == "est":   # 추정·불투명 근거 = 실판매가로 교체해야 하는 것
            sql += (" AND (COALESCE(i.wholesale_basis,'') LIKE '%coef%'"
                    " OR COALESCE(i.wholesale_basis,'') LIKE '%research%'"
                    " OR COALESCE(i.wholesale_basis,'') LIKE '%추정%'"
                    " OR COALESCE(i.wholesale_basis,'') LIKE '%출처 비공개%'"
                    " OR COALESCE(i.wholesale_basis,'') = '')")
        elif f == "unused":
            sql += (" AND NOT EXISTS (SELECT 1 FROM menu_ingredients mi"
                    " WHERE mi.ingredient_key=i.ingredient_key)")
        elif f == "tier":
            sql += (" AND EXISTS (SELECT 1 FROM ingredient_price p"
                    " WHERE p.ingredient_key=i.ingredient_key)")
        sql += " ORDER BY uses DESC, i.name LIMIT 600"
        rows = [dict(r) for r in c.execute(sql, args)]
        c.close()
        return rows

    def _ing_detail(self, key):
        c = conn()
        ing = c.execute("SELECT * FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
        tiers = [dict(r) for r in c.execute(
            "SELECT tier, origin, part, grade, price, pack_kg, source, basis "
            "FROM ingredient_price WHERE ingredient_key=? ORDER BY price", (key,))]
        menus = [dict(r) for r in c.execute(
            """SELECT m.id, m.name, b.name AS brand, mi.amount, mi.unit
               FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
               JOIN brands b ON b.id=m.brand_id WHERE mi.ingredient_key=?
               ORDER BY b.name LIMIT 40""", (key,))]
        c.close()
        return {"ing": (dict(ing) if ing else None), "tiers": tiers, "menus": menus}

    def _menu_detail(self, mid):
        c = conn()
        m = c.execute("""SELECT m.*, b.name AS brand FROM menus m
                         JOIN brands b ON b.id=m.brand_id WHERE m.id=?""", (mid,)).fetchone()
        # 검수에 필요한 건 이름·양만이 아니다. **부위·원산지·도매단가·근거**까지 봐야
        # "통다리 메뉴에 콤보육", "1kg 단품 가격(택배비 별도)" 같은 걸 잡을 수 있다.
        ings = [dict(r) for r in c.execute(
            """SELECT i.ingredient_key, i.name, i.origin, i.name_note,
                      i.wholesale_price, i.wholesale_basis, i.manual_price, i.base_unit,
                      mi.amount, mi.unit, mi.line_cost, mi.wholesale_cost
               FROM menu_ingredients mi JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
               WHERE mi.menu_id=? ORDER BY mi.sort_order""", (mid,))]
        v = c.execute("SELECT verified_at, note FROM menu_verified WHERE menu_id=?", (mid,)).fetchone()
        c.close()
        return {"menu": (dict(m) if m else None), "ingredients": ings,
                "verified": (dict(v) if v else None)}

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception as e:
            return self._json({"ok": False, "error": "bad json: %s" % e}, 400)
        if p == "/api/login":
            r = self._login(body)
            return self._json(r) if r else None      # 성공 시 _login 이 직접 응답했다
        if self._need_login(p):
            return
        try:
            if p == "/api/mealkit/pick":
                return self._json(self._pick(body))
            if p == "/api/mealkit/none":
                return self._json(self._none(body))
            if p == "/api/mealkit/reject":
                return self._json(self._reject(body))
            if p == "/api/mealkit/unreject":
                return self._json(self._unreject(body))
            if p == "/api/mealkit/undo":
                return self._json(self._undo(body))
            if p == "/api/menu/rename":
                return self._json(self._rename(body))
            if p == "/api/audit/dismiss":
                return self._json(self._dismiss(body))
            if p == "/api/ingredient/update":
                return self._json(self._ing_update(body))
            if p == "/api/menu/verify":
                return self._json({"ok": True, **self._menu_verify(body)})
            if p == "/api/menu/unverify":
                return self._json({"ok": True, **self._menu_unverify(body)})
            if p == "/api/menu/price":
                return self._json(self._menu_price(body))
            if p == "/api/retail/pick":
                return self._json(self._retail_pick(body))
            if p == "/api/retail/none":
                return self._json(self._retail_none(body))
            if p == "/api/retail/undo":
                return self._json(self._retail_undo(body))
            if p == "/api/retail/reject":
                return self._json(self._retail_reject(body))
            if p == "/api/retail/swap":
                return self._json(self._retail_swap(body))
            if p == "/api/menu-ingredient/remove":
                return self._json(self._mi_remove(body))
            if p == "/api/menu-ingredient/restore":
                return self._json(self._mi_restore(body))
            if p == "/api/ingredient/rename":
                return self._json(self._ing_rename2(body))
            if p == "/api/ingredient/delete":
                return self._json(self._ing_delete(body))
            if p == "/api/retail/research":
                return self._json(self._retail_research(body))
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)
        return self._json({"ok": False, "error": "unknown endpoint"}, 404)

    # ── 재료 소매(쿠팡) 검수 ─────────────────────────────────────
    #  도매 = 식봄 / 소매 = 쿠팡 (대표 확정 2026-07-26).
    #  쿠팡 상품을 붙이면 **소매가 + 최소 판매단위**가 같이 정해진다.
    #  ⚠️ 소매가 도매의 3~6배인 건 정상이다(소포장 프리미엄). 가격 배수로 오류를
    #     판단하지 말고 **품목이 맞는지**로 볼 것. 실제 오매칭 사례:
    #     김밥용 세트→삼각김밥틀 · 떡볶이 떡→떡볶이 완제품 · 중력 밀가루→통밀가루
    RETAIL_JSON = os.path.join(BASE, "data", "research", "ingredient_retail.json")

    def _retail(self, f=""):
        try:
            src = json.load(io.open(self.RETAIL_JSON, encoding="utf-8"))
        except Exception:
            src = {}
        c = conn()
        done = {r["ingredient_key"]: dict(r) for r in
                c.execute("SELECT * FROM ingredient_retail")}
        cur_pack = {r["ingredient_key"]: dict(r) for r in
                    c.execute("SELECT ingredient_key, qty, label FROM ingredient_pack")}
        rows = []
        for k, v in src.items():
            if k.startswith("_"):
                continue
            d = done.get(k)
            cands = v.get("cands") or []
            top = cands[0] if cands else None
            # 이름이 약하게만 겹치면(토큰 1개) 오매칭 가능성이 높다 → 표시해준다
            weak = 1 if (top and top.get("hit", 0) <= 1 and len(v.get("keyword", "").split()) > 1) else 0
            rows.append({
                "key": k, "name": v["name"], "uses": v["uses"],
                "base_unit": v.get("base_unit"),
                "now_wholesale": v.get("now_wholesale"),
                "now_retail": v.get("now_retail"),
                "now_pack": cur_pack.get(k),
                "cands": cands, "weak": weak,
                "decided": d["status"] if d else None,
                "picked": d if d else None,
            })
        c.close()
        if f == "todo":
            rows = [r for r in rows if not r["decided"]]
        elif f == "weak":
            rows = [r for r in rows if r["weak"] and not r["decided"]]
        elif f == "none":
            rows = [r for r in rows if not r["cands"]]
        elif f == "done":
            rows = [r for r in rows if r["decided"]]
        rows.sort(key=lambda r: (-r["uses"], r["name"]))
        return rows

    # ── 실시간 소매 검수 (2026-07-26 신설) ─────────────────────────
    #  수집기 `scripts/retail_fill.py` 가 쿠팡 **로켓 최저가**를 찾아 status='pending' 으로 넣는다.
    #  이 화면은 그걸 3초마다 읽어 대표가 「통과」/「반려」만 누르면 되게 한다.
    #  · pending  = 수집됐고 아직 안 본 것
    #  · ok       = 통과 (소매가·장보기 단위가 DB에 반영된다)
    #  · skip     = 로켓배송 상품이 없어 수집기가 넘긴 것 (대표 방침: 없으면 일단 넘긴다)
    def _retail_live(self):
        c = conn()
        rows = [dict(r) for r in c.execute("""
            SELECT x.*, i.name AS ing_name, i.base_unit,
                   i.wholesale_price AS now_wholesale,
                   (SELECT COUNT(*) FROM menu_ingredients mi
                     WHERE mi.ingredient_key=x.ingredient_key) AS uses,
                   (SELECT qty*1000 FROM ingredient_pack p WHERE p.ingredient_key=x.ingredient_key) AS pack_now_g,
                   (SELECT COUNT(*) FROM retail_rejected j
                     WHERE j.ingredient_key=x.ingredient_key) AS rejected
            FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
            ORDER BY (x.status<>'pending'), (x.status<>'skip'), uses DESC, i.name""")]
        # 🔴 후보를 함께 내려준다 — 대표가 화면에서 **매칭을 직접 골라 바꾼다**(지시 2026-07-26).
        #    자동으로 고른 최저가가 그 재료가 아닐 수 있으니, 후보를 보여주고 체크하게 한다.
        rej = {}
        for r in c.execute("SELECT ingredient_key, product_id FROM retail_rejected"):
            rej.setdefault(r[0], set()).add(r[1])
        used_in = {}
        for u in c.execute("""
            SELECT mi.ingredient_key k, mi.menu_id, b.name brand, m.name menu, mi.amount, mi.unit
            FROM menu_ingredients mi
            JOIN menus m ON m.id=mi.menu_id JOIN brands b ON b.id=m.brand_id
            ORDER BY b.name, m.name"""):
            used_in.setdefault(u["k"], []).append(
                {"menu_id": u["menu_id"], "brand": u["brand"], "menu": u["menu"],
                 "amount": u["amount"], "unit": u["unit"]})
        for r in rows:
            r["used_in"] = used_in.get(r["ingredient_key"], [])
            r["cands"] = _retail_cands(r["ingredient_key"], r["ing_name"],
                                       rej.get(r["ingredient_key"], set()))
            r["keyword"] = (r.get("keyword")
                            or (r["cands"][0]["keyword"] if r["cands"] else None))
        cnt = {r["status"]: r["n"] for r in c.execute(
            "SELECT status, COUNT(*) n FROM ingredient_retail GROUP BY status")}
        total = c.execute("""SELECT COUNT(*) FROM ingredients i WHERE
            (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key)>0
            """).fetchone()[0]
        c.close()
        return {"rows": rows, "count": cnt, "total": total}

    def _retail_pick(self, b):
        """상품 채택 → 소매가·장보기 단위를 함께 반영한다."""
        key = b["key"]
        # 🔴 소매는 g으로 저장한다. kg 단가는 만들지 않는다(대표 지시 2026-07-26).
        pg = float(b.get("pack_g") or 0)
        price = float(b.get("price") or 0)
        c = conn()
        c.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,?,?,?, 'ok', ?)""",
                  (key, b.get("product_id"), b.get("name"), price, pg,
                   1 if b.get("rocket") else 0, b.get("image"), b.get("url"), st.now()))
        bu = c.execute("SELECT base_unit FROM ingredients WHERE ingredient_key=?",
                       (key,)).fetchone()
        bu = bu[0] if bu else None
        pieces = float(b.get("pieces") or 0)
        # 개·세트 단위 재료는 kg 환산이 무의미하다 — **개당 가격**을 쓴다.
        #  치킨무는 91개 메뉴에서 "1개"로 쓰인다. 60개 23,500원이면 개당 392원.
        if pieces and bu not in ("kg", "L"):
            per = round(price / pieces)
            c.execute("""UPDATE ingredients SET manual_price=?, updated_at=?
                WHERE ingredient_key=?""", (per, st.now()[:10], key))
            c.execute("INSERT OR REPLACE INTO ingredient_pack(ingredient_key,qty,label) VALUES(?,?,?)",
                      (key, pieces, b.get("label") or ("%g개" % pieces)))
            c.commit(); c.close()
            return {"ok": True, "per_piece": per, "pieces": pieces}
        # 무게·부피 단위 — kg당 단가 + 장보기 단위("500g 팩" 추측을 실제 용량으로)
        if pg:
            lbl = b.get("label") or ("%gkg" % (pg / 1000) if pg >= 1000 else "%dg" % round(pg))
            c.execute("INSERT OR REPLACE INTO ingredient_pack(ingredient_key,qty,label) VALUES(?,?,?)",
                      (key, pg / 1000.0, lbl))
        c.commit(); c.close()
        return {"ok": True, "pack_g": pg}

    def _retail_none(self, b):
        # status: none = 쿠팡에 마땅한 상품 없음 / store = 매장 전용(집에서 안 사는 것)
        #  치킨무·곁들임·포장류는 "집에서 만들면" 원가에 넣을 필요가 없다(대표 지적 2026-07-26).
        stt = b.get("status") if b.get("status") in ("none", "store") else "none"
        c = conn()
        c.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,status,decided_at) VALUES(?,?,?)""", (b["key"], stt, st.now()))
        c.commit(); c.close()
        return {"ok": True, "status": stt}

    def _mi_remove(self, b):
        """그 메뉴에서 이 재료 라인을 뻐다.

        같은 재료가 어떤 메뉴에는 맞고 어떤 메뉴에는 안 맞는다
        (시럽은 설뱅엔 맞지만 핫도그에는 설탕이다 — 대표 지적 2026-07-26).
        그래서 메뉴별로 뻐낸다.
        """
        mid, key = int(b["menu_id"]), b["key"]
        c = conn()
        row = c.execute("""SELECT m.name mn, b.name br, i.name inm,
                   mi.amount, mi.unit, mi.sort_order, mi.composition
            FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
            JOIN brands b ON b.id=m.brand_id JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
            WHERE mi.menu_id=? AND mi.ingredient_key=?""", (mid, key)).fetchone()
        if not row:
            c.close()
            return {"ok": False, "error": "없는 라인"}
        # 🔴 지우기 전에 보관한다 — 되돌릴 수 없으면 사고가 된다(버거킹 불고기와퍼 사례)
        c.execute("""INSERT INTO mi_removed
            (menu_id,ingredient_key,amount,unit,sort_order,composition,removed_at)
            VALUES(?,?,?,?,?,?,?)""",
                  (mid, key, row["amount"], row["unit"], row["sort_order"],
                   row["composition"], st.now()))
        c.execute("DELETE FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?", (mid, key))
        c.commit(); c.close()
        return {"ok": True, "menu": row["br"] + " " + row["mn"], "ing": row["inm"],
                "menu_id": mid, "key": key}

    def _mi_restore(self, b):
        """뺀 라인을 되살린다."""
        mid, key = int(b["menu_id"]), b["key"]
        c = conn()
        r = c.execute("""SELECT * FROM mi_removed WHERE menu_id=? AND ingredient_key=?
                         ORDER BY id DESC LIMIT 1""", (mid, key)).fetchone()
        if not r:
            c.close()
            return {"ok": False, "error": "보관된 기록이 없습니다"}
        c.execute("""INSERT OR REPLACE INTO menu_ingredients
            (menu_id,ingredient_key,amount,unit,sort_order,composition)
            VALUES(?,?,?,?,?,?)""",
                  (mid, key, r["amount"], r["unit"], r["sort_order"], r["composition"]))
        c.execute("DELETE FROM mi_removed WHERE id=?", (r["id"],))
        c.commit(); c.close()
        return {"ok": True}

    def _ing_rename2(self, b):
        """재료명 수정 — 제품명·용량을 떼고 품목명만 남긴다(대표 지시 2026-07-26).

        ⚠️ 이름을 바꿀 때 같이 봐야 하는 곳(CLAUDE.md):
           recipe_steps · composition · dish_def.match_pattern · price_<이름>.html 고아파일
           앞의 둘은 여기서 자동 처리한다. 뒤의 둘은 재생성 때 정리된다.
        """
        key, new = b["key"], (b.get("name") or "").strip()
        if not new:
            return {"ok": False, "error": "이름이 비었습니다"}
        c = conn()
        old = c.execute("SELECT name FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
        if not old:
            c.close()
            return {"ok": False, "error": "없는 재료"}
        old = old[0]
        dup = c.execute("SELECT ingredient_key FROM ingredients WHERE name=? AND ingredient_key<>?",
                        (new, key)).fetchone()
        c.execute("UPDATE ingredients SET name=?, updated_at=? WHERE ingredient_key=?",
                  (new, st.now()[:10], key))
        n1 = c.execute("UPDATE menus SET recipe_steps=REPLACE(recipe_steps,?,?) "
                       "WHERE recipe_steps LIKE ?", (old, new, "%" + old + "%")).rowcount
        n2 = c.execute("UPDATE menu_ingredients SET composition=REPLACE(composition,?,?) "
                       "WHERE composition LIKE ?", (old, new, "%" + old + "%")).rowcount
        c.commit(); c.close()
        return {"ok": True, "old": old, "new": new, "recipe": n1, "comp": n2,
                "dup": (dup[0] if dup else None)}

    def _ing_delete(self, b):
        """재료 자체를 지운다(placeholder 들). 쓰는 메뉴 라인도 보관 후 삭제."""
        key = b["key"]
        c = conn()
        nm = c.execute("SELECT name FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
        if not nm:
            c.close()
            return {"ok": False, "error": "없는 재료"}
        for r in c.execute("SELECT * FROM menu_ingredients WHERE ingredient_key=?", (key,)).fetchall():
            c.execute("""INSERT INTO mi_removed
                (menu_id,ingredient_key,amount,unit,sort_order,composition,removed_at)
                VALUES(?,?,?,?,?,?,?)""",
                      (r["menu_id"], key, r["amount"], r["unit"], r["sort_order"],
                       r["composition"], st.now()))
        n = c.execute("DELETE FROM menu_ingredients WHERE ingredient_key=?", (key,)).rowcount
        c.execute("DELETE FROM ingredient_retail WHERE ingredient_key=?", (key,))
        c.execute("DELETE FROM ingredient_pack WHERE ingredient_key=?", (key,))
        c.execute("DELETE FROM ingredients WHERE ingredient_key=?", (key,))
        c.commit(); c.close()
        return {"ok": True, "name": nm[0], "lines": n}

    def _retail_research(self, b):
        """검색어를 직접 넣어 다시 찾는다 — 로켓 없음 98종을 살리는 수단."""
        key, kw = b["key"], (b.get("keyword") or "").strip()
        if not kw:
            return {"ok": False, "error": "검색어를 넣어주세요"}
        try:
            sys.path.insert(0, os.path.join(BASE, "scripts"))
            import retail_fill as RF
            from mealkit_run import load_env
        except Exception as e:
            return {"ok": False, "error": str(e)[:80]}
        env = load_env()
        ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")
        fp = RF.cpath(kw)
        if os.path.exists(fp):
            items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
        else:
            try:
                d = RF.CI.api_search(kw, ak, sk)
            except Exception as e:
                return {"ok": False, "error": "호출실패 " + str(e)[:60]}
            if d.get("rCode") not in (0, "0"):
                return {"ok": False, "error": "rCode=%s" % d.get("rCode")}
            items = (d.get("data") or {}).get("productData") or []
            io.open(fp, "w", encoding="utf-8").write(
                json.dumps({"keyword": kw, "items": items}, ensure_ascii=False))
        c = conn()
        rej = {r[0] for r in c.execute(
            "SELECT product_id FROM retail_rejected WHERE ingredient_key=?", (key,))}
        cands = [p for p in items if p.get("productPrice") and p.get("isRocket")
                 and p.get("productId") not in rej and RF.is_food(p)
                 and not RF.JUNK.search(p.get("productName") or "")]
        cands.sort(key=lambda p: p["productPrice"])
        if not cands:
            c.close()
            return {"ok": True, "found": 0, "keyword": kw}
        n = cands[0]
        c.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                  (key, n.get("productId"), n["productName"], n["productPrice"],
                   RF.pack_g(n["productName"]), n.get("productImage"), n.get("productUrl")))
        c.commit(); c.close()
        return {"ok": True, "found": len(cands), "keyword": kw,
                "name": n["productName"], "price": n["productPrice"]}

    def _retail_reject(self, b):
        """매칭 미인정 — 그 상품을 기억해 다시 안 뽑고, **바로 다음 후보로 갈아끼운다.**

        🔴 반려만 하면 그 재료가 빈 채로 남는다(대표 지시 2026-07-26
           "매칭 미인정까지 넣어 새로 매칭 하는것 까지"). 그래서 즉시 교체한다.
        """
        key = b["key"]
        c = conn()
        row = c.execute("SELECT product_id, name, price FROM ingredient_retail WHERE ingredient_key=?",
                        (key,)).fetchone()
        if row and row["product_id"]:
            c.execute("""INSERT OR REPLACE INTO retail_rejected
                (ingredient_key,product_id,name,price,reason,rejected_at)
                VALUES(?,?,?,?,?,?)""",
                      (key, row["product_id"], row["name"], row["price"],
                       b.get("reason") or "매칭 미인정", st.now()))
        nm = c.execute("SELECT name FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
        rej = {r[0] for r in c.execute(
            "SELECT product_id FROM retail_rejected WHERE ingredient_key=?", (key,))}
        cands = _retail_cands(key, nm[0] if nm else "", rej)
        if not cands:
            c.execute("""UPDATE ingredient_retail SET product_id=NULL, name=?, price=NULL,
                pack_g=NULL, image=NULL, url=NULL, status='skip' WHERE ingredient_key=?""",
                      ("후보 소진 — 검색어를 넓혀 다시 찾아야 함", key))
            c.commit(); c.close()
            return {"ok": True, "next": None}
        n = cands[0]
        c.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                  (key, n["product_id"], n["name"], n["price"], n.get("pack_g"),
                   n.get("image"), n.get("url")))
        c.commit(); c.close()
        return {"ok": True, "next": n["name"], "price": n["price"], "left": len(cands) - 1}

    def _retail_swap(self, b):
        """대표가 후보 중 하나를 골라 매칭을 바꾼다(통과는 따로 누른다)."""
        key = b["key"]
        c = conn()
        c.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                  (key, b.get("product_id"), b.get("name"), b.get("price"), b.get("pack_g"),
                   b.get("image"), b.get("url")))
        c.commit(); c.close()
        return {"ok": True}




    def _retail_undo(self, b):
        c = conn()
        c.execute("DELETE FROM ingredient_retail WHERE ingredient_key=?", (b["key"],))
        c.commit(); c.close()
        return {"ok": True}

    # ── 결정 저장 ──
    def _pick(self, b):
        mid = int(b["menu_id"])
        c = conn()
        brand = c.execute("""SELECT b.name FROM menus m JOIN brands b ON b.id=m.brand_id
                             WHERE m.id=?""", (mid,)).fetchone()
        mt = "정품" if (brand and is_official(brand[0], b.get("name"))) else "대체"
        c.execute("""INSERT OR REPLACE INTO menu_mealkit
            (menu_id,product_id,name,price,rocket,image,url,match_type,status,decided_at)
            VALUES(?,?,?,?,?,?,?,?, 'ok', ?)""",
                  (mid, b.get("product_id"), b.get("name"), b.get("price"),
                   1 if b.get("rocket") else 0, b.get("image"), b.get("url"), mt, st.now()))
        c.commit(); c.close()
        return {"ok": True, "match_type": mt}

    def _none(self, b):
        mid = int(b["menu_id"])
        c = conn()
        c.execute("""INSERT OR REPLACE INTO menu_mealkit
            (menu_id,product_id,name,price,rocket,image,url,match_type,status,decided_at)
            VALUES(?,NULL,NULL,NULL,0,NULL,NULL,NULL,'none',?)""", (mid, st.now()))
        c.commit(); c.close()
        return {"ok": True}

    def _reject(self, b):
        mid, pid = int(b["menu_id"]), int(b["product_id"])
        c = conn()
        c.execute("INSERT OR REPLACE INTO mealkit_rejected(menu_id,product_id,rejected_at) "
                  "VALUES(?,?,?)", (mid, pid, st.now()))
        # 지운 게 현재 선택이면 선택도 해제
        c.execute("DELETE FROM menu_mealkit WHERE menu_id=? AND product_id=?", (mid, pid))
        c.commit(); c.close()
        return {"ok": True}

    def _undo(self, b):
        mid = int(b["menu_id"])
        c = conn()
        c.execute("DELETE FROM menu_mealkit WHERE menu_id=?", (mid,))
        c.commit(); c.close()
        return {"ok": True}

    def _unreject(self, b):
        """×로 지운 후보 되돌리기. 잘못 지웠을 때 복구용(2026-07-25 요청)."""
        mid = int(b["menu_id"])
        pid = b.get("product_id")
        c = conn()
        if pid is None:      # 그 메뉴의 지운 후보 전부 복구
            n = c.execute("DELETE FROM mealkit_rejected WHERE menu_id=?", (mid,)).rowcount
        else:
            n = c.execute("DELETE FROM mealkit_rejected WHERE menu_id=? AND product_id=?",
                          (mid, int(pid))).rowcount
        c.commit(); c.close()
        return {"ok": True, "restored": n}

    # ── 메뉴명 수정 ──
    def _rename(self, b):
        mid, new = int(b["menu_id"]), (b.get("name") or "").strip()
        if not new:
            return {"ok": False, "error": "이름이 비어 있습니다"}
        c = conn()
        old = c.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()
        if not old:
            c.close()
            return {"ok": False, "error": "없는 메뉴"}
        old = old[0]
        c.execute("UPDATE menus SET name=? WHERE id=?", (new, mid))
        # 레시피 본문에 옛 이름이 박혀 있으면 같이 고친다(생닭 사례처럼 문구가 남는다)
        c.execute("UPDATE menus SET recipe_steps=REPLACE(recipe_steps,?,?) "
                  "WHERE id=? AND recipe_steps LIKE ?", (old, new, mid, "%" + old + "%"))
        # 곁들임·양념 구성 라벨에도 메뉴명이 박힌다("순대정식 곁들임"). 여기도 같이 고친다.
        c.execute("UPDATE menu_ingredients SET composition=REPLACE(composition,?,?) "
                  "WHERE menu_id=? AND composition LIKE ?", (old, new, mid, "%" + old + "%"))
        c.execute("UPDATE menu_name_audit SET status='applied' WHERE menu_id=?", (mid,))
        c.commit(); c.close()
        return {"ok": True, "old": old, "new": new}

    def _dismiss(self, b):
        c = conn()
        c.execute("UPDATE menu_name_audit SET status='dismissed' WHERE menu_id=?",
                  (int(b["menu_id"]),))
        c.commit(); c.close()
        return {"ok": True}

    # ── 재료 수정 ──
    def _ing_update(self, b):
        """이름·도매가 수정. 근거(basis)는 반드시 남긴다 — 왜 그 값인지 못 잃는다."""
        key = b["key"]
        c = conn()
        cur = c.execute("SELECT name, wholesale_price, wholesale_basis FROM ingredients "
                        "WHERE ingredient_key=?", (key,)).fetchone()
        if not cur:
            c.close()
            return {"ok": False, "error": "없는 재료"}
        name = (b.get("name") or cur["name"]).strip()
        price = b.get("price")
        note = (b.get("note") or "").strip()
        sets, args = ["name=?"], [name]
        if price not in (None, ""):
            price = int(price)
            if price <= 0:
                c.close()
                return {"ok": False, "error": "가격은 0보다 커야 합니다"}
            basis = "관리자 수정 %s %s원/%s" % (STAMP_TODAY, format(price, ","),
                                             b.get("unit") or "kg")
            if note:
                basis += " — " + note
            basis += " | 이전: %s" % ((cur["wholesale_basis"] or "")[:80])
            sets += ["wholesale_price=?", "wholesale_basis=?"]
            args += [price, basis]
        sets.append("updated_at=?")
        args.append(STAMP_TODAY)
        args.append(key)
        c.execute("UPDATE ingredients SET %s WHERE ingredient_key=?" % ",".join(sets), args)
        c.commit(); c.close()
        return {"ok": True, "old_price": cur["wholesale_price"],
                "old_name": cur["name"], "name": name,
                "price": (price if price not in (None, "") else cur["wholesale_price"])}

    # ── 메뉴 검수 도장 ──
    #  양·부위는 사람만 판정할 수 있다. 찍은 건 목록에서 빼고 안 찍은 것만 본다.
    def _menu_verify(self, b):
        mid = int(b["menu_id"])
        note = (b.get("note") or "").strip()
        c = conn()
        if not c.execute("SELECT 1 FROM menus WHERE id=?", (mid,)).fetchone():
            c.close()
            return {"ok": False, "error": "없는 메뉴"}
        c.execute("INSERT OR REPLACE INTO menu_verified(menu_id,verified_at,note) VALUES(?,?,?)",
                  (mid, st.now(), note or None))
        c.commit(); c.close()
        return {"verified_at": st.now()}

    def _menu_unverify(self, b):
        """양·부위를 다시 고쳤으면 도장을 떼야 한다 — 안 떼면 '검수됨'이 거짓이 된다."""
        mid = int(b["menu_id"])
        c = conn()
        n = c.execute("DELETE FROM menu_verified WHERE menu_id=?", (mid,)).rowcount
        c.commit(); c.close()
        return {"removed": n}

    def _menu_price(self, b):
        mid, price = int(b["menu_id"]), int(b["price"])
        if price <= 0:
            return {"ok": False, "error": "가격은 0보다 커야 합니다"}
        c = conn()
        old = c.execute("SELECT sell_price FROM menus WHERE id=?", (mid,)).fetchone()
        if not old:
            c.close()
            return {"ok": False, "error": "없는 메뉴"}
        c.execute("UPDATE menus SET sell_price=? WHERE id=?", (price, mid))
        c.execute("UPDATE menu_name_audit SET status='applied' WHERE menu_id=?", (mid,))
        c.commit(); c.close()
        return {"ok": True, "old": old[0], "new": price}


if __name__ == "__main__":
    st.init()
    # 🔴 127.0.0.1 을 유지한다. 폰에서 쓰려면 같은 PC에서 cloudflared 를 띄워
    #    터널로 붙인다(cloudflared 가 localhost 로 접속하므로 0.0.0.0 이 필요 없다).
    #    0.0.0.0 으로 열면 같은 공유기의 아무 기기나 비번만 뚫으면 DB를 쓴다.
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H) as srv:
        print("관리자 뒷단: http://127.0.0.1:%d/menus" % PORT)
        print("  비밀번호: .env 의 OLMANAMA_ADMIN_PW (미설정 시 0303)")
        print("  실패 %d회면 그 IP를 %d초 잠급니다. 서버를 재시작하면 전원 로그아웃됩니다."
              % (LOCK_AFTER, LOCK_SEC))
        print("  폰에서 쓰려면:  cloudflared tunnel --url http://localhost:%d" % PORT)
        print("  결정은 DB에 즉시 저장됩니다. Ctrl+C로 종료.")
        srv.serve_forever()
