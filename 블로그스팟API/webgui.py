# -*- coding: utf-8 -*-
"""방구석 관리자 — 로컬 웹 GUI (방침 v4, 2026-07-09).

실행: 방구석_관리자.bat 더블클릭 → 브라우저에서 http://localhost:8899
구조: 대시보드(/) → /blog (네이버 발행), /gems (비서 봇 모음), /iherb (아이허브 백페이지)

핵심 흐름 (네이버):
  재미나이(Gems) 출력물을 통째로 붙여넣기 → 자동 파싱(제목/태그/키워드/본문)
  → Blogspot 발행글과 키워드 자동 매칭 (없으면 "연결 대기")
  → 저장 리스트 → 다중선택 → 자동 날짜 배정 → Playwright 예약발행
"""

import os
import re
import json
import time
import threading
import webbrowser

from flask import Flask, request, jsonify, render_template_string, redirect

import naver_queue
from naver_export import text_to_naver_html, insert_images_into_body
from manager import load_github_config, upload_bytes_to_github, get_service, get_blog_id, fetch_all_posts

PORT = 8899
CONFIG_FILE = "webgui_config.json"
IHERB_FILE = "iherb_links.json"
IHERB_REWARD_CODE = "JUD1458"

app = Flask(__name__)

JOB = {"running": False, "log": []}
BLOGSPOT_CACHE = {"posts": [], "fetched_at": 0}


def job_log(msg):
    print(msg)
    JOB["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")


def load_config():
    cfg = {"gems_bots": []}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    if not cfg["gems_bots"]:
        # 기본 봇 목록 — 새 봇은 이 파일(webgui_config.json)에 항목만 추가하면 버튼이 자동 생성됨
        cfg["gems_bots"] = [{
            "category": "방구석 약국 봇",
            "name": "홈쇼핑 브릿지 글 작성 봇",
            "url": "https://gemini.google.com/gem/1IUpLIF7h_qVm4T6oaCukb0ZVsGzUiFCr?usp=sharing",
        }, {
            "category": "방구석 영양사 봇",
            "name": "(추후 추가 예정)",
            "url": "",
        }]
        save_config(cfg)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_iherb():
    if not os.path.exists(IHERB_FILE):
        return []
    with open(IHERB_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)
    # 예전에 id 없이 저장된 항목 하위호환 처리 (삭제 버튼이 동작하려면 id 필요)
    changed = False
    for i, it in enumerate(items):
        if not it.get("id"):
            it["id"] = f"legacy{i:03d}"
            changed = True
    if changed:
        save_iherb(items)
    return items


def save_iherb(items):
    with open(IHERB_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def iherb_reward_url(url):
    """아이허브 URL에 리워드코드를 붙인다."""
    url = url.split("?")[0].split("#")[0]
    return f"{url}?rcode={IHERB_REWARD_CODE}"


# ---------------------------------------------------------------------------
# Gems 출력물 통짜 파싱 — 사용자는 재미나이 결과를 그대로 붙여넣기만 하면 됨
# ---------------------------------------------------------------------------
_SECTION_RE = re.compile(r"^\[\s*([가-힣A-Za-z ]{1,15})\s*\]\s*$")
_BRIDGE_LINE_RE = re.compile(
    r"<?p?>?\s*더 자세한[^\n]*\[?방구석\s*약국\]?[^\n]*확인하세요\.?\s*(</p>)?\s*$")

_SECTION_MAP = {
    "제목": "title", "TITLE": "title",
    "태그": "tags", "해시태그": "tags", "TAGS": "tags",
    "키워드": "keyword", "매칭키워드": "keyword", "KEYWORD": "keyword",
    "라벨": "label", "카테고리": "label",
    "본문": "body", "BODY": "body",
    "요약정리표": "summary_table",
}


def _parse_bracket_sections(text):
    """[제목] / [매칭키워드] / [태그] / [본문] 대괄호 섹션 서식 파싱 (Gems 봇 실제 출력 서식)."""
    sections = {}
    current = None
    buf = []
    for line in text.split("\n"):
        m = _SECTION_RE.match(line.strip())
        key = None
        if m:
            name = m.group(1).strip()
            key = _SECTION_MAP.get(name) or _SECTION_MAP.get(name.upper())
        if key:
            if current:
                sections[current] = "\n".join(buf).strip()
            current = key
            buf = []
        elif current is not None:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


def parse_gems_output(text):
    """재미나이(Gems) 출력물을 통째로 받아 제목/태그/키워드/본문으로 분리한다.

    지원 서식 두 가지 (자동 감지, 관대하게 파싱):
    1) 대괄호 섹션: [제목] / [매칭키워드] / [태그] / [라벨] / [요약정리표] / [본문]
    2) 콜론 라벨: 제목: ... / 태그: ... / 키워드: ... / 본문 이후 전부
    공통: 본문 끝의 "#태그" 줄 흡수, "[방구석 약국] 링크에서 확인하세요" 문장은
    제거(발행 시 실제 URL 링크로 자동 삽입되므로 중복 방지).
    """
    text = text.strip()

    # ── 서식 1: 대괄호 섹션 ──
    if re.search(r"^\[\s*(제목|본문)\s*\]\s*$", text, re.MULTILINE):
        sec = _parse_bracket_sections(text)
        raw_tags = sec.get("tags", "").strip()
        # 쉼표가 있으면 쉼표로만 분리 (상품명처럼 공백 포함 태그 보존), 없으면 #/공백 분리
        if "," in raw_tags:
            tags = [t.strip("# ").strip() for t in raw_tags.split(",") if t.strip("# ").strip()]
        else:
            tags = [t.strip("#, ") for t in re.split(r"[\s]+", raw_tags) if t.strip("#, ")]
        body = sec.get("body", "")
        if sec.get("summary_table"):
            body = sec["summary_table"] + "\n\n" + body
        body = _BRIDGE_LINE_RE.sub("", body).strip()
        seen = set()
        tags = [t for t in tags if not (t in seen or seen.add(t))]
        return {"title": sec.get("title", ""), "tags": tags,
                "keyword": sec.get("keyword", ""), "body": body,
                "label": sec.get("label", "")}

    # ── 서식 2: 콜론 라벨 ──
    title, tags, keyword = "", [], ""
    body_lines = []
    consumed_body_label = False

    lines = text.split("\n")
    i = 0
    # 앞부분 라벨 스캔 (최대 앞 12줄 안에서)
    while i < len(lines):
        line = lines[i].strip()
        low = line.replace(" ", "")
        if i < 12 and re.match(r"^(제목|TITLE)\s*[:：]", line, re.IGNORECASE):
            title = re.split(r"[:：]", line, 1)[1].strip().strip('"')
        elif i < 12 and re.match(r"^(태그|해시태그|TAGS)\s*[:：]", line, re.IGNORECASE):
            raw = re.split(r"[:：]", line, 1)[1]
            tags += [t.strip("#, ") for t in re.split(r"[,\s]+", raw) if t.strip("#, ")]
        elif i < 12 and re.match(r"^(키워드|매칭키워드|KEYWORD)\s*[:：]", line, re.IGNORECASE):
            keyword = re.split(r"[:：]", line, 1)[1].strip()
        elif re.match(r"^(본문|BODY)\s*[:：]?\s*$", line, re.IGNORECASE):
            consumed_body_label = True
            body_lines = lines[i + 1:]
            break
        elif line == "---":
            body_lines = lines[i + 1:]
            break
        else:
            if line or body_lines:
                body_lines.append(lines[i])
        i += 1
    else:
        pass  # 라벨 없이 끝까지 감

    if not consumed_body_label and not body_lines:
        body_lines = lines

    body = "\n".join(body_lines).strip()

    # 제목 라벨이 없었으면 첫 줄을 제목으로
    if not title:
        first, _, rest = body.partition("\n")
        if first.strip():
            title = first.strip().strip('"#').strip()
            body = rest.strip()

    # 본문 끝의 해시태그 줄 흡수
    m = re.search(r"\n\s*((?:#[^\s#]+\s*){2,})\s*$", body)
    if m:
        tags += [t.strip("#") for t in m.group(1).split() if t.strip("#")]
        body = body[:m.start()].strip()

    # 중복 제거 (순서 유지)
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]

    body = _BRIDGE_LINE_RE.sub("", body).strip()
    return {"title": title, "tags": tags, "keyword": keyword, "body": body, "label": ""}


def get_blogspot_posts(force=False):
    """발행된 Blogspot 글 목록 (제목+URL) — 드롭다운 연결용. 10분 캐시."""
    if not force and BLOGSPOT_CACHE["posts"] and time.time() - BLOGSPOT_CACHE["fetched_at"] < 600:
        return BLOGSPOT_CACHE["posts"]
    service = get_service()
    blog_id = get_blog_id(service)
    posts = fetch_all_posts(service, blog_id, fetch_bodies=False)
    result = [{"title": p["title"], "url": p["url"]} for p in posts]
    BLOGSPOT_CACHE["posts"] = result
    BLOGSPOT_CACHE["fetched_at"] = time.time()
    return result


def match_blogspot_url(keyword):
    """키워드로 Blogspot 글을 찾는다 (제목에 키워드 포함, 가장 위 항목)."""
    if not keyword:
        return ""
    kn = keyword.replace(" ", "")
    for p in get_blogspot_posts():
        if kn in p["title"].replace(" ", ""):
            return p["url"]
    return ""


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
BASE_CSS = """
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Malgun Gothic', sans-serif; margin: 0; background: #f4f6f8; color: #222; }
  header { background: #25a186; color: #fff; padding: 14px 24px; display: flex; align-items: center; gap: 18px; }
  header a { color: #fff; text-decoration: none; font-weight: bold; }
  header nav a { font-weight: normal; font-size: 14px; opacity: .9; margin-right: 12px; }
  main { max-width: 1050px; margin: 24px auto; padding: 0 16px; }
  .cards { display: flex; gap: 16px; flex-wrap: wrap; }
  .card { background: #fff; border-radius: 10px; padding: 20px; width: 310px;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  .card h3 { margin-top: 0; }
  .btn { display: inline-block; background: #25a186; color: #fff; border: none; border-radius: 6px;
         padding: 9px 16px; font-size: 14px; cursor: pointer; text-decoration: none; }
  .btn.gray { background: #888; } .btn.small { padding: 4px 10px; font-size: 12px; }
  .btn:disabled { background: #bbb; cursor: default; }
  table { width: 100%; border-collapse: collapse; background: #fff; }
  th, td { padding: 9px 10px; border-bottom: 1px solid #eee; font-size: 14px; text-align: left; }
  th { background: #fafafa; }
  .panel { background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 20px;
           box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  input[type=text], textarea, select { width: 100%; padding: 8px; border: 1px solid #ccc;
      border-radius: 6px; font-family: inherit; font-size: 14px; }
  textarea { min-height: 260px; }
  label { font-size: 13px; color: #555; display: block; margin: 10px 0 4px; }
  #joblog { background: #111; color: #9f9; font-family: Consolas, monospace; font-size: 12px;
            padding: 12px; border-radius: 8px; height: 160px; overflow-y: auto; white-space: pre-wrap; }
  .tag { display: inline-block; background: #e8f5f1; color: #1b7d68; border-radius: 4px;
         padding: 2px 8px; font-size: 12px; margin: 1px; }
  .status-ready { color: #b80; } .status-scheduled { color: #17862c; } .status-pending { color: #c33; } .status-live { color: #0a5; font-weight:bold; }
  .stat { font-size: 26px; font-weight: bold; color: #25a186; }
  h4.cat { margin: 18px 0 8px; color: #1b7d68; }
</style>
"""

NAV = """
<header><a href="/">🏠 방구석 관리자</a>
<nav><a href="/register">📝 글 등록</a><a href="/bots">💎 비서 봇</a><a href="/iherb">🌿 아이허브</a></nav>
</header>
"""

PLATFORM_TOGGLE = """
<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">
  <span style="font-size:13px;color:#777;">등록 대상:</span>
  <button class="btn" id="tab_naver" onclick="switchPlatform('naver')" style="padding:8px 18px;">📝 네이버</button>
  <button class="btn gray" id="tab_blogspot" onclick="switchPlatform('blogspot')" style="padding:8px 18px;">📊 Blogspot</button>
</div>
"""

# 네이버/Blogspot 공용 등록 폼 — 입력창·이미지 업로드는 공통, 플랫폼 선택은 "어디로 보낼지"만 결정
UNIFIED_REGISTER_PANEL = """
<div class="panel">
  <h3>새 글 등록 <span id="reg_hint" style="font-size:12px;color:#888;"></span></h3>
  <div id="reg_blogspot_notice" style="display:none;font-size:13px;color:#999;margin-bottom:8px;line-height:1.6;">
    새 글 등록(insert)이 막혀 있어 아래 <b>대상 임시N 글</b>이 있어야 등록할 수 있습니다.
    없으면 Blogger 대시보드에서 "임시N" 제목으로 하나 발행한 뒤 새로고침하세요.
  </div>
  <div id="reg_blogspot_target" style="display:none;">
    <label>대상 임시N 글</label>
    <select id="reg_target"><option value="">-- 새로고침해서 불러오기 --</option></select>
  </div>
  <label id="reg_raw_label">내용 붙여넣기</label>
  <textarea id="reg_raw" style="min-height:260px;font-family:Consolas,monospace;font-size:13px;"></textarea>
  <label>이미지 최대 6장 (첫 번째가 썸네일 — 없어도 등록 가능, 네이버/Blogspot 공통)</label>
  <input type="file" id="reg_images" multiple accept="image/*">
  <div id="reg_blogspot_pipeline" style="display:none;">
    <label style="display:flex;align-items:center;gap:6px;margin-top:8px;">
      <input type="checkbox" id="reg_pipeline" checked style="width:auto;">
      표준 서식 자동 적용 (구매안내 삽입, 관련글 자동링크, 쿠팡 링크/고지문구 심사기간 숨김)
    </label>
  </div>
  <div style="margin-top:12px;">
    <button class="btn" id="reg_submit_btn" onclick="registerUnified()">등록</button>
    <span id="regmsg" style="margin-left:10px;font-size:13px;"></span>
  </div>
</div>
<script>
const REG_PLACEHOLDERS = {
  naver: '제목: ...\\n태그: #태그1 #태그2\\n키워드: 오메가3\\n\\n본문 내용...\\n\\n(서식이 조금 달라도 자동으로 인식합니다)',
  blogspot: 'TITLE: 글 제목\\nLABELS: 라벨1, 라벨2\\n---\\n본문 HTML...',
};

function switchPlatform(p) {
  document.getElementById('tab_naver').className = (p === 'naver') ? 'btn' : 'btn gray';
  document.getElementById('tab_blogspot').className = (p === 'blogspot') ? 'btn' : 'btn gray';
  localStorage.setItem('bp_platform', p);

  const isBs = p === 'blogspot';
  document.getElementById('reg_blogspot_notice').style.display = isBs ? 'block' : 'none';
  document.getElementById('reg_blogspot_target').style.display = isBs ? 'block' : 'none';
  document.getElementById('reg_blogspot_pipeline').style.display = isBs ? 'block' : 'none';
  document.getElementById('reg_raw_label').textContent = isBs
    ? '붙여넣기 (형식: TITLE: .. / LABELS: .., .. / --- / 본문)'
    : '재미나이 출력물 (전체 복사 → 붙여넣기)';
  document.getElementById('reg_raw').placeholder = REG_PLACEHOLDERS[p];
  document.getElementById('reg_hint').textContent = isBs
    ? '— 비교글 봇 출력을 붙여넣으면 서식까지 자동 적용'
    : '— 재미나이(Gems) 출력물을 통째로 붙여넣으세요. 제목/태그/키워드/본문 자동 분리';
  document.getElementById('reg_submit_btn').textContent = isBs ? '등록' : '저장 리스트에 등록';
}

async function registerUnified() {
  const p = localStorage.getItem('bp_platform') || 'naver';
  const msg = document.getElementById('regmsg');
  const raw = document.getElementById('reg_raw').value.trim();
  if (!raw) { msg.textContent = '붙여넣을 내용이 없습니다.'; return; }

  const fd = new FormData();
  fd.append('raw', raw);
  for (const f of document.getElementById('reg_images').files) fd.append('images', f);

  if (p === 'blogspot') {
    const targetId = document.getElementById('reg_target').value;
    if (!targetId) { msg.textContent = '대상 임시N 글을 선택하세요.'; return; }
    fd.append('id', targetId);
    fd.append('pipeline', document.getElementById('reg_pipeline').checked ? 'true' : 'false');
    msg.textContent = '등록 중... (이미지 업로드 + 관련글 링크 조회, 몇 초 걸릴 수 있음)';
    const res = await fetch('/api/blogspot/register', { method: 'POST', body: fd });
    const out = await res.json();
    msg.textContent = out.ok ? `등록 완료! (${out.title})` : ('실패: ' + out.error);
    if (out.ok) {
      document.getElementById('reg_raw').value = '';
      document.getElementById('reg_images').value = '';
      loadUnified();
    }
  } else {
    msg.textContent = '등록 중... (이미지 업로드 포함, 잠시 걸릴 수 있음)';
    const res = await fetch('/api/naver/add', { method: 'POST', body: fd });
    const out = await res.json();
    if (out.ok) {
      msg.textContent = `등록 완료! 제목: "${out.parsed.title}" / 태그 ${out.parsed.tags.length}개`
        + (out.parsed.blogspot_url ? ' / 약국 글 자동연결됨' : ' / ⚠ 연결 대기 (목록에서 연결하세요)');
      document.getElementById('reg_raw').value = '';
      document.getElementById('reg_images').value = '';
      loadUnified();
    } else { msg.textContent = '실패: ' + out.error; }
  }
}

switchPlatform(localStorage.getItem('bp_platform') || 'naver');
</script>
"""

# 네이버+Blogspot 공용 관리 UI (통합 목록 + 공용 상세/수정 패널 + 로그) — 플랫폼 구분 없이 한 화면
UNIFIED_MANAGE_PANEL = """
<div class="panel" style="border-left:4px solid #d33;">
  <h3 style="margin-top:0;">⛔ 안내</h3>
  <p style="font-size:14px;color:#555;line-height:1.6;">
    Blogger 새 글 등록(insert)이 스팸 차단으로 막혀 있습니다 (2026-07-10 재확인, 403).
    Blogspot 새 글은 반드시 위에서 <b>대상 임시N 글</b>을 지정해서 등록해야 합니다.<br>
    참고: 퍼머링크(URL)는 글이 처음 만들어지는 순간 고정되며 API로 변경 불가 (2026-07-10 실측 확인).
  </p>
</div>

<div class="panel">
  <h3>등록 현황 <button class="btn small gray" onclick="loadUnified()">새로고침</button></h3>
  <table id="unitable">
    <thead><tr><th></th><th>플랫폼</th><th>제목</th><th>상태</th><th>일정</th><th>이미지</th><th>라벨/태그</th><th>연결</th><th></th></tr></thead>
    <tbody></tbody>
  </table>
  <div style="margin-top:12px;">
    <button class="btn" onclick="scheduleSelected()">선택한 네이버 글 발행 예약 (하루 1개씩 자동 배정)</button>
    <button class="btn gray" onclick="syncStatus(this)">네이버 발행 상태 확인 (RSS 대조)</button>
    <button class="btn gray" onclick="naverLogin(this)">네이버 로그인</button>
    <span id="schedmsg" style="margin-left:10px;font-size:13px;"></span>
  </div>
</div>

<div class="panel" id="detailpanel" style="display:none;">
  <h3>글 상세/수정 <span id="detailinfo" style="font-size:13px;color:#888;"></span></h3>
  <input type="hidden" id="d_platform"><input type="hidden" id="d_id">
  <label>제목</label><input type="text" id="d_title">
  <label>태그/라벨 (쉼표로 구분)</label><input type="text" id="d_labels">
  <label>본문 (HTML)</label>
  <textarea id="d_body" style="min-height:300px;font-family:Consolas,monospace;font-size:13px;"></textarea>

  <div id="d_naver_extra" style="display:none;font-size:13px;color:#777;margin-top:8px;">
    키워드: <span id="d_keyword">-</span> · 방구석 약국 연결: <span id="d_connect">-</span>
    <div style="margin-top:12px;">
      <button class="btn" onclick="saveDetail(false)">저장 (로컬만)</button>
      <button class="btn red" id="d_pushbtn" onclick="saveDetail(true)" style="display:none;">저장 후 네이버에 수정 반영</button>
      <button class="btn red" onclick="deleteDetail()">삭제</button>
    </div>
  </div>

  <div id="d_blogspot_extra" style="display:none;margin-top:8px;">
    <label>발행 옵션</label>
    <select id="d_action">
      <option value="keep">현재 상태 유지하고 내용만 수정</option>
      <option value="publish_now">지금 즉시 발행 (LIVE 전환)</option>
      <option value="schedule">예약 시각 변경</option>
    </select>
    <div id="d_schedule_wrap" style="display:none;margin-top:8px;">
      <input type="text" id="d_schedule" placeholder="2026-07-15T15:00:00+09:00">
    </div>
    <div style="margin-top:12px;">
      <button class="btn" onclick="saveDetail(false)">저장</button>
      <button class="btn red" onclick="deleteDetail()">삭제 (휴지통으로 이동, 복구 가능)</button>
    </div>
  </div>

  <div style="margin-top:8px;">
    <button class="btn gray" onclick="document.getElementById('detailpanel').style.display='none'">닫기</button>
    <span id="detailmsg" style="margin-left:10px;font-size:13px;"></span>
  </div>
</div>

<div class="panel"><h3>작업 로그 <span style="font-size:12px;color:#888;">(예약 등록 중 Chrome 창이 뜨면 건드리지 마세요)</span></h3>
  <div id="joblog">대기 중...</div></div>

<script>
let UNI_ROWS = [];

async function loadUnified() {
  const res = await fetch('/api/unified/list');
  const data = await res.json();
  UNI_ROWS = data.rows;

  const tb = document.querySelector('#unitable tbody');
  tb.innerHTML = '';
  for (const r of UNI_ROWS) {
    const check = r.selectable ? `<input type="checkbox" class="uni-check" value="${r.id}">` : '';
    const platBadge = r.platform === 'naver' ? '📝 네이버' : '📊 Blogspot';
    const imgs = (r.images === null || r.images === undefined) ? '-' : r.images + '장';
    const conn = r.connected ? `<a href="${r.connected}" target="_blank" style="font-size:12px;">보기</a>` : '-';
    tb.innerHTML += `<tr>
      <td>${check}</td><td>${platBadge}</td><td>${r.title}</td><td>${r.status}</td>
      <td>${r.scheduled_at || '-'}</td><td>${imgs}</td>
      <td>${(r.labels||[]).map(l=>'<span class="tag">'+l+'</span>').join('')}</td>
      <td>${conn}</td>
      <td><button class="btn small gray" onclick="openDetail('${r.platform}','${r.id}')">상세</button></td>
    </tr>`;
  }

  // 붙여넣기 등록 폼의 "대상 임시N 글" 드롭다운도 같은 데이터로 채움
  const legacy = UNI_ROWS.filter(r => r.platform === 'blogspot' && r.legacy);
  const sel = document.getElementById('reg_target');
  sel.innerHTML = legacy.length
    ? '<option value="">선택하세요</option>' + legacy.map(r => `<option value="${r.id}">${r.title} (${r.status})</option>`).join('')
    : '<option value="">임시N 글 없음 — 대시보드에서 먼저 발행하세요</option>';
}

async function openDetail(platform, id) {
  document.getElementById('d_platform').value = platform;
  document.getElementById('d_id').value = id;
  document.getElementById('d_naver_extra').style.display = platform === 'naver' ? 'block' : 'none';
  document.getElementById('d_blogspot_extra').style.display = platform === 'blogspot' ? 'block' : 'none';
  const msg = document.getElementById('detailmsg');
  msg.textContent = '불러오는 중...';

  if (platform === 'naver') {
    const res = await fetch('/api/naver/get?id=' + id);
    const out = await res.json();
    if (!out.ok) { msg.textContent = out.error; return; }
    document.getElementById('d_title').value = out.post.title;
    document.getElementById('d_labels').value = out.post.tags.join(', ');
    document.getElementById('d_body').value = out.body;
    document.getElementById('d_keyword').textContent = out.post.keyword || '-';
    document.getElementById('d_connect').textContent = out.post.blogspot_url || '연결 안됨';
    const row = UNI_ROWS.find(r => r.platform === 'naver' && r.id === id);
    document.getElementById('detailinfo').textContent = row ? `(${row.status})` : '';
    document.getElementById('d_pushbtn').style.display = (row && row.status !== '대기' && row.status !== '연결 대기') ? 'inline-block' : 'none';
  } else {
    const res = await fetch('/api/blogspot/get?id=' + id);
    const out = await res.json();
    if (!out.ok) { msg.textContent = out.error; return; }
    document.getElementById('d_title').value = out.post.title;
    document.getElementById('d_labels').value = (out.post.labels || []).join(', ');
    document.getElementById('d_body').value = out.post.content;
    document.getElementById('detailinfo').textContent = `(현재 상태: ${out.post.status}, URL: ${out.post.url})`;
  }
  msg.textContent = '';
  document.getElementById('detailpanel').style.display = 'block';
  document.getElementById('detailpanel').scrollIntoView({behavior: 'smooth'});
}

document.getElementById('d_action').addEventListener('change', (e) => {
  document.getElementById('d_schedule_wrap').style.display = e.target.value === 'schedule' ? 'block' : 'none';
});

async function saveDetail(pushToNaver) {
  const platform = document.getElementById('d_platform').value;
  const id = document.getElementById('d_id').value;
  const msg = document.getElementById('detailmsg');
  const labels = document.getElementById('d_labels').value.split(',').map(t => t.trim()).filter(Boolean);
  const body = document.getElementById('d_body').value;
  const title = document.getElementById('d_title').value.trim();

  if (platform === 'naver') {
    msg.textContent = '저장 중...';
    const res = await fetch('/api/naver/update', { method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id, title, tags: labels, body }) });
    const out = await res.json();
    if (!out.ok) { msg.textContent = '실패: ' + out.error; return; }
    msg.textContent = '로컬 저장 완료';
    loadUnified();
    if (pushToNaver) {
      if (!confirm('네이버에 등록된 글을 이 내용으로 교체합니다.\\nChrome 창이 뜨면 건드리지 마세요. 진행할까요?')) return;
      msg.textContent = '네이버 수정 반영 중... (아래 작업 로그 확인)';
      const r2 = await fetch('/api/naver/push_edit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
      const o2 = await r2.json();
      msg.textContent = o2.ok ? '네이버 반영 작업 시작됨' : ('실패: ' + o2.error);
    }
  } else {
    const action = document.getElementById('d_action').value;
    const schedule = document.getElementById('d_schedule').value.trim();
    msg.textContent = '저장 중...';
    const res = await fetch('/api/blogspot/update', { method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id, title, labels, content: body, action, schedule }) });
    const out = await res.json();
    msg.textContent = out.ok ? '저장 완료!' : ('실패: ' + out.error);
    if (out.ok) loadUnified();
  }
}

async function deleteDetail() {
  const platform = document.getElementById('d_platform').value;
  const id = document.getElementById('d_id').value;
  const title = document.getElementById('d_title').value;
  const msg = document.getElementById('detailmsg');
  const row = UNI_ROWS.find(r => r.platform === platform && r.id === id);

  if (platform === 'naver') {
    if (row && row.status === '예약됨') {
      if (!confirm(`"${title}"\\n\\n네이버에 예약 등록된 글입니다.\\n네이버 예약발행 취소 + 목록 삭제를 자동으로 진행할까요?\\n(Chrome 창이 뜨면 건드리지 마세요)`)) return;
      msg.textContent = '예약 취소 작업 시작됨 — 아래 로그 확인';
      const res = await fetch('/api/naver/cancel_reservation', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
      const out = await res.json();
      if (!out.ok) msg.textContent = '실패: ' + out.error;
    } else {
      if (!confirm(`"${title}" 글을 저장 리스트에서 삭제할까요?`)) return;
      await fetch('/api/naver/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
    }
  } else {
    if (!confirm(`"${title}" 글을 휴지통으로 이동할까요? (다시 발행하면 복구 가능)`)) return;
    const res = await fetch('/api/blogspot/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
    const out = await res.json();
    if (!out.ok) { msg.textContent = '실패: ' + out.error; return; }
  }
  document.getElementById('detailpanel').style.display = 'none';
  loadUnified();
}

async function syncStatus(btn) {
  if (btn) btn.disabled = true;
  const msg = document.getElementById('schedmsg');
  msg.textContent = '네이버 RSS와 대조해서 실제 발행 여부 확인 중...';
  const res = await fetch('/api/naver/sync_status', { method: 'POST' });
  const out = await res.json();
  msg.textContent = out.ok ? `확인 완료 (${out.updated}건 URL 갱신)` : ('실패: ' + out.error);
  if (btn) btn.disabled = false;
  loadUnified();
}

async function naverLogin(btn) {
  btn.disabled = true;
  const msg = document.getElementById('schedmsg');
  msg.textContent = 'Chrome 창이 뜨면 네이버 로그인해주세요 ("로그인 상태 유지" 체크)...';
  const res = await fetch('/api/naver/login', { method: 'POST' });
  const out = await res.json();
  msg.textContent = out.ok ? '로그인 세션 저장 완료!' : ('실패: ' + out.error);
  btn.disabled = false;
}

async function scheduleSelected() {
  const ids = [...document.querySelectorAll('.uni-check:checked')].map(c => c.value);
  const msg = document.getElementById('schedmsg');
  if (!ids.length) { msg.textContent = '발행할 네이버 글을 체크하세요.'; return; }
  const res = await fetch('/api/naver/schedule', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ids })
  });
  const out = await res.json();
  if (!out.ok) { msg.textContent = '실패: ' + out.error; return; }
  if (!confirm('아래 일정으로 예약 등록할까요?\\n\\n' + out.plan.join('\\n')
               + '\\n\\nChrome 창이 뜨면 끝날 때까지 건드리지 마세요.')) {
    await fetch('/api/naver/cancel_assign', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ids }) });
    loadUnified(); return;
  }
  await fetch('/api/naver/run', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ids }) });
  msg.textContent = '예약 등록 작업 시작됨 — 아래 로그 확인';
  loadUnified();
}

setInterval(async () => {
  const res = await fetch('/api/naver/job_log');
  const data = await res.json();
  const el = document.getElementById('joblog');
  if (data.log.length) { el.textContent = data.log.join('\\n'); el.scrollTop = el.scrollHeight; }
}, 2000);

loadUnified();
</script>
"""

DASHBOARD_HTML = BASE_CSS + NAV + """
<main>
  <div class="cards">
    <div class="card"><h3>📝 글 등록 (네이버 / Blogspot)</h3>
      <div>네이버 대기 <span class="stat">{{ ready }}</span> · 예약됨 <span class="stat">{{ scheduled }}</span></div>
      <p style="font-size:13px;color:#777;">연결 대기(Blogspot 링크 없음): {{ pending }}건</p>
      <a class="btn" href="/register">열기</a></div>
    <div class="card"><h3>💎 비서 봇 (Gems)</h3>
      <p>카테고리별 Gems 바로가기 {{ bots }}개</p><a class="btn" href="/bots">열기</a></div>
    <div class="card"><h3>🌿 아이허브 정리</h3>
      <p>리워드 링크 관리 ({{ iherb }}건)</p><a class="btn" href="/iherb">열기</a></div>
    <div class="card"><h3>🛒 쇼핑 위젯 순위</h3>
      <p style="font-size:13px;color:#777;">네이버쇼핑 검색 인기순 데이터 갱신 (하루 1회 권장)</p>
      <button class="btn" onclick="updateWidget(this)">위젯 순위 갱신</button>
      <span id="widgetmsg" style="font-size:12px;margin-left:6px;"></span></div>
    <div class="card" style="opacity:.55;"><h3>🍱 식단 등록 (예정)</h3>
      <p>방구석 조리실 모듈</p><button class="btn gray" disabled>준비 중</button></div>
  </div>

  <div class="panel" style="margin-top:20px;">
    <h3>전체 등록 현황 <button class="btn small gray" onclick="loadStats()">새로고침</button></h3>
    <div class="cards" style="margin-bottom:14px;">
      <div class="card" style="width:220px;"><h3 style="margin-bottom:4px;">📝 네이버</h3>
        <div class="stat" id="stat_naver_total">-</div>
        <p style="font-size:12px;color:#777;margin:2px 0 0;">등록 <span id="stat_naver_ready">-</span> · 예약 <span id="stat_naver_scheduled">-</span></p></div>
      <div class="card" style="width:220px;"><h3 style="margin-bottom:4px;">📊 Blogspot</h3>
        <div class="stat" id="stat_bs_total">-</div>
        <p style="font-size:12px;color:#777;margin:2px 0 0;">공개 <span id="stat_bs_live">-</span> · 예약/초안 <span id="stat_bs_other">-</span></p></div>
    </div>
    <div style="margin-bottom:8px;">
      <select id="stat_filter" onchange="renderStatsTable()">
        <option value="all">전체 보기</option>
        <option value="naver">네이버만</option>
        <option value="blogspot">Blogspot만</option>
      </select>
    </div>
    <div style="max-height:360px;overflow-y:auto;border:1px solid #eee;border-radius:8px;">
      <table id="statstable" style="border-collapse:separate;border-spacing:0;">
        <thead><tr><th style="position:sticky;top:0;">플랫폼</th><th style="position:sticky;top:0;">제목</th>
          <th style="position:sticky;top:0;">상태</th><th style="position:sticky;top:0;">URL</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <script>
  async function updateWidget(btn) {
    btn.disabled = true;
    document.getElementById('widgetmsg').textContent = '갱신 중...';
    const res = await fetch('/api/widget/update', { method: 'POST' });
    const out = await res.json();
    document.getElementById('widgetmsg').textContent = out.ok ? '완료!' : ('실패: ' + out.error);
    btn.disabled = false;
  }
  </script>
  <div class="panel" style="margin-top:20px;">
    <h3>최근 저장된 콘텐츠 <button class="btn small gray" onclick="loadRecent()">새로고침</button></h3>
    <table><thead><tr><th>플랫폼</th><th>제목</th><th>상태</th><th>예약일시</th></tr></thead>
    <tbody id="recentbody"></tbody></table></div>
</main>
<script>
async function loadRecent() {
  const res = await fetch('/api/recent');
  const data = await res.json();
  const tb = document.getElementById('recentbody');
  tb.innerHTML = '';
  for (const p of data.posts) {
    const st = {ready: (p.blogspot_url ? '대기' : '연결 대기'), scheduled: '예약됨'}[p.status] || p.status;
    tb.innerHTML += `<tr><td>${p.platform}</td><td>${p.title}</td><td>${st}</td><td>${p.scheduled_at || '-'}</td></tr>`;
  }
}
loadRecent();

let STATS_ROWS = [];
async function loadStats() {
  const res = await fetch('/api/stats/all');
  const d = await res.json();
  document.getElementById('stat_naver_total').textContent = d.naver.total;
  document.getElementById('stat_naver_ready').textContent = d.naver.ready;
  document.getElementById('stat_naver_scheduled').textContent = d.naver.scheduled;
  document.getElementById('stat_bs_total').textContent = d.blogspot.total;
  document.getElementById('stat_bs_live').textContent = d.blogspot.live;
  document.getElementById('stat_bs_other').textContent = d.blogspot.other;
  STATS_ROWS = d.naver.list.map(x => ({platform: '네이버', ...x}))
    .concat(d.blogspot.list.map(x => ({platform: 'Blogspot', ...x})));
  renderStatsTable();
}
function renderStatsTable() {
  const filter = document.getElementById('stat_filter').value;
  const tb = document.querySelector('#statstable tbody');
  tb.innerHTML = '';
  const rows = STATS_ROWS.filter(r =>
    filter === 'all' || (filter === 'naver' && r.platform === '네이버') || (filter === 'blogspot' && r.platform === 'Blogspot'));
  for (const r of rows) {
    const url = r.url ? `<a href="${r.url}" target="_blank" style="font-size:12px;">${r.url}</a>` : '<span style="color:#bbb;">-</span>';
    tb.innerHTML += `<tr><td>${r.platform}</td><td>${r.title}</td><td>${r.status}</td><td>${url}</td></tr>`;
  }
  if (!rows.length) tb.innerHTML = '<tr><td colspan="4" style="color:#999;">없음</td></tr>';
}
loadStats();
setInterval(loadRecent, 10000);
</script>
"""

REGISTER_HTML = BASE_CSS + NAV + """
<main>
""" + PLATFORM_TOGGLE + UNIFIED_REGISTER_PANEL + UNIFIED_MANAGE_PANEL + """
</main>
"""

GEMS_HTML = BASE_CSS + NAV + """
<main>
  <div class="panel">
    <h3>💎 비서 봇 모음</h3>
    <p style="font-size:13px;color:#777;">새 봇 추가: webgui_config.json의 gems_bots에 항목만 추가하면 버튼이 자동 생성됩니다.</p>
    {% for cat, bots in categories.items() %}
      <h4 class="cat">{{ cat }}</h4>
      {% for b in bots %}
        {% if b.url %}<a class="btn" style="margin:3px;" href="{{ b.url }}" target="_blank">{{ b.name }}</a>
        {% else %}<button class="btn gray" style="margin:3px;" disabled>{{ b.name }}</button>{% endif %}
      {% endfor %}
    {% endfor %}
  </div>
</main>
"""

IHERB_HTML = BASE_CSS + NAV + """
<main>
  <div class="panel">
    <h3>🌿 아이허브 정리 (관리자 전용 — 네이버/블로그 본문에는 절대 사용 금지)</h3>
    <form method="post" action="/iherb/add">
      <label>아이허브 상품 URL</label>
      <input type="text" name="url" placeholder="https://kr.iherb.com/pr/..." required>
      <label>메모 (상품명/함유성분/가격 등)</label>
      <input type="text" name="memo" placeholder="예: 캘리포니아골드 오메가3 1000mg / 30,000원대">
      <button class="btn" style="margin-top:10px;">저장</button>
    </form>
  </div>
  <div class="panel">
    <table><thead><tr><th>메모</th><th>리워드 링크 (JUD1458)</th><th></th><th></th></tr></thead><tbody>
    {% for it in items %}
      <tr id="row_{{ it.id }}">
          <td>
            <span id="view_{{ it.id }}">{{ it.memo }}</span>
            <input id="input_{{ it.id }}" type="text" value="{{ it.memo }}" style="display:none;width:90%;">
          </td>
          <td style="font-size:12px;word-break:break-all;">{{ it.reward_url }}</td>
          <td><button class="btn small" onclick="navigator.clipboard.writeText('{{ it.reward_url }}');this.textContent='복사됨!'">복사</button></td>
          <td style="white-space:nowrap;">
            <button class="btn small gray" id="editbtn_{{ it.id }}" onclick="startEdit('{{ it.id }}')">수정</button>
            <button class="btn small" id="savebtn_{{ it.id }}" style="display:none;" onclick="saveMemo('{{ it.id }}')">저장</button>
            <form method="post" action="/iherb/delete" style="margin:0;display:inline;" onsubmit="return confirm('삭제할까요?\\n{{ it.memo }}');">
                <input type="hidden" name="id" value="{{ it.id }}">
                <button class="btn small red" type="submit">삭제</button>
            </form>
          </td></tr>
    {% endfor %}
    {% if not items %}<tr><td colspan="4" style="color:#999;">저장된 항목이 없습니다</td></tr>{% endif %}
    </tbody></table>
  </div>
</main>
<script>
function startEdit(id) {
  document.getElementById('view_' + id).style.display = 'none';
  document.getElementById('input_' + id).style.display = 'inline-block';
  document.getElementById('editbtn_' + id).style.display = 'none';
  document.getElementById('savebtn_' + id).style.display = 'inline-block';
  document.getElementById('input_' + id).focus();
}
async function saveMemo(id) {
  const memo = document.getElementById('input_' + id).value.trim();
  await fetch('/iherb/update', { method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id, memo }) });
  document.getElementById('view_' + id).textContent = memo;
  document.getElementById('view_' + id).style.display = 'inline';
  document.getElementById('input_' + id).style.display = 'none';
  document.getElementById('editbtn_' + id).style.display = 'inline-block';
  document.getElementById('savebtn_' + id).style.display = 'none';
}
</script>
"""


@app.route("/")
def dashboard():
    data = naver_queue.load_queue()
    posts = data["posts"]
    ready = sum(1 for p in posts if p["status"] == "ready")
    scheduled = sum(1 for p in posts if p["status"] == "scheduled")
    pending = sum(1 for p in posts if p["status"] == "ready" and not p.get("blogspot_url"))
    recent = list(reversed(posts))[:8]
    cfg = load_config()
    return render_template_string(
        DASHBOARD_HTML, ready=ready, scheduled=scheduled, pending=pending,
        bots=len([b for b in cfg["gems_bots"] if b.get("url")]),
        iherb=len(load_iherb()), recent=recent)


@app.route("/register")
@app.route("/naver")       # 구버전 경로 호환 -> 통합 페이지로
@app.route("/blog")        # 구버전 경로 호환
@app.route("/blogspot")    # 구버전 경로 호환
def register_page():
    return render_template_string(REGISTER_HTML)


@app.route("/bots")
@app.route("/gems")  # 구버전 경로 호환
def gems_page():
    cfg = load_config()
    categories = {}
    for b in cfg["gems_bots"]:
        categories.setdefault(b.get("category", "기타"), []).append(b)
    return render_template_string(GEMS_HTML, categories=categories)


@app.route("/iherb")
def iherb_page():
    return render_template_string(IHERB_HTML, items=load_iherb())


@app.route("/iherb/add", methods=["POST"])
def iherb_add():
    items = load_iherb()
    url = request.form.get("url", "").strip()
    if url:
        items.insert(0, {
            "id": time.strftime("%Y%m%d%H%M%S") + f"{len(items):03d}",
            "url": url,
            "memo": request.form.get("memo", "").strip() or url[:50],
            "reward_url": iherb_reward_url(url),
        })
        save_iherb(items)
    return redirect("/iherb")


@app.route("/iherb/update", methods=["POST"])
def iherb_update():
    b = request.get_json()
    items = load_iherb()
    for it in items:
        if it.get("id") == b.get("id"):
            it["memo"] = b.get("memo", it["memo"]).strip() or it["memo"]
    save_iherb(items)
    return jsonify({"ok": True})


@app.route("/iherb/delete", methods=["POST"])
def iherb_delete():
    target_id = request.form.get("id", "")
    items = [it for it in load_iherb() if it.get("id") != target_id]
    save_iherb(items)
    return redirect("/iherb")


@app.route("/api/widget/update", methods=["POST"])
def api_widget_update():
    try:
        from naver_widget import update_widget_data
        update_widget_data(log=job_log)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/stats/all")
def api_stats_all():
    """네이버/Blogspot 전체 등록 현황 (제목+URL+상태) — 대시보드 통합 카운트용."""
    # 네이버: 저장 리스트 기준 (등록=발행 전, 예약=네이버 예약발행 등록됨)
    naver_data = naver_queue.load_queue()
    naver_posts = naver_data["posts"]
    naver_ready = sum(1 for p in naver_posts if p["status"] == "ready")
    naver_scheduled = sum(1 for p in naver_posts if p["status"] == "scheduled")
    naver_list = [{
        "title": p["title"],
        "status": {"ready": "대기", "scheduled": "예약됨"}.get(p["status"], p["status"]),
        "url": p.get("naver_url") or "",
    } for p in naver_posts]

    # Blogspot: Blogger API 실시간 (LIVE/DRAFT/SCHEDULED 전체)
    try:
        service = get_service()
        blog_id = get_blog_id(service)
        bs_posts = fetch_all_posts(service, blog_id, fetch_bodies=False,
                                   statuses=["LIVE", "DRAFT", "SCHEDULED"])
        bs_live = sum(1 for p in bs_posts if p.get("status") == "LIVE")
        bs_other = len(bs_posts) - bs_live
        bs_list = [{
            "title": p["title"],
            "status": {"LIVE": "공개", "DRAFT": "초안", "SCHEDULED": "예약됨"}.get(p.get("status"), p.get("status", "")),
            "url": p.get("url") or "",
        } for p in bs_posts]
    except Exception as e:
        bs_live = bs_other = 0
        bs_list = []
        job_log(f"Blogspot 통계 조회 실패: {e}")

    return jsonify({
        "naver": {"total": len(naver_posts), "ready": naver_ready,
                  "scheduled": naver_scheduled, "list": naver_list},
        "blogspot": {"total": len(bs_list), "live": bs_live, "other": bs_other, "list": bs_list},
    })


@app.route("/api/recent")
def api_recent():
    data = naver_queue.load_queue()
    return jsonify({"posts": list(reversed(data["posts"]))[:8]})


@app.route("/api/blogspot/posts")
def api_blogspot_posts():
    try:
        return jsonify({"posts": get_blogspot_posts()})
    except Exception as e:
        return jsonify({"posts": [], "error": str(e)})


def _fetch_blogspot_admin_posts(force=False):
    """레거시 임시글 판정을 위해서만 fetchBodies=True로 (본문에서 실 내용 있는지 확인)."""
    service = get_service()
    blog_id = get_blog_id(service)
    posts = fetch_all_posts(service, blog_id, statuses=["LIVE", "DRAFT", "SCHEDULED"])
    return service, blog_id, posts


@app.route("/api/blogspot/list")
def api_blogspot_list():
    try:
        service, blog_id, posts = _fetch_blogspot_admin_posts()

        legacy = [{"id": p["id"], "title": p["title"], "status": p.get("status", ""),
                   "url": p.get("url", "")}
                  for p in posts if re.match(r"^임시\d+$", p["title"].strip())]

        not_live = [{"id": p["id"], "title": p["title"], "status": p.get("status", ""),
                     "published": (p.get("published") or "")[:16].replace("T", " "),
                     "labels": p.get("labels", [])}
                    for p in posts if p.get("status") != "LIVE"
                    and not re.match(r"^임시\d+$", p["title"].strip())]

        label_count = {}
        for p in posts:
            for l in p.get("labels", []):
                label_count.setdefault(l, {"count": 0, "statuses": set()})
                label_count[l]["count"] += 1
                label_count[l]["statuses"].add(p.get("status", ""))
        topics = [{"label": l, "count": v["count"], "statuses": sorted(v["statuses"])}
                  for l, v in sorted(label_count.items(), key=lambda x: -x[1]["count"])]

        return jsonify({"legacy": legacy, "posts": not_live, "topics": topics})
    except Exception as e:
        return jsonify({"legacy": [], "posts": [], "topics": [], "error": str(e)})


def _naver_display_status(p):
    has_real = p.get("naver_url") and re.search(r"blog\.naver\.com/[^/]+/\d+", p["naver_url"])
    if p["status"] == "ready":
        return "연결 대기" if not p.get("blogspot_url") else "대기"
    return "발행완료" if has_real else "예약됨"


@app.route("/api/unified/list")
def api_unified_list():
    """네이버 저장 리스트 + Blogspot 전체 글을 플랫폼 구분 없는 한 목록으로 합친다.

    프론트는 이 하나의 API만 써서 통합 테이블과 등록폼의 "대상 임시N 글" 드롭다운을
    동시에 채운다 (2026-07-11, 화면 통합 확정).
    """
    rows = []
    ndata = naver_queue.load_queue()
    for p in ndata["posts"]:
        rows.append({
            "platform": "naver", "id": p["id"], "title": p["title"],
            "status": _naver_display_status(p),
            "scheduled_at": p.get("scheduled_at"),
            "images": len(p.get("images", [])),
            "labels": p.get("tags", []),
            "connected": p.get("blogspot_url") or "",
            "selectable": p["status"] == "ready",
            "legacy": False,
        })

    try:
        service = get_service()
        blog_id = get_blog_id(service)
        bs_posts = fetch_all_posts(service, blog_id, fetch_bodies=False,
                                   statuses=["LIVE", "DRAFT", "SCHEDULED"])
        status_kr = {"LIVE": "공개", "DRAFT": "초안", "SCHEDULED": "예약됨"}
        for p in bs_posts:
            is_legacy = bool(re.match(r"^임시\d+$", p["title"].strip()))
            label = status_kr.get(p.get("status"), p.get("status", ""))
            rows.append({
                "platform": "blogspot", "id": p["id"], "title": p["title"],
                "status": label + (" (임시글)" if is_legacy else ""),
                "scheduled_at": (p.get("published") or "")[:16].replace("T", " "),
                "images": None,
                "labels": p.get("labels", []),
                "connected": p.get("url") or "",
                "selectable": False,
                "legacy": is_legacy,
            })
    except Exception as e:
        job_log(f"Blogspot 목록 조회 실패: {e}")

    return jsonify({"rows": rows})


@app.route("/api/blogspot/get")
def api_blogspot_get():
    try:
        service = get_service()
        blog_id = get_blog_id(service)
        from manager import execute_with_retry
        post = execute_with_retry(
            service.posts().get(blogId=blog_id, postId=request.args.get("id"), view="ADMIN"))
        return jsonify({"ok": True, "post": post})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


def _insert_blogspot_images(body, image_urls):
    """이미지들을 본문에 삽입하되, 맨 앞의 MOBILE_CSS_MARKER 블록은 건드리지 않는다.

    naver_export.insert_images_into_body()는 문서 맨 앞에 썸네일을 넣는데, Blogspot
    본문은 항상 <!-- MOBILE_FONT_CSS_V1 --><style>...</style>로 시작해야 하므로
    그 블록 뒤에 이미지를 끼워 넣는다 (재사용, 로직 중복 없음).
    """
    if not image_urls:
        return body
    from manager import MOBILE_CSS_MARKER
    if body.startswith(MOBILE_CSS_MARKER):
        idx = body.find("</style>") + len("</style>")
        return body[:idx] + insert_images_into_body(body[idx:], image_urls)
    return insert_images_into_body(body, image_urls)


@app.route("/api/blogspot/register", methods=["POST"])
def api_blogspot_register():
    """새 글 붙여넣기 등록 — TITLE:/LABELS:/---/본문 형식을 파싱해서 대상 임시N 글에 반영한다.

    insert()가 막혀 있어 새 post_id를 만들 수 없으므로, 반드시 이미 존재하는(수동 발행된)
    임시N 글을 target으로 지정해서 update()로 덮어쓰는 구조 (2026-07-10/11 확정 워크플로우).
    이미지는 네이버와 동일하게 GitHub 업로드 후 본문에 삽입 (2026-07-11 통합).
    """
    try:
        target_id = request.form.get("id", "")
        raw = request.form.get("raw", "").strip()
        use_pipeline = request.form.get("pipeline", "true") == "true"
        if not target_id or not raw:
            return jsonify({"ok": False, "error": "대상 글 또는 내용이 없습니다"})

        header, _, body = raw.partition("---")
        title, labels = "", []
        for line in header.strip().split("\n"):
            if line.strip().upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("LABELS:"):
                labels = [l.strip() for l in line.split(":", 1)[1].split(",") if l.strip()]
        body = body.strip()
        if not title or not body:
            return jsonify({"ok": False, "error": "TITLE 또는 본문(--- 아래)을 인식하지 못했습니다"})

        service = get_service()
        blog_id = get_blog_id(service)

        if use_pipeline:
            from manager import finalize_blogspot_content
            all_posts = fetch_all_posts(service, blog_id, fetch_bodies=False)
            body = finalize_blogspot_content(body, labels, all_posts)
        else:
            from manager import MOBILE_CSS_MARKER, MOBILE_CSS_BLOCK
            if not body.startswith(MOBILE_CSS_MARKER):
                body = MOBILE_CSS_BLOCK + body

        files = [f for f in request.files.getlist("images") if f and f.filename][:6]
        if files:
            github_cfg = load_github_config()
            stamp = time.strftime("%Y%m%d%H%M%S")
            image_urls = []
            for i, f in enumerate(files):
                ext = os.path.splitext(f.filename)[1].lower()
                if ext in ("", ".jfif"):
                    ext = ".jpg"
                url = upload_bytes_to_github(f.read(), f"bs_{stamp}_{i}{ext}", github_cfg)
                image_urls.append(url)
            body = _insert_blogspot_images(body, image_urls)

        from manager import execute_with_retry
        execute_with_retry(service.posts().update(
            blogId=blog_id, postId=target_id,
            body={"title": title, "content": body, "labels": labels}))

        return jsonify({"ok": True, "title": title})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/blogspot/delete", methods=["POST"])
def api_blogspot_delete():
    """Blogspot 글을 휴지통으로 이동한다 (posts().delete()는 소프트 삭제 —
    2026-07-10/11 확인: publish()를 다시 호출하면 복구 가능)."""
    try:
        from manager import execute_with_retry
        post_id = request.get_json().get("id", "")
        service = get_service()
        blog_id = get_blog_id(service)
        execute_with_retry(service.posts().delete(blogId=blog_id, postId=post_id))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/blogspot/update", methods=["POST"])
def api_blogspot_update():
    try:
        b = request.get_json()
        service = get_service()
        blog_id = get_blog_id(service)
        from manager import execute_with_retry, MOBILE_CSS_MARKER, MOBILE_CSS_BLOCK

        content = b.get("content", "")
        if not content.strip().startswith(MOBILE_CSS_MARKER):
            content = MOBILE_CSS_BLOCK + content

        body = {"title": b["title"], "content": content, "labels": b.get("labels", [])}
        execute_with_retry(service.posts().update(blogId=blog_id, postId=b["id"], body=body))

        action = b.get("action", "keep")
        if action == "publish_now":
            execute_with_retry(service.posts().publish(blogId=blog_id, postId=b["id"]))
        elif action == "schedule":
            sched = b.get("schedule", "").strip()
            if not sched:
                return jsonify({"ok": False, "error": "예약 시각을 입력하세요 (예: 2026-07-15T15:00:00+09:00)"})
            execute_with_retry(service.posts().revert(blogId=blog_id, postId=b["id"]))
            execute_with_retry(service.posts().publish(blogId=blog_id, postId=b["id"], publishDate=sched))

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/naver/queue")
def api_queue():
    data = naver_queue.load_queue()
    posts = [p for p in data["posts"] if p.get("platform", "naver") == "naver"]
    return jsonify({"posts": posts})


@app.route("/api/naver/set_link", methods=["POST"])
def api_set_link():
    body = request.get_json()
    naver_queue.set_blogspot_link(body["id"], body["url"])
    return jsonify({"ok": True})


@app.route("/api/naver/get")
def api_get_post():
    pid = request.args.get("id", "")
    data = naver_queue.load_queue()
    for p in data["posts"]:
        if p["id"] == pid:
            return jsonify({"ok": True, "post": p, "body": naver_queue.get_post_body(p)})
    return jsonify({"ok": False, "error": "글을 찾을 수 없습니다"})


@app.route("/api/naver/update", methods=["POST"])
def api_update_post():
    b = request.get_json()
    body = b.get("body", "")
    if re.search(r"link\.coupang\.com|iherb\.com", body, re.IGNORECASE):
        return jsonify({"ok": False, "error": "본문에 쇼핑몰 링크 포함 (네이버 글 규칙 위반)"})
    naver_queue.update_post_content(b["id"], title=b.get("title"),
                                    tags=b.get("tags"), body_html=body)
    return jsonify({"ok": True})


@app.route("/api/naver/push_edit", methods=["POST"])
def api_push_edit():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "다른 작업이 실행 중입니다"})
    pid = request.get_json()["id"]
    data = naver_queue.load_queue()
    target = next((p for p in data["posts"] if p["id"] == pid), None)
    if not target:
        return jsonify({"ok": False, "error": "글을 찾을 수 없습니다"})

    has_url = bool(target.get("naver_url")
                   and re.search(r"blog\.naver\.com/[^/]+/\d+", target["naver_url"]))
    is_scheduled = target["status"] == "scheduled" and target.get("scheduled_at")
    if not has_url and not is_scheduled:
        return jsonify({"ok": False, "error": "네이버에 등록된 글이 아닙니다 (발행 전 글은 로컬 저장만 하면 됩니다)"})

    JOB["running"] = True
    JOB["log"] = []

    def worker():
        try:
            body = naver_queue.get_post_body(target)
            if target.get("blogspot_url") and target["blogspot_url"] not in body:
                body += (f'\n<p><br></p>\n<p>더 자세한 브랜드별 비교표와 최저가는 '
                         f'<a href="{target["blogspot_url"]}">[방구석 약국]</a> 링크에서 확인하세요.</p>')
            if has_url:
                # 이미 공개된 글: 글 주소로 직접 수정
                from naver_publish import edit_naver_post
                edit_naver_post(target["naver_url"], target["title"], body, log=job_log)
            else:
                # 아직 공개 전(예약 상태): 예약 발행 목록에서 불러와 수정 + 예약 시각 유지
                import datetime as _dt
                from naver_publish import edit_scheduled_post
                dt = _dt.datetime.strptime(target["scheduled_at"], "%Y-%m-%d %H:%M")
                edit_scheduled_post(target["title"], target["title"], body, dt, log=job_log)
            job_log("=== 수정 반영 작업 종료 ===")
        except Exception as e:
            job_log(f"작업 오류: {e}")
        finally:
            JOB["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/naver/cancel_reservation", methods=["POST"])
def api_cancel_reservation():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "다른 작업이 실행 중입니다"})
    pid = request.get_json()["id"]
    data = naver_queue.load_queue()
    target = next((p for p in data["posts"] if p["id"] == pid), None)
    if not target:
        return jsonify({"ok": False, "error": "글을 찾을 수 없습니다"})

    JOB["running"] = True
    JOB["log"] = []

    def worker():
        try:
            from naver_publish import cancel_scheduled_post
            gone = cancel_scheduled_post(target["title"], log=job_log)
            if gone:
                naver_queue.delete_post(pid)
                job_log("저장 리스트에서도 삭제 완료")
            else:
                job_log("네이버 취소가 확인되지 않아 목록은 유지했습니다 — 확인 후 다시 시도하세요")
            job_log("=== 예약 취소 작업 종료 ===")
        except Exception as e:
            job_log(f"작업 오류: {e}")
        finally:
            JOB["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/naver/sync_status", methods=["POST"])
def api_sync_status():
    try:
        updated = naver_queue.sync_published_status(log=job_log)
        return jsonify({"ok": True, "updated": updated})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/naver/login", methods=["POST"])
def api_naver_login():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "발행 작업 실행 중"})
    try:
        from naver_publish import ensure_login
        ok = ensure_login(log=job_log, wait_minutes=10)
        return jsonify({"ok": ok, "error": "" if ok else "로그인 확인 실패 — 다시 시도해주세요"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/naver/delete", methods=["POST"])
def api_delete():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "발행 작업 실행 중에는 삭제할 수 없습니다"})
    naver_queue.delete_post(request.get_json()["id"])
    return jsonify({"ok": True})


@app.route("/api/naver/add", methods=["POST"])
def api_add():
    try:
        raw = request.form.get("raw", "").strip()
        if not raw:
            return jsonify({"ok": False, "error": "내용이 비어 있습니다"})

        parsed = parse_gems_output(raw)
        if not parsed["title"] or not parsed["body"]:
            return jsonify({"ok": False, "error": "제목/본문을 인식하지 못했습니다"})

        body = text_to_naver_html(parsed["body"])
        if re.search(r"link\.coupang\.com|iherb\.com", body, re.IGNORECASE):
            return jsonify({"ok": False, "error": "본문에 쇼핑몰 링크 포함 (네이버 글 규칙 위반)"})

        # Blogspot 글 자동 매칭 (키워드 기준) — 링크 자체는 발행 시점에 본문 끝에 붙는다
        blogspot_url = ""
        try:
            blogspot_url = match_blogspot_url(parsed["keyword"])
        except Exception:
            pass

        image_urls = []
        files = [f for f in request.files.getlist("images") if f and f.filename][:6]
        if files:
            github_cfg = load_github_config()
            stamp = time.strftime("%Y%m%d%H%M%S")
            for i, f in enumerate(files):
                ext = os.path.splitext(f.filename)[1].lower()
                if ext in ("", ".jfif"):
                    ext = ".jpg"
                url = upload_bytes_to_github(f.read(), f"nv_{stamp}_{i}{ext}", github_cfg)
                image_urls.append(url)
            body = insert_images_into_body(body, image_urls)

        naver_queue.add_post(parsed["title"], body, parsed["tags"], image_urls,
                             platform="naver", keyword=parsed["keyword"],
                             blogspot_url=blogspot_url)
        parsed["blogspot_url"] = blogspot_url
        return jsonify({"ok": True, "parsed": parsed})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/naver/schedule", methods=["POST"])
def api_schedule():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "이미 발행 작업이 실행 중입니다"})
    ids = request.get_json().get("ids", [])
    if len(ids) > naver_queue.MAX_BATCH:
        return jsonify({"ok": False, "error": f"한 번에 최대 {naver_queue.MAX_BATCH}개까지"})

    # 연결 대기(Blogspot 링크 없음) 글은 발행 불가 — 브릿지 글의 존재 이유가 그 링크이므로
    data = naver_queue.load_queue()
    by_id = {p["id"]: p for p in data["posts"]}
    no_link = [by_id[i]["title"] for i in ids if i in by_id and not by_id[i].get("blogspot_url")]
    if no_link:
        return jsonify({"ok": False, "error": "연결 대기 상태 글이 있습니다 (약국 글 연결 필요): " + ", ".join(no_link)})

    assigned = naver_queue.assign_schedule_dates(ids)
    if not assigned:
        return jsonify({"ok": False, "error": "배정 가능한(대기 상태) 글이 없습니다"})
    plan = [f"{e['title'][:30]} → {dt.strftime('%m/%d %H:%M')}" for e, dt in assigned]
    return jsonify({"ok": True, "plan": plan})


@app.route("/api/naver/cancel_assign", methods=["POST"])
def api_cancel_assign():
    for pid in request.get_json().get("ids", []):
        naver_queue.unassign(pid)
    return jsonify({"ok": True})


@app.route("/api/naver/run", methods=["POST"])
def api_run():
    if JOB["running"]:
        return jsonify({"ok": False, "error": "이미 실행 중"})
    ids = request.get_json().get("ids", [])
    data = naver_queue.load_queue()
    import datetime as _dt
    targets = []
    for p in data["posts"]:
        if p["id"] in ids and p.get("scheduled_at") and p["status"] == "ready":
            dt = _dt.datetime.strptime(p["scheduled_at"], "%Y-%m-%d %H:%M")
            targets.append((p, dt))
    if not targets:
        return jsonify({"ok": False, "error": "예약일시가 배정된 글이 없습니다"})

    JOB["running"] = True
    JOB["log"] = []

    def worker():
        try:
            from naver_publish import batch_register_scheduled
            entries = []
            for p, dt in targets:
                body = naver_queue.get_post_body(p)
                # 연결 링크는 발행 시점에 본문 끝에 붙인다 (연결 대기 -> 나중 연결 흐름 지원)
                if p.get("blogspot_url") and p["blogspot_url"] not in body:
                    body += (f'\n<p><br></p>\n<p>더 자세한 브랜드별 비교표와 최저가는 '
                             f'<a href="{p["blogspot_url"]}">[방구석 약국]</a> 링크에서 확인하세요.</p>')

                def make_cb(pid):
                    def cb(ok, url):
                        if ok:
                            # 예약 등록 시 글이 아직 공개 전이라 실제 글 주소가 안 잡힐 수 있음 —
                            # 진짜 글 주소 형식(blog.naver.com/아이디/숫자)일 때만 저장
                            valid = url if url and re.search(r"blog\.naver\.com/[^/]+/\d+", url) else None
                            naver_queue.mark_registered(pid, valid)
                        else:
                            naver_queue.unassign(pid)
                    return cb
                entries.append((p["title"], body, p["tags"], dt, make_cb(p["id"])))
            batch_register_scheduled(entries, log=job_log)
            job_log("=== 예약 등록 작업 종료 ===")
        except Exception as e:
            job_log(f"작업 오류: {e}")
        finally:
            JOB["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/naver/job_log")
def api_job_log():
    return jsonify({"running": JOB["running"], "log": JOB["log"][-200:]})


if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    print(f"방구석 관리자 실행 중: http://localhost:{PORT}")
    app.run(port=PORT, debug=False)
