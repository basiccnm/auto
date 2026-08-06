// ================= 미션 API (2026-08-01) =================
// 부모가 오늘 3개를 정하면 아이가 자기 폰에서 확인하고 해낸다.
//
// 이 파일이 지키는 규칙들 — 화면이 아니라 여기서 지켜야 우회가 안 된다:
//   ① 부모가 안 정해도 **오늘 3개는 자동으로 찬다.** 바쁜 날 하루 걸렀다고 아이 화면이 비면
//      그날로 끝난다. 부모는 보고 넘기거나 갈아끼우기만 한다.
//   ② **3개가 전부 「대기」이면 안 된다.** 그날 아무 도장도 못 받고 자는 아이가 생긴다.
//   ③ 사진을 낸 것은 부모가 안 봐도 **다음날 오전 8시에 자동 승인**된다.
//      기다림은 인내심이 아니라 «어른에 대한 신뢰»에서 나온다 — 약속이 어긋나면 아이는 3분 만에 포기한다.
//   ④ 「오늘은 못 했어요」에는 **벌이 없다.** 도장이 안 늘 뿐이다. 잃을 게 있으면 반드시 거짓말한다.
//   ⑤ 연속 달성(스트릭)은 만들지 않는다. 끊기는 게 아까워 안 한 날도 누르게 된다.
//   ⑥ 부모는 도장을 **되돌릴 수 있다.** 취소가 없으면 그건 훈련이 아니라 방치다.

import { apiOk, apiList, apiErr, readJson } from "./api_core.js";
import { resolveAuth } from "./auth_core.js";

const DAY_PICK = 3;              // 하루에 주는 개수
const PHOTO_KEEP_DAYS = 7;       // 미션 사진 보관 기간. 서랍(기록)과 **별개**다
const PHOTO_MAX = 3 * 1024 * 1024;

const nowIso = () => new Date().toISOString();

/* 한국 시각으로 오늘이 며칠인가. 서버는 UTC로 돌지만 아이의 «오늘»은 KST다.
   이걸 안 맞추면 밤 10시에 한 미션이 내일 것으로 기록된다. */
const KST = 9 * 3600 * 1000;
function ymdKst(d) {
  const t = new Date((d ? d.getTime() : Date.now()) + KST);
  return t.toISOString().slice(0, 10).replace(/-/g, "");
}
// 다음날 오전 8시(KST)를 UTC ISO 로. 그때 자동 승인된다.
function autoAtIso() {
  const t = new Date(Date.now() + KST);
  t.setUTCHours(0, 0, 0, 0);
  t.setUTCDate(t.getUTCDate() + 1);
  return new Date(t.getTime() + 8 * 3600 * 1000 - KST).toISOString();
}
function bandOf(grade) {
  const g = parseInt(grade, 10) || 1;
  return g <= 2 ? "low" : g <= 4 ? "mid" : "high";
}
// 주말이면 주말 미션에서, 평일이면 평일에서 고른다(방학은 부모가 켤 때 쓴다)
function seasonOf(d) {
  const w = new Date((d ? d.getTime() : Date.now()) + KST).getUTCDay();
  return (w === 0 || w === 6) ? "weekend" : "weekday";
}

function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

// 자녀 폰도 부른다 — 그 아이 것만 열린다(index.js 관문 + 여기서 한 번 더).
async function gate(request, db, env, childId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  const child = await db.prepare(
    "SELECT id, grade, owner_token FROM children WHERE id = ? AND owner_token = ?"
  ).bind(childId, auth.ownerToken).first();
  if (!child) return { err: apiErr("NOT_FOUND") };
  if (auth.role === "child" && String(auth.childId) !== String(child.id)) return { err: apiErr("FORBIDDEN") };
  return { child, auth, isChild: auth.role === "child" };
}

const shape = (r) => ({
  id: r.id, code: r.mission_code, title: r.title, area: r.area,
  minutes: r.minutes, verify: r.verify, verify_hint: r.verify_hint,
  slot: r.slot, stars: r.stars, caution: r.caution || null,
  status: r.status, has_photo: !!r.photo_key,
  claimed_at: r.claimed_at, decided_at: r.decided_at, auto_at: r.auto_at,
  got: r.got_stars,
});

async function todayRows(db, childId, ymd) {
  const { results } = await db.prepare(
    `SELECT a.id, a.mission_code, a.status, a.photo_key, a.claimed_at, a.decided_at, a.auto_at,
            a.stars AS got_stars,
            m.title, m.area, m.minutes, m.verify, m.verify_hint, m.slot, m.stars, m.caution
       FROM mission_assign a JOIN missions m ON m.code = a.mission_code
      WHERE a.child_id = ? AND a.ymd = ?
      ORDER BY (a.status='open') DESC, m.verify, a.id`
  ).bind(childId, ymd).all();
  return results || [];
}

/* 오늘 것이 없으면 자동으로 채운다 — **부모가 안 들어와도 아이는 미션을 받는다.**
   즉시 2 + 대기 1 이 기본. 그날 아무 도장도 못 받는 상황을 막는다(규칙 ②). */
async function ensureToday(db, child) {
  const ymd = ymdKst();
  const have = await todayRows(db, child.id, ymd);
  if (have.length) return have;

  const band = bandOf(child.grade), season = seasonOf();
  const pick = async (verify, n) => {
    const { results } = await db.prepare(
      `SELECT code FROM missions
        WHERE band = ? AND season = ? AND verify = ? AND active = 1
        ORDER BY (id * 7 + ?) % 97 LIMIT ?`      // 날짜를 섞어 매일 같은 것만 나오지 않게
    ).bind(band, season, verify, parseInt(ymd, 10) % 97, n).all();
    return (results || []).map((x) => x.code);
  };
  let codes = [...(await pick("instant", 2)), ...(await pick("review", 1))];
  if (codes.length < DAY_PICK) codes = [...codes, ...(await pick("endday", DAY_PICK - codes.length))];
  codes = [...new Set(codes)].slice(0, DAY_PICK);

  const now = nowIso();
  for (const c of codes) {
    await db.prepare(
      "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
    ).bind(child.id, c, ymd, now).run();
  }
  return todayRows(db, child.id, ymd);
}

async function starsOf(db, childId) {
  const r = await db.prepare("SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id = ?").bind(childId).first();
  return (r && r.n) || 0;
}
async function addStars(db, childId, delta, reason) {
  await db.prepare("INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES (?, ?, ?, ?)")
    .bind(childId, delta, reason, nowIso()).run();
}

// ── GET /api/v1/children/{id}/missions ──────────────────────
async function getToday(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  const rows = await ensureToday(db, child);
  const done = rows.filter((r) => r.status === "done").length;
  const waiting = rows.filter((r) => r.status === "waiting").length;
  return apiList(rows.map(shape), {
    ymd: ymdKst(), band: bandOf(child.grade), season: seasonOf(),
    done, waiting, total: rows.length, stars: await starsOf(db, child.id), viewer: isChild ? "child" : "parent",
  });
}

/* ── GET /api/v1/missions — 부모가 고를 목록 ─────────────────
   공용 목록(owner_token IS NULL) + **우리 집 것**을 함께 준다.
   우리 집 것이 위로 온다 — 자기가 만든 것을 목록 바닥에서 찾게 하면 안 쓴다. */
async function listCatalog(request, db, env, url) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const band = url.searchParams.get("band") || "";
  const season = url.searchParams.get("season") || "";
  let sql = `SELECT code, band, season, title, area, minutes, cycle, verify, verify_hint, slot, stars, caution, why,
                    (owner_token IS NOT NULL) AS mine
               FROM missions WHERE active = 1 AND (owner_token IS NULL OR owner_token = ?)`;
  const b = [auth.ownerToken];
  // 우리 집 미션은 학년·요일을 안 가린다 — 만든 사람이 알아서 쓴다
  if (["low", "mid", "high"].includes(band)) { sql += " AND (owner_token IS NOT NULL OR band = ?)"; b.push(band); }
  if (["weekday", "weekend", "vacation", "patience"].includes(season)) {
    sql += " AND (owner_token IS NOT NULL OR season = ?)"; b.push(season);
  }
  sql += " ORDER BY mine DESC, area, minutes";
  const { results } = await db.prepare(sql).bind(...b).all();
  const { results: banned } = await db.prepare("SELECT title, reason FROM mission_banned").all();
  return apiList(results || [], { banned: banned || [] });
}

/* ── POST /api/v1/missions — 우리 집 미션 만들기 ─────────────
   「구몬 3장」·「윙크 20분」처럼 집마다 다른 것은 공용 목록에 못 담는다.
   한 번 만들면 계속 재사용하므로 매일 타자를 치는 게 아니다. */
const CUSTOM_MAX = 20;
async function createCustom(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const b = await readJson(request);
  const title = String((b && b.title) || "").trim().slice(0, 20);
  const minutes = Math.max(0, Math.min(120, parseInt((b && b.minutes) || 5, 10) || 5));
  const verify = ["instant", "review", "endday"].includes(b && b.verify) ? b.verify : "instant";
  const area = Object.prototype.hasOwnProperty.call(
    { body: 1, things: 1, study: 1, prep: 1, read: 1, family: 1, outside: 1, digital: 1, mind: 1, money: 1 },
    (b && b.area) || "") ? b.area : "study";
  if (title.length < 2) return apiErr("VALIDATION", { fields: { title: "미션 이름을 적어 주세요." } });

  const n = await db.prepare("SELECT COUNT(*) n FROM missions WHERE owner_token = ?").bind(auth.ownerToken).first();
  if ((n && n.n) >= CUSTOM_MAX) {
    return apiErr("LIMIT_EXCEEDED", null, `우리 집 미션은 ${CUSTOM_MAX}개까지 만들 수 있어요.`);
  }
  const stars = minutes >= 15 ? 3 : minutes >= 5 ? 2 : 1;
  const code = "U-" + crypto.randomUUID().slice(0, 8);
  await db.prepare(
    `INSERT INTO missions (code, band, season, title, area, minutes, cycle, verify, verify_hint, slot, stars, why, active, created_at, owner_token)
     VALUES (?, 'low', 'weekday', ?, ?, ?, 'daily', ?, ?, 'any', ?, '우리 집에서 만든 미션', 1, ?, ?)`
  ).bind(code, title, area, minutes, verify, verify === "review" ? "해낸 모습" : null, stars, nowIso(), auth.ownerToken).run();
  const row = await db.prepare("SELECT * FROM missions WHERE code = ?").bind(code).first();
  return apiOk({ mission: row }, 201);
}

// ── DELETE /api/v1/missions/{code} — 내가 만든 것만 ─────────
async function deleteCustom(request, db, env, code) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const row = await db.prepare("SELECT code FROM missions WHERE code = ? AND owner_token = ?")
    .bind(code, auth.ownerToken).first();
  if (!row) return apiErr("NOT_FOUND");
  // 이미 준 것은 그대로 둔다(도장이 사라지면 안 된다) — 앞으로 목록에만 안 나온다
  await db.prepare("UPDATE missions SET active = 0 WHERE code = ?").bind(code).run();
  return apiOk({ deleted: true, code });
}

// ── PUT /api/v1/children/{id}/missions — 부모가 오늘 것을 정한다 ──
async function setToday(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  if (isChild) return apiErr("FORBIDDEN");
  const b = await readJson(request);
  const codes = Array.isArray(b && b.codes) ? b.codes.slice(0, DAY_PICK).map(String) : null;
  if (!codes || !codes.length) return apiErr("VALIDATION", { fields: { codes: "미션을 골라 주세요." } });

  const { results: picked } = await db.prepare(
    `SELECT code, verify FROM missions WHERE active = 1 AND code IN (${codes.map(() => "?").join(",")})`
  ).bind(...codes).all();
  if (!picked.length) return apiErr("VALIDATION", { fields: { codes: "없는 미션이에요." } });
  /* 규칙 ② — 셋 다 사진이면 아이가 부담스럽다.
     (2026-08-02 이전엔 「그날 도장을 못 받는다」가 이유였는데, 이제 의뢰는 전부 부모 확인이라
      도장 시점은 어차피 같다. 남은 이유는 «사진 세 장은 숙제가 된다»는 것 하나다.) */
  if (picked.length > 1 && picked.every((p) => p.verify === "review")) {
    return apiErr("VALIDATION", { fields: { codes: "사진 없이 눌러서 보고하는 것도 하나 넣어 주세요." } });
  }

  const ymd = ymdKst(), now = nowIso();
  // 아직 손대지 않은 것만 치운다 — 이미 한 것을 지우면 아이가 받은 도장이 사라진다
  await db.prepare("DELETE FROM mission_assign WHERE child_id = ? AND ymd = ? AND status = 'open'")
    .bind(child.id, ymd).run();
  for (const p of picked) {
    await db.prepare(
      "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
    ).bind(child.id, p.code, ymd, now).run();
  }
  return apiOk({ items: (await todayRows(db, child.id, ymd)).map(shape) });
}

async function findAssign(db, ownerToken, id) {
  return db.prepare(
    `SELECT a.*, m.verify, m.stars AS mstars, m.title, c.owner_token
       FROM mission_assign a
       JOIN missions m ON m.code = a.mission_code
       JOIN children c ON c.id = a.child_id
      WHERE a.id = ? AND c.owner_token = ?`
  ).bind(id, ownerToken).first();
}

/* ── POST /api/v1/missions/{id}/done — 아이가 완료를 누른다 ──
   2026-08-02: 의뢰(랜덤 미션)는 **전부 부모 확인형**이 됐다. 그 자리에서 별이 나오지 않는다.
   즉시 판정은 일일 퀘스트 셋(급식·친구·과목)이 맡는다 — 그건 아이가 «고르기만» 하는 것이라
   맞고 틀림이 없고, 데이터가 쌓이는 게 목적이라 부모가 낄 자리가 없다.
   반대로 의뢰는 «했어요» 한마디로 별이 나오면 부모가 볼 이유가 사라진다.
   RPG로 치면 일일 퀘스트는 자동 정산, 의뢰는 의뢰인 검수다.
   부모가 안 봐도 다음날 아침 8시에 자동으로 나간다(autoAtIso) — 아이가 손해 보지 않는다.
   사진 미션은 원래부터 이 길이었다. 이제 셋이 같은 길로 모인다. */
async function claim(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a) return apiErr("NOT_FOUND");
  if (auth.role === "child" && String(auth.childId) !== String(a.child_id)) return apiErr("FORBIDDEN");
  if (a.status !== "open") return apiErr("VALIDATION", { status: a.status }, "이미 처리된 미션이에요.");
  if (a.verify === "review") return apiErr("VALIDATION", null, "사진을 찍어 보내주세요.");

  /* 별은 여기서 주지 않는다. approve() 나 autoApprove 크론이 준다.
     여기서 주고 나중에 또 주면 두 배가 나간다 — 별 원장은 되돌리기 어렵다. */
  const now = nowIso(), auto = autoAtIso();
  await db.prepare("UPDATE mission_assign SET status='waiting', claimed_at=?, auto_at=? WHERE id=?")
    .bind(now, auto, id).run();
  return apiOk({ status: "waiting", auto_at: auto });
}

/* ── POST /api/v1/missions/meal-rate — 급식 평가(지시서 0802-3 1-1) ──
   자녀 토큰 전용. 하루 한 번(UNIQUE child_id+ymd). 저장과 동시에 부모 대화로 흘린다 —
   부모 쪽 신규 UI 없음, 기존 messages 채널 재사용. 별 1개는 mission_stars 집계에 얹는다.
   ⚠ 적용 전 migrate_meal_ratings_2026-08-02.sql 필요. index.js 자녀 화이트리스트에도 경로 추가됨. */
export async function mealRate(request, db, auth) {
  if (auth.role !== "child") return apiErr("FORBIDDEN");
  const ymd = ymdKst();
  const b = await request.json().catch(() => null);
  const stars = Number(b?.stars);
  if (!Number.isInteger(stars) || stars < 1 || stars > 5) return apiErr("VALIDATION", { stars: "1~5" });
  const items = Array.isArray(b?.items) ? b.items.slice(0, 20) : [];
  const now = new Date().toISOString();

  /* 하루 한 번 — UNIQUE(child_id, ymd) 가 막는다. changes 가 0이면 이미 한 것이다.
     ⚠ 여기서 별을 먼저 주고 INSERT 를 뒤에 하면 여러 번 눌러 별을 긁을 수 있다. 순서를 지킨다. */
  const ins = await db.prepare(
    "INSERT OR IGNORE INTO meal_ratings (child_id, ymd, stars, created_at) VALUES (?1, ?2, ?3, ?4)")
    .bind(auth.childId, ymd, stars, now).run();
  if (!ins.meta.changes) return apiErr("VALIDATION", { ymd: "오늘 급식은 이미 골랐어요" });

  /* 항목별 — **원문·합친 이름·종류를 다 남긴다.**
     합치는 사전은 쌓인 식단표를 실제로 훑어본 뒤에 좋아진다. 그때 원문에서 다시 계산하려면
     원문이 살아 있어야 한다. 종류(볶음·국·튀김…)는 개별 메뉴가 한 주에 거의 안 겹쳐서
     그것만으로는 표본이 안 되기 때문에 같이 쌓는다. */
  for (const it of items) {
    const raw = String(it?.raw || "").slice(0, 60);
    if (!raw) continue;
    await db.prepare(
      `INSERT INTO meal_rating_items (child_id, ymd, dish_raw, dish_key, dish_cat, rank, created_at)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`)
      .bind(auth.childId, ymd, raw, String(it?.key || raw).slice(0, 60),
            String(it?.cat || "기타").slice(0, 20),
            Number.isInteger(it?.rank) ? it.rank : null, now).run();
  }

  // 즉시판정 — 사진도 기다림도 없다. 별은 원장에 적어야 집계(starsOf)에 잡힌다.
  await addStars(db, auth.childId, 1, "meal-rate");
  return apiOk({ got: 1, total_stars: await starsOf(db, auth.childId), ymd });
}

/* ── POST /api/v1/missions/play-log — 오늘 누구랑 놀았어(2026-08-02) ──
   부모는 아이 교우관계를 모른다. 아이가 먼저 말하지 않는다. 그런데 부모가 제일 알고 싶은 것이다.
   받는 건 **이름 문자열 하나뿐**이다 — 성별·연락처·학교 아무것도 안 받는다.
   「혼자 놀았어」도 답이다. 요즘 혼자 논다는 것도 부모가 알아야 할 신호다.
   ⚠ 적용 전 migrate_play_log_2026-08-02.sql 필요. */
export async function playLog(request, db, auth) {
  if (auth.role !== "child") return apiErr("FORBIDDEN");
  const ymd = ymdKst();
  const b = await request.json().catch(() => null);
  const alone = !!b?.alone;
  const names = Array.isArray(b?.friends)
    ? [...new Set(b.friends.map((x) => String(x || "").trim()).filter(Boolean))].slice(0, 10)
    : [];
  if (!alone && !names.length) return apiErr("VALIDATION", { friends: "한 명은 골라야 해요" });
  const now = new Date().toISOString();

  // 하루 한 번 — 별을 먼저 주고 INSERT 를 뒤에 하면 여러 번 눌러 별을 긁는다. 순서를 지킨다.
  const day = await db.prepare(
    "INSERT OR IGNORE INTO play_days (child_id, ymd, alone, created_at) VALUES (?1, ?2, ?3, ?4)")
    .bind(auth.childId, ymd, alone ? 1 : 0, now).run();
  if (!day.meta.changes) return apiErr("VALIDATION", { ymd: "오늘은 이미 골랐어요" });

  for (const name of names) {
    // 친구 목록은 이름 하나로 유지한다(UNIQUE child_id+name). 같은 이름은 한 줄뿐.
    await db.prepare("INSERT OR IGNORE INTO kid_friends (child_id, name, created_at) VALUES (?1, ?2, ?3)")
      .bind(auth.childId, name.slice(0, 10), now).run();
    await db.prepare("INSERT INTO play_log (child_id, ymd, name, created_at) VALUES (?1, ?2, ?3, ?4)")
      .bind(auth.childId, ymd, name.slice(0, 10), now).run();
  }

  await addStars(db, auth.childId, 1, "play-log");
  return apiOk({ got: 1, total_stars: await starsOf(db, auth.childId), ymd });
}

/* ── POST /api/v1/missions/subject-log — 오늘 재밌었던 과목(2026-08-02) ──
   일일 퀘스트 셋째. 시간표에 이미 있는 과목이라 아이는 고르기만 한다.
   성적표가 «잘하는 것»을 알려준다면 이건 «재밌어하는 것»을 알려준다 — 부모가 못 보던 축이다.
   과목은 주 단위로 반복돼서 한 달이면 표본이 충분하다(개별 급식 메뉴와 다른 점).
   ⚠ 적용 전 migrate_subject_log_2026-08-02.sql 필요. */
export async function subjectLog(request, db, auth) {
  if (auth.role !== "child") return apiErr("FORBIDDEN");
  const ymd = ymdKst();
  const b = await request.json().catch(() => null);
  const subject = String(b?.subject || "").trim().slice(0, 20);
  if (!subject) return apiErr("VALIDATION", { subject: "과목을 골라야 해요" });
  const now = new Date().toISOString();

  // 하루 한 번 — 별을 먼저 주고 INSERT 를 뒤에 하면 여러 번 눌러 별을 긁는다. 순서를 지킨다.
  const ins = await db.prepare(
    "INSERT OR IGNORE INTO subject_log (child_id, ymd, subject, created_at) VALUES (?1, ?2, ?3, ?4)")
    .bind(auth.childId, ymd, subject, now).run();
  if (!ins.meta.changes) return apiErr("VALIDATION", { ymd: "오늘은 이미 골랐어요" });

  await addStars(db, auth.childId, 1, "subject-log");
  return apiOk({ got: 1, total_stars: await starsOf(db, auth.childId), ymd });
}

// ── POST /api/v1/missions/{id}/photo — 사진 제출 → 대기 ─────
async function submitPhoto(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a) return apiErr("NOT_FOUND");
  if (auth.role === "child" && String(auth.childId) !== String(a.child_id)) return apiErr("FORBIDDEN");
  if (a.status !== "open") return apiErr("VALIDATION", { status: a.status }, "이미 처리된 미션이에요.");

  const form = await request.formData().catch(() => null);
  const file = form && form.get("photo");
  if (!file || typeof file.size !== "number") return apiErr("VALIDATION", { fields: { photo: "사진이 필요해요." } });
  if (file.size > PHOTO_MAX) return apiErr("VALIDATION", { fields: { photo: "사진이 너무 커요." } });

  /* 미션 사진은 **서랍과 다른 곳**에 둔다. 매일 쌓이는 임시 증거라 7일 뒤 지운다.
     서랍에 섞으면 상장 사이에 실내화 사진이 끼어 서랍의 값이 사라진다. */
  const key = `missions/${a.child_id}/${id}.jpg`;
  try {
    await env.RECORDS.put(key, file.stream(), { httpMetadata: { contentType: file.type || "image/jpeg" } });
  } catch (_) {
    return apiErr("STORAGE");
  }
  const now = nowIso();
  await db.prepare("UPDATE mission_assign SET status='waiting', photo_key=?, claimed_at=?, auto_at=? WHERE id=?")
    .bind(key, now, autoAtIso(), id).run();
  return apiOk({ status: "waiting", auto_at: autoAtIso() });
}

// ── GET /api/v1/missions/{id}/photo — 부모가 본다 ───────────
async function getPhoto(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("NOT_FOUND");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a || !a.photo_key) return apiErr("NOT_FOUND");
  const obj = await env.RECORDS.get(a.photo_key);
  if (!obj) return apiErr("NOT_FOUND");
  return new Response(obj.body, {
    headers: { "Content-Type": obj.httpMetadata?.contentType || "image/jpeg", "Cache-Control": "private, max-age=300" },
  });
}

// ── POST /api/v1/missions/{id}/skip — 「오늘은 못 했어요」 ──
// 벌이 없다. 도장이 안 늘 뿐이다. 안 한 날을 말할 방법이 있어야 거짓말이 준다.
async function skip(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a) return apiErr("NOT_FOUND");
  if (auth.role === "child" && String(auth.childId) !== String(a.child_id)) return apiErr("FORBIDDEN");
  if (a.status !== "open") return apiErr("VALIDATION", { status: a.status }, "이미 처리된 미션이에요.");
  await db.prepare("UPDATE mission_assign SET status='skipped', decided_at=? WHERE id=?").bind(nowIso(), id).run();
  return apiOk({ status: "skipped" });
}

// ── POST /api/v1/missions/{id}/approve — 부모가 확인 ────────
async function approve(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a) return apiErr("NOT_FOUND");
  if (a.status !== "waiting") return apiErr("VALIDATION", { status: a.status }, "확인할 수 없는 상태예요.");
  await db.prepare("UPDATE mission_assign SET status='done', decided_at=?, stars=? WHERE id=?")
    .bind(nowIso(), a.mstars, id).run();
  await addStars(db, a.child_id, a.mstars, "mission:" + a.mission_code);
  return apiOk({ status: "done", got: a.mstars, stars: await starsOf(db, a.child_id) });
}

/* ── POST /api/v1/missions/{id}/revert — 부모가 되돌린다 ──
   「거짓말했지?」가 아니라 **「다시 해볼까?」**다. 앱이 문구를 그렇게 주면 부모도 그렇게 말한다.
   취소가 없으면 아이가 그냥 눌러버리고, 그건 훈련이 아니라 방치다. */
async function revert(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const a = await findAssign(db, auth.ownerToken, id);
  if (!a) return apiErr("NOT_FOUND");
  /* skipped 도 되돌릴 수 있어야 한다 (2026-08-02 폰 실측).
     아이가 「오늘은 못 했어요」를 잘못 누르면 **그날 내내 손도 못 대는** 상태였다.
     못 하겠다고 말한 걸 되살리는 건 부모 판단이다 — 다시 할 기회를 막을 이유가 없다. */
  if (a.status !== "done" && a.status !== "waiting" && a.status !== "skipped") {
    return apiErr("VALIDATION", { status: a.status }, "되돌릴 수 없는 상태예요.");
  }
  if (a.stars) await addStars(db, a.child_id, -a.stars, "revert:" + a.mission_code);
  /* 되돌리면 **사진도 같이 지운다** (2026-08-02 폰 실측으로 잡음).
     decided_at 을 NULL 로 미는 순간 아래 7일 정리 크론의 조건(decided_at IS NOT NULL)에서 빠져
     그 사진은 **아무도 안 지우는 상태로 R2에 영원히 남았다.** 아이 사진이라 더 그러면 안 된다.
     어차피 «다시 해볼까?» 는 그 사진을 무효로 하는 행동이라, 남길 이유도 없다. */
  if (a.photo_key) { try { await env.RECORDS.delete(a.photo_key); } catch (_) {} }
  await db.prepare("UPDATE mission_assign SET status='open', claimed_at=NULL, decided_at=NULL, auto_at=NULL, stars=0, photo_key=NULL WHERE id=?")
    .bind(id).run();
  return apiOk({ status: "open", stars: await starsOf(db, a.child_id) });
}

/* ── 크론이 부른다 ──────────────────────────────────────────
   ① 다음날 오전 8시가 지난 「대기」는 **묻지도 따지지도 않고 승인**한다.
      이 한 줄이 아이에게 «내가 한 일은 반드시 보상받는다»를 증명한다. 기다림은 여기서 배워진다.
   ② 7일 지난 미션 사진은 지운다. 서랍과 달리 임시 증거라 쌓아둘 이유가 없다. */
export async function missionCron(db, env) {
  const now = nowIso();
  const { results: due } = await db.prepare(
    "SELECT id, child_id, mission_code FROM mission_assign WHERE status='waiting' AND auto_at IS NOT NULL AND auto_at <= ? LIMIT 200"
  ).bind(now).all();
  for (const d of due) {
    const m = await db.prepare("SELECT stars FROM missions WHERE code = ?").bind(d.mission_code).first();
    const s = (m && m.stars) || 1;
    await db.prepare("UPDATE mission_assign SET status='done', decided_at=?, stars=? WHERE id=?").bind(now, s, d.id).run();
    await addStars(db, d.child_id, s, "mission:" + d.mission_code);
  }
  const cut = new Date(Date.now() - PHOTO_KEEP_DAYS * 86400000).toISOString();
  const { results: old } = await db.prepare(
    "SELECT id, photo_key FROM mission_assign WHERE photo_key IS NOT NULL AND decided_at IS NOT NULL AND decided_at < ? LIMIT 200"
  ).bind(cut).all();
  for (const o of old) {
    try { await env.RECORDS.delete(o.photo_key); } catch (_) {}
    await db.prepare("UPDATE mission_assign SET photo_key=NULL WHERE id=?").bind(o.id).run();
  }
  return { approved: due.length, purged: old.length };
}

// ── 라우터 ──────────────────────────────────────────────────
/* ── GET /api/v1/children/{id}/report?month=YYYYMM — 부모 월간 리포트 ──
   ⚠ **표본 수를 반드시 같이 준다.** 「3번 중 2번」이 「67%」보다 정직하다.
      한 반 30명·같은 성별 15명이라 분모가 작은 게 정상이고, 비율만 보여주면 부모가 과신한다.
   ⚠ 개별 급식 메뉴는 **2회 이상 나온 것만.** 한 주 25품에 겹치는 게 밥·김치뿐이라
      1회짜리를 「좋아하는 메뉴」로 올리면 거짓이 된다. 그래서 **종류(dish_cat)** 를 같이 센다.
   자녀 토큰은 막는다 — 이건 부모가 보는 화면이다. */
async function report(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  if (isChild) return apiErr("FORBIDDEN");

  const url = new URL(request.url);
  const raw = String(url.searchParams.get("month") || "");
  const month = /^\d{6}$/.test(raw) ? raw : ymdKst().slice(0, 6);
  const like = month + "%";
  const all = async (sql, ...b) => ((await db.prepare(sql).bind(...b).all()).results || []);

  // ── 급식 ──
  const mealDays = await all(
    "SELECT COUNT(*) n, AVG(stars) avg FROM meal_ratings WHERE child_id=?1 AND ymd LIKE ?2", child.id, like);
  const cats = await all(
    `SELECT dish_cat cat, COUNT(*) shown, SUM(CASE WHEN rank=1 THEN 1 ELSE 0 END) best
       FROM meal_rating_items WHERE child_id=?1 AND ymd LIKE ?2
      GROUP BY dish_cat HAVING shown > 0 ORDER BY best DESC, shown DESC`, child.id, like);
  const dishes = await all(
    `SELECT dish_key name, COUNT(*) shown, SUM(CASE WHEN rank=1 THEN 1 ELSE 0 END) best
       FROM meal_rating_items WHERE child_id=?1 AND ymd LIKE ?2 AND dish_cat != '주식'
      GROUP BY dish_key HAVING shown >= 2 ORDER BY best DESC, shown DESC LIMIT 8`, child.id, like);

  // ── 친구 ── 혼자 논 날도 같이 준다. 「요즘 혼자 노는 날이 늘었다」가 부모가 알아야 할 신호다
  const friends = await all(
    `SELECT name, COUNT(*) n FROM play_log WHERE child_id=?1 AND ymd LIKE ?2
      GROUP BY name ORDER BY n DESC LIMIT 8`, child.id, like);
  const days = await all(
    "SELECT COUNT(*) n, SUM(alone) alone FROM play_days WHERE child_id=?1 AND ymd LIKE ?2", child.id, like);

  // ── 과목 ── 주 단위로 반복돼서 한 달이면 표본이 는다
  const subjects = await all(
    `SELECT subject, COUNT(*) n FROM subject_log WHERE child_id=?1 AND ymd LIKE ?2
      GROUP BY subject ORDER BY n DESC LIMIT 8`, child.id, like);

  return apiOk({
    month,
    meal: { days: mealDays[0]?.n || 0, avg_stars: mealDays[0]?.avg ? Math.round(mealDays[0].avg * 10) / 10 : null,
            cats, dishes },
    play: { days: days[0]?.n || 0, alone: days[0]?.alone || 0, friends },
    subject: { days: subjects.reduce((s, x) => s + x.n, 0), items: subjects },
  });
}

/* ── GET /api/v1/children/{id}/marks?month=YYYYMM — 달력 «아이 흔적» (2026-08-03) ──
   부모 앱 달력이 날짜마다 점을 찍는 데 쓴다. 리포트(월 합계)와는 다른 것이다 —
   저건 «한 달 동안 무엇을 좋아했나», 이건 «며칟날 무엇을 했나»다.

   ⚠ 앱의 `marksOf(ymd)` 가 읽는 모양 그대로 돌려준다. 모양을 바꾸면 앱이 화면을 다시 짜야 한다:
        days["20260803"] = { stamp: 2, of: 3, photo: 1, meal: 4 }
      · stamp = 도장 받은 개수(done)   · of    = 그날 준 미션 개수
      · photo = 사진으로 내는 미션 개수 · meal  = 급식 평가 별점(1~5, 없으면 없음)
   ⚠ photo 를 `photo_key IS NOT NULL` 로 세면 **지난 달이 전부 0이 된다** —
      미션 사진은 승인 7일 뒤 지워지기 때문이다(PHOTO_KEEP_DAYS).
      그래서 «사진으로 내는 미션이었나»(missions.verify='review')로 센다. 이건 안 지워진다.
   ⚠ 값이 하나도 없는 날은 **키를 안 만든다.** 빈 객체를 날마다 실어 보내면
      한 달이면 30개 쓰레기가 오가고, 앱은 «0개»와 «모른다»를 구별 못 하게 된다.
   ⚠ 자녀 토큰도 자기 것은 볼 수 있다 — 아이가 자기 달력을 보는 건 막을 이유가 없다. */
async function marks(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;

  const url = new URL(request.url);
  const raw = String(url.searchParams.get("month") || "");
  const month = /^\d{6}$/.test(raw) ? raw : ymdKst().slice(0, 6);
  const like = month + "%";
  const all = async (sql, ...b) => ((await db.prepare(sql).bind(...b).all()).results || []);

  const days = {};
  const at = (ymd) => (days[ymd] = days[ymd] || {});

  // 미션 — 하루치를 한 줄로 접어서 가져온다. 날짜별 반복 질의는 한 달이면 30번이다
  const ms = await all(
    `SELECT a.ymd ymd,
            COUNT(*) of_n,
            SUM(CASE WHEN a.status = 'done' THEN 1 ELSE 0 END) stamp,
            SUM(CASE WHEN m.verify = 'review' THEN 1 ELSE 0 END) photo
       FROM mission_assign a
       LEFT JOIN missions m ON m.code = a.mission_code
      WHERE a.child_id = ?1 AND a.ymd LIKE ?2
      GROUP BY a.ymd`, child.id, like);
  ms.forEach((r) => {
    const d = at(r.ymd);
    d.of = r.of_n || 0;
    if (r.stamp) d.stamp = r.stamp;
    if (r.photo) d.photo = r.photo;
  });

  // 급식 평가 — 하루 한 번(UNIQUE child_id, ymd)이라 그대로 얹는다
  const me = await all(
    "SELECT ymd, stars FROM meal_ratings WHERE child_id = ?1 AND ymd LIKE ?2", child.id, like);
  me.forEach((r) => { if (r.stars) at(r.ymd).meal = r.stars; });

  // 아무것도 안 한 날은 빼고 보낸다(위 ⚠ 참고)
  Object.keys(days).forEach((k) => { if (!days[k].stamp && !days[k].photo && !days[k].meal) delete days[k]; });

  return apiOk({ month, days });
}

export async function handleMissionApi(request, db, env, url) {
  const p = url.pathname, m = request.method;

  if (p === "/api/v1/missions" && m === "GET") return listCatalog(request, db, env, url);
  if (p === "/api/v1/missions" && m === "POST") return createCustom(request, db, env);
  const mine = p.match(/^\/api\/v1\/missions\/(U-[0-9a-f]{8})$/);
  if (mine && m === "DELETE") return deleteCustom(request, db, env, mine[1]);

  let x = p.match(/^\/api\/v1\/children\/(\d+)\/report\/?$/);
  if (x && m === "GET") return report(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/marks\/?$/);
  if (x && m === "GET") return marks(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/missions\/?$/);
  if (x) {
    if (m === "GET") return getToday(request, db, env, x[1]);
    if (m === "PUT") return setToday(request, db, env, x[1]);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  x = p.match(/^\/api\/v1\/missions\/(\d+)\/(done|photo|skip|approve|revert)$/);
  if (x) {
    const id = x[1], act = x[2];
    if (act === "photo" && m === "GET") return getPhoto(request, db, env, id);
    if (m !== "POST") return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
    if (act === "done") return claim(request, db, env, id);
    if (act === "photo") return submitPhoto(request, db, env, id);
    if (act === "skip") return skip(request, db, env, id);
    if (act === "approve") return approve(request, db, env, id);
    if (act === "revert") return revert(request, db, env, id);
  }
  return null;   // 우리 것이 아니다
}
