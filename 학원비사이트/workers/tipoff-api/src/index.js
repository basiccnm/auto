// 정보 제보 + 별점 API + 관리자 승인/거절 페이지
// POST /submit           - 제보 저장 (status=pending)
// POST /rate              - 별점 제출/갱신 (upsert)
// GET  /admin             - 대기 목록 (Basic Auth)
// POST /admin/approve/:id - 승인 -> 해당 academies/dojos.phone 갱신 (D1 반영 즉시)
// POST /admin/reject/:id  - 거절

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function checkBasicAuth(request, env) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) return false;
  const decoded = atob(auth.slice(6));
  const [, password] = decoded.split(":");
  return password === env.ADMIN_PASSWORD;
}

function unauthorized() {
  return new Response("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="admin"' },
  });
}

async function handleSubmit(request, env) {
  const body = await request.json().catch(() => null);
  if (!body) return json({ error: "invalid body" }, 400);

  const { entity_type, entity_slug, entity_name, phone, submitter_type } = body;
  if (!["academy", "dojo"].includes(entity_type)) return json({ error: "invalid entity_type" }, 400);
  if (!entity_slug || !entity_name) return json({ error: "missing entity fields" }, 400);
  if (!phone || !/^[0-9\-]{7,20}$/.test(phone)) return json({ error: "invalid phone" }, 400);
  if (!["관계자", "이용자"].includes(submitter_type)) return json({ error: "invalid submitter_type" }, 400);

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const ipHash = await sha256(ip);
  const now = new Date().toISOString();

  // 같은 IP가 같은 대상에 10분 내 중복 제출하는 것만 방지 (연타 방지, 엄격한 차단 아님)
  const dup = await env.DB.prepare(
    `SELECT id FROM tip_offs WHERE entity_slug = ? AND submitted_ip_hash = ?
     AND created_at > datetime('now', '-10 minutes') LIMIT 1`
  )
    .bind(entity_slug, ipHash)
    .first();
  if (dup) return json({ error: "duplicate submission, please wait" }, 429);

  await env.DB.prepare(
    `INSERT INTO tip_offs (entity_type, entity_slug, entity_name, phone, submitter_type, status, submitted_ip_hash, created_at)
     VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)`
  )
    .bind(entity_type, entity_slug, entity_name, phone, submitter_type, ipHash, now)
    .run();

  return json({ ok: true });
}

// 학원 정보 등록/변경 신청 저장 (신규 등록 or 정보 변경). 승인 전까지 사이트 미반영.
// mode="correction"은 "분류(종목)가 잘못됐어요" 제보 전용 — 사업자 본인이 아니어도 제출 가능하도록
// 수강료/주소/전화 등 전체 필수 규칙을 적용하지 않고 classification_note + 대상 slug만 요구.
async function handleInfoSubmit(request, env) {
  const body = await request.json().catch(() => null);
  if (!body) return json({ error: "invalid body" }, 400);

  const mode = body.mode === "new" ? "new" : body.mode === "correction" ? "correction" : "edit";
  const name = (body.name || "").trim();
  const email = (body.reply_email || "").trim();
  const classificationNote = (body.classification_note || "").trim();

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const ipHash = await sha256(ip);
  const now = new Date().toISOString();

  const dup = await env.DB.prepare(
    `SELECT id FROM info_submissions WHERE submitted_ip_hash = ? AND created_at > datetime('now','-2 minutes') LIMIT 1`
  ).bind(ipHash).first();
  if (dup) return json({ error: "잠시 후 다시 시도해주세요" }, 429);

  if (mode === "correction") {
    if (!body.entity_slug || !classificationNote) return json({ error: "제보 대상 또는 내용 누락" }, 400);
    await env.DB.prepare(
      `INSERT INTO info_submissions (mode, entity_type, entity_slug, name, classification_note, reply_email, status, submitted_ip_hash, created_at)
       VALUES ('correction', ?, ?, ?, ?, ?, 'pending', ?, ?)`
    ).bind(
      body.entity_type === "dojo" ? "dojo" : "academy",
      body.entity_slug,
      name || null,
      classificationNote,
      email || null,
      ipHash,
      now
    ).run();
    return json({ ok: true });
  }

  const phone = (body.phone || "").trim();
  const address = (body.address || "").trim();
  const courses = Array.isArray(body.courses) ? body.courses.filter((c) => c && c.course && c.price) : [];

  if (!name || !phone || !address || !email) return json({ error: "필수 항목 누락" }, 400);
  if (!courses.length) return json({ error: "교육과정 최소 1개" }, 400);
  if (mode === "edit" && !body.entity_slug) return json({ error: "대상 누락" }, 400);
  if (mode === "new" && (!body.sido || !body.sigungu)) return json({ error: "지역 누락" }, 400);

  await env.DB.prepare(
    `INSERT INTO info_submissions (mode, entity_type, entity_slug, name, sido, sigungu, dong, address, phone, category, courses_json, reply_email, classification_note, status, submitted_ip_hash, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)`
  ).bind(
    mode,
    body.entity_type === "dojo" ? "dojo" : "academy",
    body.entity_slug || null,
    name,
    body.sido || null,
    body.sigungu || null,
    body.dong || null,
    address,
    phone,
    body.category || null,
    JSON.stringify(courses.map((c) => ({ course: String(c.course).trim(), price: Number(String(c.price).replace(/[^0-9]/g, "")) || 0 }))),
    email,
    classificationNote || null,
    ipHash,
    now
  ).run();

  return json({ ok: true });
}

// 도장 종목 slug -> 표시명 매핑(재분류 시 category_name/sport_name 자동 채움).
const DOJO_SLUG_INFO = {
  taekwondo: { category_name: "태권도장", sport_name: "태권도" },
  boxing: { category_name: "권투장", sport_name: "권투" },
  judo: { category_name: "유도장", sport_name: "유도" },
  hapkido: { category_name: "합기도장", sport_name: "합기도" },
  wrestling: { category_name: "레슬링장", sport_name: "레슬링" },
  kumdo: { category_name: "검도장", sport_name: "검도" },
  wushu: { category_name: "우슈장", sport_name: "우슈" },
  gita: { category_name: "체육도장", sport_name: "" },
};

// 분류 오류 제보(correction) 처리: 관리자가 고른 category_slug로 대상 레코드를 실제로 재분류.
async function handleReclassify(request, env, id) {
  const body = await request.json().catch(() => null);
  if (!body || !body.category_slug) return json({ error: "invalid body" }, 400);
  const sub = await env.DB.prepare(`SELECT * FROM info_submissions WHERE id = ?`).bind(id).first();
  if (!sub || !sub.entity_slug) return json({ error: "not found" }, 404);

  if (sub.entity_type === "dojo") {
    const info = DOJO_SLUG_INFO[body.category_slug];
    if (!info) return json({ error: "invalid category_slug" }, 400);
    await env.DB.prepare(`UPDATE dojos SET category_slug = ?, category_name = ?, sport_name = ? WHERE slug = ?`)
      .bind(body.category_slug, info.category_name, info.sport_name, sub.entity_slug)
      .run();
  } else {
    if (!body.category_name) return json({ error: "category_name 필요" }, 400);
    await env.DB.prepare(`UPDATE academies SET category_slug = ?, category_name = ? WHERE slug = ?`)
      .bind(body.category_slug, body.category_name, sub.entity_slug)
      .run();
  }

  const now = new Date().toISOString();
  await env.DB.prepare(`UPDATE info_submissions SET status = 'approved', reviewed_at = ? WHERE id = ?`).bind(now, id).run();
  return json({ ok: true });
}

// 정보신청 승인/거절. 승인 시 대상 학원에 info_provided=1 + 수강료/주소/전화 반영(변경 모드), 신규는 새 레코드 삽입.
async function handleInfoAction(env, id, action) {
  const sub = await env.DB.prepare(`SELECT * FROM info_submissions WHERE id = ? AND status = 'pending'`).bind(id).first();
  if (!sub) return json({ error: "not found or processed" }, 404);
  const now = new Date().toISOString();

  // correction(분류 오류 제보)은 수강료/전화 데이터가 없으므로 edit/new 로직을 타면 안 됨(덮어쓰기 사고 방지).
  // 실제 재분류는 /admin/info/reclassify 에서 관리자가 직접 지정 → 여기서는 상태만 approved로 바꿔 "확인함" 표시.
  if (action === "approve" && sub.mode !== "correction") {
    const courses = JSON.parse(sub.courses_json || "[]");
    const feeParsed = JSON.stringify(courses);
    const hasFee = courses.length ? 1 : 0;
    if (sub.mode === "edit") {
      const table = sub.entity_type === "dojo" ? "dojos" : "academies";
      await env.DB.prepare(
        `UPDATE ${table} SET info_provided = 1, phone = ?, fee_parsed = ?, has_fee_data = ? WHERE slug = ?`
      ).bind(sub.phone, feeParsed, hasFee, sub.entity_slug).run();
    } else {
      // 신규: academies에 최소 레코드 삽입 (분야는 기타 slug로, 관리자가 추후 조정 가능)
      const slug = (sub.name || "academy").replace(/[^\w가-힣]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") + "-new" + id;
      await env.DB.prepare(
        `INSERT INTO academies (sido, sigungu, dong, name, status, category_name, category_slug, fee_parsed, has_fee_data, info_provided, address_road, phone, reg_date, slug, inst_type)
         VALUES (?, ?, ?, ?, '개원', ?, 'gita', ?, ?, 1, ?, ?, ?, ?, '학원')`
      ).bind(sub.sido, sub.sigungu, sub.dong || null, sub.name, sub.category || "기타", feeParsed, hasFee, sub.address, sub.phone, now.slice(0, 10), slug).run();
    }
  }

  await env.DB.prepare(`UPDATE info_submissions SET status = ?, reviewed_at = ? WHERE id = ?`)
    .bind(action === "approve" ? "approved" : "rejected", now, id).run();
  return json({ ok: true });
}

async function handleRate(request, env) {
  const body = await request.json().catch(() => null);
  if (!body) return json({ error: "invalid body" }, 400);

  const { entity_type, entity_slug, score, voter_token } = body;
  if (!["academy", "dojo"].includes(entity_type)) return json({ error: "invalid entity_type" }, 400);
  if (!entity_slug) return json({ error: "missing entity_slug" }, 400);
  if (!Number.isInteger(score) || score < 1 || score > 5) return json({ error: "invalid score" }, 400);
  if (!voter_token || typeof voter_token !== "string" || voter_token.length < 8) {
    return json({ error: "invalid voter_token" }, 400);
  }

  const voterKey = await sha256(entity_slug + ":" + voter_token);
  const now = new Date().toISOString();

  await env.DB.prepare(
    `INSERT INTO ratings (entity_type, entity_slug, score, voter_key, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT (entity_type, entity_slug, voter_key)
     DO UPDATE SET score = excluded.score, updated_at = excluded.updated_at`
  )
    .bind(entity_type, entity_slug, score, voterKey, now, now)
    .run();

  const stats = await env.DB.prepare(
    `SELECT COUNT(*) as cnt, AVG(score) as avg FROM ratings WHERE entity_type = ? AND entity_slug = ?`
  )
    .bind(entity_type, entity_slug)
    .first();

  return json({ ok: true, count: stats.cnt, average: stats.avg });
}

async function handleAdminList(env) {
  const { results } = await env.DB.prepare(
    `SELECT id, entity_type, entity_slug, entity_name, phone, submitter_type, status, created_at
     FROM tip_offs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 200`
  ).all();

  const { results: subs } = await env.DB.prepare(
    `SELECT id, mode, entity_type, entity_slug, name, sido, sigungu, dong, address, phone, category, courses_json, reply_email, created_at
     FROM info_submissions WHERE status = 'pending' AND mode != 'correction' ORDER BY created_at ASC LIMIT 200`
  ).all();

  const { results: corrections } = await env.DB.prepare(
    `SELECT id, entity_type, entity_slug, name, classification_note, reply_email, created_at
     FROM info_submissions WHERE status = 'pending' AND mode = 'correction' ORDER BY created_at ASC LIMIT 200`
  ).all();

  const { results: banners } = await env.DB.prepare(
    `SELECT id, slot, sido, sigungu, category_slug, image_url, link_url, alt_text, active
     FROM banners ORDER BY id DESC LIMIT 100`
  ).all();

  const subRows = subs
    .map((s) => {
      let courses = "";
      try { courses = JSON.parse(s.courses_json || "[]").map((c) => `${c.course} ${Number(c.price).toLocaleString()}원`).join("<br>"); } catch {}
      return `<tr>
      <td>${s.id}</td>
      <td>${s.mode === "new" ? "신규" : "변경"}</td>
      <td>${s.name || ""}<br><small>${s.entity_slug || (s.sido || "") + " " + (s.sigungu || "") + " " + (s.dong || "")}</small></td>
      <td>${s.phone || ""}<br><small>${s.address || ""}</small></td>
      <td style="font-size:12px">${courses}</td>
      <td>${s.reply_email || ""}</td>
      <td>${s.created_at}</td>
      <td>
        <button onclick="infoAct(${s.id},'approve')">승인</button>
        <button onclick="infoAct(${s.id},'reject')">거절</button>
      </td>
    </tr>`;
    })
    .join("");

  const DOJO_OPTS = [
    ["taekwondo", "태권도"], ["boxing", "권투"], ["judo", "유도"], ["hapkido", "합기도"],
    ["wrestling", "레슬링"], ["kumdo", "검도"], ["wushu", "우슈"], ["gita", "기타종목"],
  ];
  const correctionRows = corrections
    .map((c) => {
      const reclassInput = c.entity_type === "dojo"
        ? `<select id="rc-slug-${c.id}">${DOJO_OPTS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>`
        : `<input id="rc-slug-${c.id}" placeholder="category_slug (예: bosup)" style="width:110px;display:inline-block;">
           <input id="rc-name-${c.id}" placeholder="분야명(예: 수학학원)" style="width:110px;display:inline-block;">`;
      return `<tr>
      <td>${c.id}</td>
      <td>${c.entity_type === "dojo" ? "도장" : "학원"}</td>
      <td>${c.name || ""}<br><small>${c.entity_slug || ""}</small></td>
      <td style="max-width:220px;">${c.classification_note || ""}</td>
      <td>${c.reply_email || ""}</td>
      <td>${c.created_at}</td>
      <td>
        ${reclassInput}
        <button onclick="reclassify(${c.id}, '${c.entity_type}')">적용</button>
        <button onclick="infoAct(${c.id},'reject')">거절</button>
      </td>
    </tr>`;
    })
    .join("");

  const rows = results
    .map(
      (r) => `
    <tr>
      <td>${r.id}</td>
      <td>${r.entity_type}</td>
      <td>${r.entity_name}</td>
      <td>${r.entity_slug}</td>
      <td>${r.phone}</td>
      <td>${r.submitter_type}</td>
      <td>${r.created_at}</td>
      <td>
        <button onclick="act(${r.id},'approve')">승인</button>
        <button onclick="act(${r.id},'reject')">거절</button>
      </td>
    </tr>`
    )
    .join("");

  const bannerRows = banners
    .map(
      (b) => `
    <tr>
      <td>${b.id}</td>
      <td>${b.slot}</td>
      <td>${b.sido || "전체"}</td>
      <td>${b.sigungu || "전체"}</td>
      <td>${b.category_slug || "전체"}</td>
      <td><a href="${b.link_url}" target="_blank">링크</a></td>
      <td>${b.active ? "활성" : "비활성"}</td>
      <td><button onclick="delBanner(${b.id})">삭제</button></td>
    </tr>`
    )
    .join("");

  const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8">
  <title>관리자</title>
  <style>body{font-family:sans-serif;padding:20px}table{border-collapse:collapse;width:100%;margin-bottom:24px}
  td,th{border:1px solid #ddd;padding:6px;font-size:13px}button{margin-right:4px}
  fieldset{margin-bottom:24px;max-width:480px}label{display:block;margin:8px 0 2px;font-size:13px}
  input,select{width:100%;padding:6px;box-sizing:border-box}</style></head>
  <body>
  <h1>학원 정보 등록/변경 신청 (${subs.length}건)</h1>
  <table><thead><tr><th>ID</th><th>모드</th><th>학원/지역</th><th>전화·주소</th><th>교육과정·수강료</th><th>회신메일</th><th>제출일시</th><th>처리</th></tr></thead>
  <tbody>${subRows}</tbody></table>

  <h1>분류(종목) 오류 제보 (${corrections.length}건)</h1>
  <table><thead><tr><th>ID</th><th>유형</th><th>대상</th><th>제보 내용</th><th>회신메일</th><th>제출일시</th><th>재분류·처리</th></tr></thead>
  <tbody>${correctionRows}</tbody></table>

  <h1>전화번호 제보 검토 대기 (${results.length}건)</h1>
  <table><thead><tr><th>ID</th><th>유형</th><th>이름</th><th>slug</th><th>전화</th><th>제출자</th><th>제출일시</th><th>처리</th></tr></thead>
  <tbody>${rows}</tbody></table>

  <h1>배너 관리</h1>
  <fieldset>
    <legend>새 배너 등록</legend>
    <form id="banner-form">
      <label>슬롯 (1/2/3)</label><input name="slot" type="number" min="1" max="3" required>
      <label>시도 (비우면 전체)</label><input name="sido">
      <label>시군구 (비우면 전체)</label><input name="sigungu">
      <label>분야 slug (비우면 전체, 예: bosup)</label><input name="category_slug">
      <label>이미지 URL</label><input name="image_url" required>
      <label>링크 URL</label><input name="link_url" required>
      <label>대체 텍스트</label><input name="alt_text" required>
      <button type="submit" style="margin-top:12px;">등록</button>
    </form>
  </fieldset>
  <table><thead><tr><th>ID</th><th>슬롯</th><th>시도</th><th>시군구</th><th>분야</th><th>링크</th><th>상태</th><th>처리</th></tr></thead>
  <tbody>${bannerRows}</tbody></table>

  <script>
  function authHeader() {
    var pw = sessionStorage.getItem('adminpw');
    if (!pw) { pw = prompt('관리자 비밀번호') || ''; sessionStorage.setItem('adminpw', pw); }
    return 'Basic ' + btoa(':' + pw);
  }
  function act(id, action) {
    fetch('/admin/' + action + '/' + id, { method: 'POST', headers: { 'Authorization': authHeader() } })
      .then(() => location.reload());
  }
  function infoAct(id, action) {
    if (action === 'reject' && !confirm('거절하시겠어요?')) return;
    fetch('/admin/info/' + action + '/' + id, { method: 'POST', headers: { 'Authorization': authHeader() } })
      .then(function(r){ if(r.ok) location.reload(); else alert('처리 실패'); });
  }
  function reclassify(id, entityType) {
    var slugEl = document.getElementById('rc-slug-' + id);
    var slug = slugEl.value.trim();
    if (!slug) { alert('분류를 선택/입력해주세요'); return; }
    var body = { category_slug: slug };
    if (entityType !== 'dojo') {
      var nameEl = document.getElementById('rc-name-' + id);
      body.category_name = nameEl.value.trim();
      if (!body.category_name) { alert('분야명을 입력해주세요'); return; }
    }
    fetch('/admin/info/reclassify/' + id, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': authHeader() },
      body: JSON.stringify(body),
    }).then(function(r){ if(r.ok) location.reload(); else alert('처리 실패'); });
  }
  function delBanner(id) {
    fetch('/admin/banners/' + id + '/delete', { method: 'POST', headers: { 'Authorization': authHeader() } })
      .then(() => location.reload());
  }
  document.getElementById('banner-form').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var f = new FormData(ev.target);
    var body = {};
    f.forEach(function (v, k) { body[k] = v || null; });
    fetch('/admin/banners', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': authHeader() },
      body: JSON.stringify(body),
    }).then(function (r) { if (r.ok) location.reload(); else alert('등록 실패'); });
  });
  </script>
  </body></html>`;

  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}

async function handleAddBanner(request, env) {
  const body = await request.json().catch(() => null);
  if (!body) return json({ error: "invalid body" }, 400);
  const { slot, sido, sigungu, category_slug, image_url, link_url, alt_text } = body;
  if (![1, 2, 3].includes(Number(slot))) return json({ error: "invalid slot" }, 400);
  if (!image_url || !link_url || !alt_text) return json({ error: "missing fields" }, 400);

  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO banners (slot, sido, sigungu, category_slug, image_url, link_url, alt_text, active, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)`
  )
    .bind(Number(slot), sido || null, sigungu || null, category_slug || null, image_url, link_url, alt_text, now)
    .run();

  return json({ ok: true });
}

async function handleDeleteBanner(env, id) {
  await env.DB.prepare(`DELETE FROM banners WHERE id = ?`).bind(id).run();
  return json({ ok: true });
}

async function handleAdminAction(env, id, action) {
  const tip = await env.DB.prepare(`SELECT * FROM tip_offs WHERE id = ? AND status = 'pending'`)
    .bind(id)
    .first();
  if (!tip) return json({ error: "not found or already processed" }, 404);

  const now = new Date().toISOString();
  const newStatus = action === "approve" ? "approved" : "rejected";

  if (action === "approve") {
    const table = tip.entity_type === "academy" ? "academies" : "dojos";
    await env.DB.prepare(`UPDATE ${table} SET phone = ? WHERE slug = ?`)
      .bind(tip.phone, tip.entity_slug)
      .run();
  }

  await env.DB.prepare(`UPDATE tip_offs SET status = ?, reviewed_at = ? WHERE id = ?`)
    .bind(newStatus, now, id)
    .run();

  return json({ ok: true, status: newStatus });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });

    if (url.pathname === "/submit" && request.method === "POST") {
      return handleSubmit(request, env);
    }

    if (url.pathname === "/rate" && request.method === "POST") {
      return handleRate(request, env);
    }

    if (url.pathname === "/info-submit" && request.method === "POST") {
      return handleInfoSubmit(request, env);
    }

    const infoActionMatch = url.pathname.match(/^\/admin\/info\/(approve|reject)\/(\d+)$/);
    if (infoActionMatch && request.method === "POST") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      return handleInfoAction(env, Number(infoActionMatch[2]), infoActionMatch[1]);
    }

    const reclassifyMatch = url.pathname.match(/^\/admin\/info\/reclassify\/(\d+)$/);
    if (reclassifyMatch && request.method === "POST") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      return handleReclassify(request, env, Number(reclassifyMatch[1]));
    }

    if (url.pathname === "/admin" && request.method === "GET") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      return handleAdminList(env);
    }

    const adminActionMatch = url.pathname.match(/^\/admin\/(approve|reject)\/(\d+)$/);
    if (adminActionMatch && request.method === "POST") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      const [, action, id] = adminActionMatch;
      return handleAdminAction(env, Number(id), action);
    }

    if (url.pathname === "/admin/banners" && request.method === "POST") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      return handleAddBanner(request, env);
    }

    const bannerDeleteMatch = url.pathname.match(/^\/admin\/banners\/(\d+)\/delete$/);
    if (bannerDeleteMatch && request.method === "POST") {
      if (!checkBasicAuth(request, env)) return unauthorized();
      return handleDeleteBanner(env, Number(bannerDeleteMatch[1]));
    }

    return new Response("Not found", { status: 404 });
  },
};
