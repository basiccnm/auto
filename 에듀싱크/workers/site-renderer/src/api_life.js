/* ═══════════════════════════════════════════════════════════
   학교생활 API — 서류 · 대화 · 커뮤니티 (2026-07-25)

   여태 이 셋은 앱 안에서만 돌았다. 앱을 지우거나 폰을 바꾸면 사라졌다.
   표는 scripts/migrate_docs_messages_2026-07-25.sql (documents · messages),
   커뮤니티는 웹이 쓰던 community_posts 를 그대로 쓴다.

   권한 규칙은 기존과 같다 — **owner_token 으로 그 자녀가 내 아이인지 매 요청 확인**한다.
   id를 안다고 남의 것을 못 본다. 못 찾으면 404(있는지 없는지도 알려주지 않는다).

   재인증(§3.4): 이 셋은 **가벼운 값**이라 access 만으로 쓰기·지우기가 된다.
   무겁게 막는 건 기록·자녀·계정이다. 여기까지 재인증을 걸면 "넣는 데 30초"가 깨진다.
   ═══════════════════════════════════════════════════════════ */
import { apiOk, apiList, apiErr, corsOrigin, corsHeaders, withCors } from "./api_core.js";

const DOC_KINDS = ["field", "absence", "counsel"];
const DOC_PHASES = ["apply", "report"];
const MSG_SENDERS = ["parent", "child"];
const MAX_TEXT = 500;          // 대화 한 줄 상한
const MAX_BODY = 1000;         // 커뮤니티 글 상한
const LIST_LIMIT = 200;

const nowIso = () => new Date().toISOString();
const clean = (v, max) => String(v ?? "").trim().slice(0, max);

async function readJson(request) {
  try { return await request.json(); } catch (_) { return null; }
}

// 이 자녀가 내 아이인가 — 모든 요청의 첫 관문
async function ownedChild(db, ownerToken, childId) {
  if (!ownerToken || !childId) return null;
  return db.prepare("SELECT id, school_id, grade, class_name FROM children WHERE id = ? AND owner_token = ?")
    .bind(childId, ownerToken).first();
}

// ── 서류 ────────────────────────────────────────────────────
function docShape(r) {
  let payload = {};
  try { payload = JSON.parse(r.payload || "{}"); } catch (_) {}
  return {
    id: r.id, child_id: r.child_id, kind: r.kind, phase: r.phase, title: r.title,
    from_ymd: r.from_ymd, to_ymd: r.to_ymd, days: r.days == null ? null : Number(r.days),
    reported: !!r.reported, payload, created_at: r.created_at, updated_at: r.updated_at,
  };
}

async function listDocuments(db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const { results } = await db
    .prepare("SELECT * FROM documents WHERE child_id = ? ORDER BY id DESC LIMIT ?")
    .bind(child.id, LIST_LIMIT).all();
  return apiList((results || []).map(docShape));
}

async function createDocument(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const kind = clean(b.kind, 20);
  const phase = clean(b.phase, 10) || "apply";
  const fields = {};
  if (!DOC_KINDS.includes(kind)) fields.kind = "서류 종류를 확인해 주세요.";
  if (!DOC_PHASES.includes(phase)) fields.phase = "신청서/보고서 중 하나여야 해요.";
  if (Object.keys(fields).length) return apiErr("VALIDATION", { fields });

  const t = nowIso();
  const ins = await db.prepare(
    `INSERT INTO documents (child_id, kind, phase, title, from_ymd, to_ymd, days, payload, reported, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)`
  ).bind(
    child.id, kind, phase, clean(b.title, 100) || null,
    clean(b.from_ymd, 8) || null, clean(b.to_ymd, 8) || null,
    Number.isFinite(+b.days) ? Math.max(0, Math.min(400, +b.days)) : null,
    JSON.stringify(b.payload && typeof b.payload === "object" ? b.payload : {}),
    t, t
  ).run();

  const row = await db.prepare("SELECT * FROM documents WHERE id = ?").bind(ins.meta.last_row_id).first();
  return apiOk(docShape(row), 201);
}

// 보고서를 냈다고 표시하거나(교외체험학습), 내용을 고친다
async function patchDocument(request, db, owner, id) {
  const row = await db.prepare(
    "SELECT d.* FROM documents d JOIN children c ON c.id = d.child_id WHERE d.id = ? AND c.owner_token = ?"
  ).bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const title = b.title === undefined ? row.title : (clean(b.title, 100) || null);
  const payload = b.payload && typeof b.payload === "object" ? JSON.stringify(b.payload) : row.payload;
  const reported = b.reported === undefined ? row.reported : (b.reported ? 1 : 0);
  await db.prepare("UPDATE documents SET title = ?, payload = ?, reported = ?, updated_at = ? WHERE id = ?")
    .bind(title, payload, reported, nowIso(), row.id).run();
  const after = await db.prepare("SELECT * FROM documents WHERE id = ?").bind(row.id).first();
  return apiOk(docShape(after));
}

async function deleteDocument(db, owner, id) {
  const row = await db.prepare(
    "SELECT d.id FROM documents d JOIN children c ON c.id = d.child_id WHERE d.id = ? AND c.owner_token = ?"
  ).bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  await db.prepare("DELETE FROM documents WHERE id = ?").bind(row.id).run();
  return apiOk({ deleted: true, id: row.id });
}

// ── 대화 ────────────────────────────────────────────────────
const msgShape = (r) => ({
  id: r.id, child_id: r.child_id, sender: r.sender, text: r.text,
  seen: !!r.seen_at, seen_at: r.seen_at, created_at: r.created_at,
});

async function listMessages(db, owner, childId, url) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  // since 를 주면 그 뒤에 온 것만 — 앱이 주기적으로 새 말만 받아갈 때 쓴다
  const since = parseInt(url.searchParams.get("since") || "0", 10) || 0;
  const { results } = await db
    .prepare("SELECT * FROM messages WHERE child_id = ? AND id > ? ORDER BY id ASC LIMIT ?")
    .bind(child.id, since, LIST_LIMIT).all();
  const unread = await db
    .prepare("SELECT COUNT(*) AS n FROM messages WHERE child_id = ? AND sender = 'child' AND seen_at IS NULL")
    .bind(child.id).first();
  return apiList((results || []).map(msgShape), { unread: (unread && unread.n) || 0 });
}

async function createMessage(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  const text = clean(b && b.text, MAX_TEXT);
  const sender = clean(b && b.sender, 10) || "parent";
  if (!text) return apiErr("VALIDATION", { fields: { text: "보낼 말을 적어주세요." } });
  if (!MSG_SENDERS.includes(sender)) return apiErr("VALIDATION", { fields: { sender: "parent 또는 child 여야 해요." } });

  const ins = await db.prepare("INSERT INTO messages (child_id, sender, text, created_at) VALUES (?, ?, ?, ?)")
    .bind(child.id, sender, text, nowIso()).run();
  const row = await db.prepare("SELECT * FROM messages WHERE id = ?").bind(ins.meta.last_row_id).first();
  return apiOk(msgShape(row), 201);
}

// 상대가 보낸 말을 읽음으로 — 말풍선의 «1»이 사라지는 지점
async function seenMessages(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  const reader = clean(b && b.reader, 10) || "parent";
  if (!MSG_SENDERS.includes(reader)) return apiErr("VALIDATION", { fields: { reader: "parent 또는 child 여야 해요." } });
  const other = reader === "parent" ? "child" : "parent";
  const r = await db.prepare("UPDATE messages SET seen_at = ? WHERE child_id = ? AND sender = ? AND seen_at IS NULL")
    .bind(nowIso(), child.id, other).run();
  return apiOk({ seen: (r.meta && r.meta.changes) || 0 });
}

/* ── 커뮤니티 = 같은 학교·같은 반 학부모 오픈채팅 (2026-08-01 개편) ──
   게시판이 아니라 **채팅**이다. 규칙이 여럿 얽혀 있어 한 곳에 적어둔다.

   ① 초등만 연다. 중·고는 성적·입시·교사 얘기가 붙어 분쟁이 커지고, 그쪽은 이미 맘카페가 잡고 있다.
   ② **참여한 시점부터만 보인다.** 이전 대화는 안 보인다(오픈채팅과 같음).
   ③ 참여할 때 「지켜야 할 것」에 동의를 받는다 — 구글 UGC 정책이 요구하는 «작성 전 약관 동의»가 여기서 끝난다.
   ④ 50자 · 30초에 한 번. 짧고 느리면 싸움이 안 붙는다. 감정글은 몇백 자다.
   ⑤ 신고는 **자동 삭제가 아니다** — 신고한 사람 눈에서만 가려지고, 서로 다른 3명이 신고해야 내려간다.
      1건 자동숨김은 «신고 버튼이 곧 삭제 버튼»이 되어 악용된다.
   ⑥ 차단하면 그 사람 글이 나에게만 안 보인다.
   준실명(학년·반 학부모)은 예전 그대로다 — 학교가 붙어 있으면 저격글이 확 준다. */
const COMM_MAX_BODY = 50;        // 한 마디 길이. 답도 담기되 싸움은 안 되는 선
const COMM_COOLDOWN_MS = 30000;  // 30초에 한 번 = 한 시간에 120마디
const COMM_HIDE_AT = 3;          // 서로 다른 이 인원이 신고하면 내려간다

const postShape = (r, mine) => ({
  id: r.id, body: r.body, display_name: r.display_name,
  grade: r.author_grade, class_name: r.author_class,
  mine: !!mine, created_at: r.created_at,
});

// 초등만. school_kind 가 「초등학교」인 자녀의 방만 열린다.
async function commRoom(db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return { err: apiErr("NOT_FOUND") };
  const school = await db.prepare("SELECT school_kind FROM schools WHERE id = ?").bind(child.school_id).first();
  if (!school || !String(school.school_kind || "").startsWith("초")) {
    return { err: apiErr("FORBIDDEN", null, "지금은 초등학교만 열려 있어요.") };
  }
  const me = await db.prepare("SELECT * FROM community_members WHERE child_id = ?").bind(child.id).first();
  return { child, member: me || null };
}

// 참여 — 다시 들어오면 joined_at 이 갱신된다(그래서 그 전 대화는 또 안 보인다)
async function joinCommunity(request, db, owner, childId) {
  const { child, err } = await commRoom(db, owner, childId);
  if (err) return err;
  const b = await readJson(request);
  if (!b || b.agree !== true) {
    return apiErr("VALIDATION", { fields: { agree: "함께 지킬 것에 동의해 주세요." } });
  }
  const now = nowIso();
  await db.prepare(
    `INSERT INTO community_members (child_id, owner_token, joined_at, agreed_at, left_at)
     VALUES (?, ?, ?, ?, NULL)
     ON CONFLICT(child_id) DO UPDATE SET joined_at = excluded.joined_at, agreed_at = excluded.agreed_at, left_at = NULL`
  ).bind(child.id, owner, now, now).run();
  return apiOk({ joined_at: now });
}

async function leaveCommunity(db, owner, childId) {
  const { child, err } = await commRoom(db, owner, childId);
  if (err) return err;
  await db.prepare("UPDATE community_members SET left_at = ? WHERE child_id = ?").bind(nowIso(), child.id).run();
  return apiOk({ left: true });
}

async function listPosts(db, owner, childId, url) {
  const { child, member, err } = await commRoom(db, owner, childId);
  if (err) return err;
  // 아직 참여 전이면 대화를 안 준다 — 화면은 「참여하기」를 그린다
  if (!member || member.left_at) return apiList([], { joined: false });

  // since = 마지막으로 받아간 글 id. 채팅이라 새로 온 것만 이어 받는다.
  const since = parseInt(url?.searchParams.get("since") || "0", 10) || 0;
  const { results } = await db.prepare(
    `SELECT p.* FROM community_posts p
      WHERE p.school_id = ? AND p.author_grade = ? AND p.author_class = ?
        AND p.hidden = 0
        AND p.created_at > ?                       -- 참여 시점 이후만
        AND p.id > ?
        AND NOT EXISTS (SELECT 1 FROM community_reports r WHERE r.post_id = p.id AND r.owner_token = ?)
        AND NOT EXISTS (SELECT 1 FROM community_blocks b WHERE b.owner_token = ? AND b.blocked_token = p.owner_token)
      ORDER BY p.id ASC LIMIT ?`
  ).bind(child.school_id, String(child.grade), String(child.class_name),
    member.joined_at, since, owner, owner, LIST_LIMIT).all();
  return apiList((results || []).map((r) => postShape(r, r.owner_token === owner)), { joined: true });
}

async function createPost(request, db, owner, childId) {
  const { child, member, err } = await commRoom(db, owner, childId);
  if (err) return err;
  if (!member || member.left_at) return apiErr("FORBIDDEN", null, "먼저 대화에 참여해 주세요.");

  /* 관리자가 커뮤니티 이용을 막은 사람. **대화만** 막힌다 —
     급식·기록·서식은 돈 내고 쓰는 기능이라 시비 한 번으로 끊으면 그건 환불 사유가 된다. */
  const ban = await db.prepare("SELECT until FROM community_bans WHERE owner_token = ?").bind(owner).first();
  if (ban && (!ban.until || ban.until > nowIso())) {
    return apiErr("FORBIDDEN", { until: ban.until || null },
      ban.until ? `대화가 잠시 멈춰 있어요 (${String(ban.until).slice(0, 10)}까지).` : "대화 이용이 중지되었어요.");
  }

  const b = await readJson(request);
  const body = clean(b && b.body, COMM_MAX_BODY);
  if (!body) return apiErr("VALIDATION", { fields: { body: "내용을 적어주세요." } });

  /* 30초 간격 — 도배도 막고 싸움도 식힌다. 서버에서 건다(앱에서만 막으면 우회된다).
     내 마지막 글 시각과 비교한다. 방이 아니라 사람 기준이라 다른 방에서 연타해도 걸린다. */
  const last = await db.prepare(
    "SELECT created_at FROM community_posts WHERE owner_token = ? ORDER BY id DESC LIMIT 1"
  ).bind(owner).first();
  if (last) {
    const gap = Date.now() - new Date(last.created_at).getTime();
    if (gap < COMM_COOLDOWN_MS) {
      const wait = Math.ceil((COMM_COOLDOWN_MS - gap) / 1000);
      return apiErr("LIMIT_EXCEEDED", { retry_after: wait }, `${wait}초 뒤에 다시 보낼 수 있어요.`);
    }
  }

  const ins = await db.prepare(
    `INSERT INTO community_posts (school_id, child_id, owner_token, body, display_name, author_grade, author_class, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(child.school_id, child.id, owner, body,
    `${child.grade}학년 ${child.class_name}반 학부모`, String(child.grade), String(child.class_name), nowIso()).run();
  const row = await db.prepare("SELECT * FROM community_posts WHERE id = ?").bind(ins.meta.last_row_id).first();
  return apiOk(postShape(row, true), 201);
}

/* 신고 — 누르는 즉시 **신고한 사람에게만** 안 보인다(목록 조회에서 걸러진다).
   서로 다른 3명이 신고해야 모두에게서 내려간다. community_reports 의 UNIQUE(post_id, owner_token) 가
   한 사람의 다중 신고를 막아준다. 내려간 글은 관리자 화면에서 사람이 확인한다. */
async function reportPost(db, owner, id) {
  const post = await db.prepare("SELECT * FROM community_posts WHERE id = ?").bind(id).first();
  if (!post) return apiErr("NOT_FOUND");
  if (post.owner_token === owner) return apiErr("VALIDATION", null, "내 글은 신고할 수 없어요.");
  try {
    await db.prepare("INSERT INTO community_reports (post_id, owner_token, created_at) VALUES (?, ?, ?)")
      .bind(post.id, owner, nowIso()).run();
  } catch (_) {
    return apiOk({ reported: true, already: true });   // 이미 신고한 글 — 조용히 성공으로
  }
  const n = await db.prepare("SELECT COUNT(*) AS n FROM community_reports WHERE post_id = ?").bind(post.id).first();
  const count = (n && n.n) || 0;
  await db.prepare("UPDATE community_posts SET report_count = ?, hidden = ? WHERE id = ?")
    .bind(count, count >= COMM_HIDE_AT ? 1 : 0, post.id).run();
  return apiOk({ reported: true, hidden: count >= COMM_HIDE_AT });
}

// 차단 — 그 사람 글이 나에게만 안 보인다. 상대는 차단당한 줄 모른다(알려주면 그게 새 분쟁이 된다).
async function blockAuthor(db, owner, id) {
  const post = await db.prepare("SELECT owner_token FROM community_posts WHERE id = ?").bind(id).first();
  if (!post) return apiErr("NOT_FOUND");
  if (post.owner_token === owner) return apiErr("VALIDATION", null, "나 자신은 차단할 수 없어요.");
  await db.prepare(
    "INSERT OR IGNORE INTO community_blocks (owner_token, blocked_token, created_at) VALUES (?, ?, ?)"
  ).bind(owner, post.owner_token, nowIso()).run();
  return apiOk({ blocked: true });
}

// 내 글만 지운다. 남의 글은 신고·차단으로 처리한다.
async function deletePost(db, owner, id) {
  const row = await db.prepare("SELECT id FROM community_posts WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  await db.batch([
    db.prepare("DELETE FROM community_reports WHERE post_id = ?").bind(row.id),   // 신고가 글을 참조 → 먼저
    db.prepare("DELETE FROM community_posts WHERE id = ?").bind(row.id),
  ]);
  return apiOk({ deleted: true, id: row.id });
}

/* ── 내 일정(다이어리) ──────────────────────────────────────
   병원·여행처럼 **그 날 하루짜리** 일정. 학사일정(학교가 정한 것)과 다르다.
   웹은 personal_events 를 HTML 경로로 쓰고 있었는데 앱용 API가 없었다 → 여기서 연다.
   가벼운 값이라 access 만으로 넣고 지운다(계약 §3.4). */
/* ⚠ 2026-07-31 — 시작시각을 **remind_at 에 넣고 있었다**("16:00").
   그런데 크론은 remind_at 을 ISO 시각으로 보고 `remind_at <= now` 로 비교한다.
   문자열 비교라 "16:00" < "2026-…" 이 늘 참 → 시작시각을 넣은 일정마다 **곧바로 알림이 나갔다.**
   (다행히 그 시점 개인일정이 0건이라 실제 발송 사고는 없었다.)
   이제 시작시각은 start_time, remind_at 은 **진짜 알림 시각(ISO)** 으로 나눈다. */
const eventShape = (r) => ({
  id: r.id, date: r.event_date, title: r.label, memo: r.detail || null,
  start: r.start_time || null,
  remind_at: r.remind_at || null,
  created_at: r.created_at,
});
// 알림 시각은 ISO(…Z)만 받는다 — HH:MM 이 들어오면 크론이 즉시 쏜다
const cleanRemind = (v) => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v) ? v.slice(0, 30) : null);

async function listEvents(db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const { results } = await db
    .prepare("SELECT * FROM personal_events WHERE child_id = ? AND owner_token = ? ORDER BY event_date, id LIMIT ?")
    .bind(child.id, owner, LIST_LIMIT).all();
  return apiList((results || []).map(eventShape));
}

async function createEvent(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  const date = clean(b && b.date, 8);
  const title = clean(b && b.title, 60);
  const fields = {};
  if (!/^\d{8}$/.test(date)) fields.date = "날짜를 YYYYMMDD로 보내주세요.";
  if (!title) fields.title = "일정 이름을 적어주세요.";
  if (Object.keys(fields).length) return apiErr("VALIDATION", { fields });

  const ins = await db.prepare(
    "INSERT INTO personal_events (owner_token, child_id, event_date, label, detail, start_time, remind_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
  ).bind(owner, child.id, date, title, clean(b.memo, 200) || null,
    clean(b.start, 5) || null, cleanRemind(b.remind_at), nowIso()).run();
  const row = await db.prepare("SELECT * FROM personal_events WHERE id = ?").bind(ins.meta.last_row_id).first();
  return apiOk(eventShape(row), 201);
}

async function patchEvent(request, db, owner, id) {
  const row = await db.prepare("SELECT * FROM personal_events WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  const b = await readJson(request) || {};
  /* 알림 시각을 바꾸면 «이미 보냈음» 표시를 지운다 — 안 지우면 새 시각에 알림이 안 온다. */
  const nextRemind = b.remind_at === undefined ? row.remind_at : cleanRemind(b.remind_at);
  await db.prepare("UPDATE personal_events SET label = ?, detail = ?, start_time = ?, remind_at = ?, remind_sent = ? WHERE id = ?")
    .bind(b.title === undefined ? row.label : clean(b.title, 60) || row.label,
      b.memo === undefined ? row.detail : (clean(b.memo, 200) || null),
      b.start === undefined ? row.start_time : (clean(b.start, 5) || null),
      nextRemind,
      nextRemind === row.remind_at ? row.remind_sent : 0,
      row.id).run();
  const after = await db.prepare("SELECT * FROM personal_events WHERE id = ?").bind(row.id).first();
  return apiOk(eventShape(after));
}

async function deleteEvent(db, owner, id) {
  const row = await db.prepare("SELECT id FROM personal_events WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  await db.prepare("DELETE FROM personal_events WHERE id = ?").bind(row.id).run();
  return apiOk({ deleted: true, id: row.id });
}

/* ── 준비물 체크리스트 (2026-07-27) ─────────────────────────
   «내일 뭐 가져가?» 를 앱이 대신 기억한다. 일정과 따로 두는 이유는 마이그레이션 주석 참고.
   done 만 바꾸는 일이 압도적으로 많아서 PATCH 는 부분 갱신으로 받는다. */
const supplyShape = (r) => ({
  id: r.id, date: r.due_ymd, item: r.item, memo: r.memo || null,
  done: !!r.done, created_at: r.created_at,
});

async function listSupplies(db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const { results } = await db
    .prepare("SELECT * FROM supplies WHERE child_id = ? AND owner_token = ? ORDER BY due_ymd, id LIMIT ?")
    .bind(child.id, owner, LIST_LIMIT).all();
  return apiList((results || []).map(supplyShape));
}

async function createSupply(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = await readJson(request);
  // 「4주치 만들기」가 한 번에 여러 개를 보낸다 — 낱개도 같은 경로로 받게 배열로 감싼다.
  const raw = Array.isArray(b && b.items) ? b.items : [b];
  if (!raw.length || raw.length > 30) {
    return apiErr("VALIDATION", { fields: { items: "한 번에 30개까지 넣을 수 있어요." } });
  }
  const rows = [];
  for (const x of raw) {
    const date = clean(x && x.date, 8);
    const item = clean(x && x.item, 40);
    if (!/^\d{8}$/.test(date)) return apiErr("VALIDATION", { fields: { date: "날짜를 YYYYMMDD로 보내주세요." } });
    if (!item) return apiErr("VALIDATION", { fields: { item: "준비물 이름을 적어주세요." } });
    rows.push({ date, item, memo: clean(x.memo, 100) || null });
  }
  const now = nowIso();
  await db.batch(rows.map((r) => db.prepare(
    "INSERT INTO supplies (owner_token, child_id, due_ymd, item, memo, done, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)"
  ).bind(owner, child.id, r.date, r.item, r.memo, now)));
  // 방금 넣은 것만 골라 돌려준다(앱이 id를 알아야 체크·삭제가 된다)
  const { results } = await db
    .prepare("SELECT * FROM supplies WHERE child_id = ? AND owner_token = ? AND created_at = ? ORDER BY id")
    .bind(child.id, owner, now).all();
  return apiOk({ items: (results || []).map(supplyShape) }, 201);
}

async function patchSupply(request, db, owner, id) {
  const row = await db.prepare("SELECT * FROM supplies WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  const b = await readJson(request) || {};
  await db.prepare("UPDATE supplies SET item = ?, memo = ?, due_ymd = ?, done = ? WHERE id = ?")
    .bind(
      b.item === undefined ? row.item : clean(b.item, 40) || row.item,
      b.memo === undefined ? row.memo : (clean(b.memo, 100) || null),
      b.date === undefined || !/^\d{8}$/.test(clean(b.date, 8)) ? row.due_ymd : clean(b.date, 8),
      b.done === undefined ? row.done : (b.done ? 1 : 0),
      row.id).run();
  const after = await db.prepare("SELECT * FROM supplies WHERE id = ?").bind(row.id).first();
  return apiOk(supplyShape(after));
}

async function deleteSupply(db, owner, id) {
  const row = await db.prepare("SELECT id FROM supplies WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!row) return apiErr("NOT_FOUND");
  await db.prepare("DELETE FROM supplies WHERE id = ?").bind(row.id).run();
  return apiOk({ deleted: true, id: row.id });
}

/* ── 자녀 기기 연결 — 일회용 6자리 코드 (2026-07-25 확정) ────
   엄마가 아이 폰에서 **로그인하지 않는다.** 로그인시키면 아이 폰에 부모 토큰이 남아
   결제·기록 삭제·형제 정보까지 열린다. 로그아웃 로직을 아무리 잘 짜도 한 번 새면 끝이라
   애초에 안 들어가게 한다. 아이 폰이 갖는 건 **그 아이 대화만 되는 토큰**이다. */
const INVITE_TTL = 600;          // 10분. 옆에서 불러주고 바로 넣는 용도라 길 필요가 없다
const INVITE_MAX_TRY = 10;       // 6자리는 100만 가지 — 무제한 대입은 막는다

async function createInvite(db, owner, account, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const code = String(crypto.getRandomValues(new Uint32Array(1))[0] % 1000000).padStart(6, "0");
  const now = Math.floor(Date.now() / 1000);
  await db.batch([
    db.prepare("DELETE FROM child_invites WHERE child_id = ? OR expires_at < ?").bind(child.id, now),  // 낡은 것 정리
    db.prepare("INSERT INTO child_invites (code, child_id, account_id, expires_at, created_at) VALUES (?, ?, ?, ?, ?)")
      .bind(code, child.id, account ? account.id : null, now + INVITE_TTL, nowIso()),
  ]);
  return apiOk({ code, expires_in: INVITE_TTL });
}

/* 연결 끊기 — 기기 표식을 지운다. 그 순간 그 폰이 들고 있던 토큰은 auth_core 에서 막힌다
   («옛 토큰(dev 없음)은 통과» 예외에 걸리지 않는다 — dev 는 있는데 표식이 사라진 경우라서). */
async function unlinkChildDevice(db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  await db.prepare("UPDATE children SET child_device = NULL, child_device_at = NULL WHERE id = ?").bind(child.id).run();
  return apiOk({ unlinked: true, child_id: child.id });
}

// 아이 폰이 코드를 내고 **자녀 전용 토큰**을 받아간다. 인증 불필요(아직 아무 자격이 없다).
export async function claimInvite(request, db, env, signToken, authSecret, TOKEN_TTL) {
  const b = await readJson(request);
  const code = clean(b && b.code, 6);
  if (!/^\d{6}$/.test(code)) return apiErr("VALIDATION", { fields: { code: "6자리 숫자를 넣어주세요." } });
  const now = Math.floor(Date.now() / 1000);

  const row = await db.prepare("SELECT * FROM child_invites WHERE code = ?").bind(code).first();
  // 없는 코드와 만료된 코드를 **같은 말로** 돌려준다 — 다르면 "그 코드는 있었다"가 새어나간다
  if (!row || row.used_at || row.expires_at < now) {
    return apiErr("AUTH_INVALID", null, "코드가 맞지 않거나 시간이 지났어요. 부모님께 새 코드를 받아주세요.");
  }
  /* 학교(slug·이름)까지 같이 준다 — 아이 폰은 **자기 자신 말고는 아무것도 모른다.**
     예전엔 이 값을 안 줘도 화면이 멀쩡했는데, 그건 그 폰에 남아 있던 **부모 캐시**를 쓴 것이었다
     (2026-08-02 실측). 캐시를 지우고 나면 급식·시간표를 부를 열쇠가 없다. */
  const child = await db.prepare(
    `SELECT c.id, c.nickname, c.grade, c.class_name, c.school_id, c.trial_expires_at,
            s.slug AS school_slug, s.name AS school_name, s.school_kind,
            a.id AS account_id, a.owner_token
       FROM children c
       JOIN accounts a ON a.owner_token = c.owner_token
       LEFT JOIN schools s ON s.id = c.school_id
      WHERE c.id = ?`
  ).bind(row.child_id).first();
  if (!child) return apiErr("NOT_FOUND");

  /* 🔒 **자녀 1명당 기기 1대**(2026-07-31 지시). 새 코드로 붙으면 앞 기기는 그 자리에서 끊긴다.
     기기 표식(dev)을 토큰에 넣고 children.child_device 에도 적어 둔다 —
     둘이 다르면 auth_core 가 막는다. 없으면 아이 폰 여러 대에 같은 권한이 퍼진다. */
  const dev = crypto.randomUUID();
  await db.batch([
    db.prepare("UPDATE child_invites SET used_at = ? WHERE code = ?").bind(nowIso(), code),
    db.prepare("UPDATE children SET child_device = ?, child_device_at = ? WHERE id = ?").bind(dev, nowIso(), child.id),
  ]);

  // 자녀 토큰 — refresh를 주지 않는다. 만료되면 부모에게 코드를 다시 받는다(기기가 오래 방치되지 않게).
  const access = await signToken(
    { sub: child.account_id, typ: "access", tok: child.owner_token, role: "child", chd: child.id, dev },
    authSecret(env), TOKEN_TTL.refresh
  );
  return apiOk({
    access_token: access, token_type: "Bearer", expires_in: TOKEN_TTL.refresh,
    child: {
      id: child.id, nickname: child.nickname, grade: child.grade, class_name: child.class_name,
      /* 이용권 기한 — 없으면 자녀폰이 연결 직후부터 잠긴다(2026-08-03 전수검사 10번) */
      pass_expires_at: child.trial_expires_at || null,
      school: child.school_slug
        ? { slug: child.school_slug, name: child.school_name, school_kind: child.school_kind }
        : null,
    },
  });
}

// ── 라우터 ──────────────────────────────────────────────────
// index.js가 /api/v1/* 에서 CORS를 씌워주므로 여기서는 순수 응답만 만든다.
export async function handleLifeApi(request, db, env, url, auth) {
  const path = url.pathname;
  const method = request.method.toUpperCase();
  const owner = auth.ownerToken;
  if (auth.error) return apiErr(auth.error);
  if (!owner) return apiErr("AUTH_REQUIRED");
  /* 자녀 기기는 **그 아이 대화와 그 아이 준비물만** 만진다. 서류·커뮤니티·초대발급은 부모 것이다.
     index.js에서 한 번 거르지만 여기서도 막는다 — 관문이 하나면 그 하나가 뚫리면 끝이다.
     ⚠ 여기서 «그 아이인지»를 본다. index.js 는 경로 모양만 보므로,
       다른 아이 번호를 넣어 부르는 것은 이 줄이 막는다. 삭제는 아예 안 연다. */
  /* 자녀 앱 테마(2026-08-02) — 자녀 토큰 전용. 기기를 바꿔도 아이가 고른 화면이 따라온다.
     scripts/migrate_kid_prefs_2026-08-02.sql 이 children 에 kid_theme·kid_accent 를 더한다.
     ⚠ 아래 자녀 경로 제한보다 먼저 와야 한다 — 저 정규식은 messages·supplies 만 열어준다. */
  if (auth.role === "child" && path === "/api/v1/child/prefs") {
    if (method === "GET") {
      const r = await db.prepare("SELECT kid_theme, kid_accent FROM children WHERE id=?1")
        .bind(auth.childId).first();
      return apiOk({ theme: r?.kid_theme || null, accent: r?.kid_accent || null });
    }
    if (method === "PUT") {
      const b = await request.json().catch(() => null);
      /* 색 12벌(2026-08-03). 앱의 KID_THEMES 와 **같은 목록**이다 — 늘리면 여기도 늘린다.
         모르는 값은 막는다. 저장은 되는데 화면이 기본색으로 뜨면 «저장이 안 된다»는 문의가 온다. */
      const KID_THEMES = ["rose", "lilac", "mint", "peach", "butter", "aqua",
                          "gold", "cyan", "lime", "magenta", "orange", "violet"];
      // 옛 이름을 그대로 받아 새 이름으로 바꿔 저장한다 — 앱이 못 고친 채 올려도 여기서 살린다
      const OLD = { pastel: "mint", quest: "gold" };
      const want = OLD[b?.theme] || b?.theme;
      const theme = KID_THEMES.includes(want) ? want : null;
      const accent = typeof b?.accent === "string" && b.accent.length <= 16 ? b.accent : null;
      if (!theme) return apiErr("VALIDATION", { theme: "pastel|quest" });
      await db.prepare("UPDATE children SET kid_theme=?1, kid_accent=?2 WHERE id=?3")
        .bind(theme, accent, auth.childId).run();
      return apiOk({ theme, accent });
    }
    return apiErr("VALIDATION", { method: "unsupported" });
  }

  if (auth.role === "child") {
    const mine = path.match(/^\/api\/v1\/children\/(\d+)\/(messages|supplies)(\/seen)?\/?$/);
    if (!mine || String(auth.childId) !== mine[1]) return apiErr("FORBIDDEN");
    if (method === "DELETE") return apiErr("FORBIDDEN");
  }
  const bad = () => apiErr("VALIDATION", { method: "unsupported" }, "지원하지 않는 요청 방식이에요.");

  let m = path.match(/^\/api\/v1\/children\/(\d+)\/documents\/?$/);
  if (m) {
    if (method === "GET") return listDocuments(db, owner, m[1]);
    if (method === "POST") return createDocument(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/documents\/(\d+)\/?$/);
  if (m) {
    if (method === "PATCH") return patchDocument(request, db, owner, m[1]);
    if (method === "DELETE") return deleteDocument(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/messages\/?$/);
  if (m) {
    if (method === "GET") return listMessages(db, owner, m[1], url);
    if (method === "POST") return createMessage(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/messages\/seen\/?$/);
  if (m) {
    if (method === "POST") return seenMessages(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/community\/?$/);
  if (m) {
    if (method === "GET") return listPosts(db, owner, m[1], url);
    if (method === "POST") return createPost(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/community\/join\/?$/);
  if (m) {
    if (method === "POST") return joinCommunity(request, db, owner, m[1]);
    if (method === "DELETE") return leaveCommunity(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/events\/?$/);
  if (m) {
    if (method === "GET") return listEvents(db, owner, m[1]);
    if (method === "POST") return createEvent(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/events\/(\d+)\/?$/);
  if (m) {
    if (method === "PATCH") return patchEvent(request, db, owner, m[1]);
    if (method === "DELETE") return deleteEvent(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/supplies\/?$/);
  if (m) {
    if (method === "GET") return listSupplies(db, owner, m[1]);
    if (method === "POST") return createSupply(request, db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/supplies\/(\d+)\/?$/);
  if (m) {
    if (method === "PATCH") return patchSupply(request, db, owner, m[1]);
    if (method === "DELETE") return deleteSupply(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/children\/(\d+)\/invite\/?$/);
  if (m) {
    if (method === "POST") return createInvite(db, owner, auth.account, m[1]);
    // 연결 끊기 — 아이 폰을 잃어버렸거나 바꿨을 때. 기기 표식을 지우면 그 폰 토큰은 바로 죽는다.
    if (method === "DELETE") return unlinkChildDevice(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/community\/(\d+)\/?$/);
  if (m) {
    if (method === "DELETE") return deletePost(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/community\/(\d+)\/report\/?$/);
  if (m) {
    if (method === "POST") return reportPost(db, owner, m[1]);
    return bad();
  }
  m = path.match(/^\/api\/v1\/community\/(\d+)\/block\/?$/);
  if (m) {
    if (method === "POST") return blockAuthor(db, owner, m[1]);
    return bad();
  }
  return null;   // 우리 것이 아니다 — index.js가 다음 라우트로 넘긴다
}
