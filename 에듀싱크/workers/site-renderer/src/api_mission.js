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
// 스타코인은 star_core 한 곳에서만 다룬다 — 리밋을 여기저기서 세면 반드시 어긋난다(2026-08-08)
import { grantStars, spendStars, starsOf as coinBalance, coinState, BONUS,
         ECON, clampLine, starLineOf, coinLimitOf, missionBudgetOf } from "./star_core.js";

/* ⚠ 옛 「하루 3개」. 이제 **개수가 아니라 별 라인**으로 채운다(2026-08-12) —
   저학년 미션은 별이 1~2 라서 3개면 4점밖에 안 됐다. 여기 남은 건 안전선 하나뿐:
   부모가 목록에서 고를 때 한 번에 담을 수 있는 최대치(ECON.maxPerDay). */
const DAY_PICK = ECON.maxPerDay;
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

/* ── ⚙️ GET /api/v1/children/{id}/econ — 경제 설정을 앱에 내려보낸다 ──
   🔴 **앱은 이 숫자들을 자기 안에 안 들고 있다.** 여기서 받아 쓴다.
      그래서 `star_core.js` 의 ECON 을 고치고 워커만 배포하면 **그 자리에서 반영된다** —
      APK 를 다시 만들 필요도, 스토어를 기다릴 필요도 없다(2026-08-12 대표님 지시).
   ⚠ 새 숫자를 만들면 **여기에도 실어라.** 안 실으면 앱은 옛 임시값을 계속 쓴다. */
async function econ(request, db, env, childId) {
  const g = await gate(request, db, env, childId);
  if (g.err) return g.err;
  const line = await starLineOf(db, g.child.id);
  return apiOk({
    star_line: line,
    line_min: ECON.starLineMin, line_max: ECON.starLineMax, line_step: ECON.starLineStep,
    line_default: ECON.starLineDefault,
    limit: coinLimitOf(line),
    hidden_limit: ECON.hiddenLimit,
    max_per_day: ECON.maxPerDay, min_per_day: ECON.minPerDay,
    mission_budget: missionBudgetOf(line),   // 의뢰 미션이 맡는 몫 — 나머지는 퀴즈·세트·기록
    auto_pass_instant: !!ECON.autoPassInstant,
    bonus: ECON.bonus,
    retry_cost: ECON.retryCost,
    coin: await coinState(db, g.child.id),
  });
}

/* ── PUT /api/v1/children/{id}/star-line — 부모가 하루 별 예산을 정한다 ──
   아이는 못 바꾼다. 이게 「무조건 통과」를 막는 유일한 손잡이라서 아이가 쥐면 의미가 없다. */
async function setStarLine(request, db, env, childId) {
  const g = await gate(request, db, env, childId);
  if (g.err) return g.err;
  if (g.isChild) return apiErr("FORBIDDEN", null, "별 라인은 부모님이 정해요.");
  const b = await readJson(request);
  const raw = Number(b && b.star_line);
  if (!Number.isFinite(raw) || raw <= 0) {
    return apiErr("VALIDATION", { fields: { star_line: "하루 별 예산을 정해 주세요." } });
  }
  const line = clampLine(raw);
  await db.prepare("UPDATE children SET star_line = ? WHERE id = ?").bind(line, g.child.id).run();
  /* ⚠ 오늘 이미 배정된 미션은 **건드리지 않는다.** 아이가 보고 있던 목록이 눈앞에서 바뀌면
     「했는데 없어졌다」가 된다. 새 라인은 내일 배정부터 — 오늘 당장 늘리고 싶으면
     부모가 add 로 하나 더 주면 된다(그 길을 이번에 열었다). */
  return apiOk({ star_line: line, limit: coinLimitOf(line), coin: await coinState(db, g.child.id) });
}

/* ── GET /api/v1/children/{id}/missions/week?code=X — 이 미션의 지난 이레 ──
   부모가 「이것만 바꾸기」를 누를지 정하는 근거다. 설명이 아니라 **해 온 기록**을 보여준다.
   done=했다 · miss=받았는데 안 했다 · none=그날 이 미션이 없었다. */
async function missionWeek(request, db, env, childId, url) {
  const g = await gate(request, db, env, childId);
  if (g.err) return g.err;
  const code = String(url.searchParams.get("code") || "");
  if (!code) return apiErr("VALIDATION", null, "어떤 미션인지 알 수 없어요.");
  const WD = ["일", "월", "화", "수", "목", "금", "토"];
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000);
    const ymd = ymdKst(d);
    const r = await db.prepare(
      "SELECT status FROM mission_assign WHERE child_id = ? AND ymd = ? AND mission_code = ?"
    ).bind(g.child.id, ymd, code).first();
    days.push({
      ymd, wd: WD[new Date(d.getTime() + 9 * 3600 * 1000).getUTCDay()],
      today: i === 0,
      st: !r ? "none" : r.status === "done" ? "done" : i === 0 ? "none" : "miss",
    });
  }
  return apiOk({ code, days });
}

const shape = (r) => ({
  id: r.id, code: r.mission_code, title: r.title, area: r.area,
  minutes: r.minutes, verify: r.verify, verify_hint: r.verify_hint,
  slot: r.slot, stars: r.stars, caution: r.caution || null,
  why: r.why || null,   // 미션 하나 화면의 «왜 이 미션인가요» — 빈 화면 채우기(2026-08-12 대표님)
  status: r.status, has_photo: !!r.photo_key,
  claimed_at: r.claimed_at, decided_at: r.decided_at, auto_at: r.auto_at,
  got: r.got_stars,
});

async function todayRows(db, childId, ymd) {
  const { results } = await db.prepare(
    `SELECT a.id, a.mission_code, a.status, a.photo_key, a.claimed_at, a.decided_at, a.auto_at,
            a.stars AS got_stars,
            m.title, m.area, m.minutes, m.verify, m.verify_hint, m.slot, m.stars, m.caution, m.why
       FROM mission_assign a JOIN missions m ON m.code = a.mission_code
      WHERE a.child_id = ? AND a.ymd = ?
      ORDER BY a.id`      /* 🔴 배정 순서 고정 — «안 한 것 먼저»로 재정렬했더니 도장을 찍는 순간
                             줄이 자리를 바꿔 화면이 널뛰었다(2026-08-12 대표님 실사용 발견).
                             한 일은 제자리에서 ✓ 로 바뀌어야 한다. */
  ).bind(childId, ymd).all();
  return results || [];
}

/* 오늘 것이 없으면 자동으로 채운다 — **부모가 안 들어와도 아이는 미션을 받는다.**
   그날 아무 도장도 못 받는 상황을 막는다(규칙 ②).

   ── 2026-08-12 «별 라인»으로 바뀐 것 ────────────────────────────────
   옛 방식은 «즉시 2 + 사진 1» 로 **개수를 고정**했다. 그런데 저학년 미션은 별이 1~2 라
   3개를 다 해도 4점이었다 — 상한 60 은커녕 15도 안 됐다.
   이제 **부모가 정한 별 라인이 찰 때까지** 넣는다. 학년이 올라 별이 커지면 개수는 저절로 준다.
   ⚠ 개수 안전선은 남긴다 — 1점짜리로 라인을 채우면 20개가 되고, 그건 미션이 아니라 숙제다.
   ⚠ 사진(review)은 **하루 한 장까지**. 세 장은 아이에게 숙제가 된다(규칙 ②의 원래 이유). */
async function ensureToday(db, child) {
  const ymd = ymdKst();
  const have = await todayRows(db, child.id, ymd);
  if (have.length) return have;

  const line = missionBudgetOf(await starLineOf(db, child.id));
  const band = bandOf(child.grade), season = seasonOf();

  /* ⚠ **후보를 잘라서 뽑지 마라.** 한때 `LIMIT 16` 으로 뽑았는데, 그 16 개 안에 3점짜리가
     한 개밖에 안 들어와서 라인을 20·40·60 어디에 둬도 별합이 13 에서 멈췄다(2026-08-12 실측).
     밴드별 후보는 50 줄 남짓이라 통째로 읽어도 싸다 — 고르는 일은 아래 그리디가 한다. */
  const { results: all } = await db.prepare(
    `SELECT code, stars, verify FROM missions
      WHERE band = ? AND season = ? AND active = 1 AND verify IN ('instant','review','endday')
      ORDER BY (id * 7 + ?) % 97`      // 날짜를 섞어 매일 같은 것만 나오지 않게
  ).bind(band, season, parseInt(ymd, 10) % 97).all();
  const cand = all || [];

  /* 사진 1개를 먼저 확보한 뒤 나머지를 채운다 — 사진이 뒤로 밀려 영영 안 걸리는 걸 막는다. */
  const shot = cand.filter((m) => m.verify === "review").slice(0, 1);
  const rest = cand.filter((m) => m.verify !== "review");

  /* ── 예산을 «크기에 맞는 것»으로 채운다 ────────────────────────────
     ⚠ 후보를 순서대로 집으면 1점짜리부터 걸려서 개수 안전선(8)에 먼저 닿는다 —
        실측: 라인을 20·40·60 어디에 둬도 별합이 13 에서 멈췄다(2026-08-12).
     그래서 매번 «남은 예산 ÷ 남은 자리»를 계산해 그 크기에 **가장 가까운 것**을 집는다.
     라인이 크면 3점짜리가, 작으면 1점짜리가 자연히 걸린다. 순서는 이미 날짜로 섞여 있으므로
     같은 크기 안에서는 매일 다른 것이 나온다.
     ⚠ 사진(shot)은 예산과 무관하게 **먼저 한 장** 넣는다 — 뒤로 밀리면 영영 안 걸린다. */
  const codes = [];
  let sum = 0;
  for (const m of shot) { codes.push(m.code); sum += m.stars || 1; }

  /* 목표 «개수»를 먼저 정한다 — 몫 ÷ 바라는 크기(2.5).
     ⚠ 남은 자리를 maxPerDay 로 세면 want 가 1 로 떨어져서 ★1 짜리를 잔뜩 집는다
       (실측: 라인 20 에 ★1×7). 목표 개수로 세야 «적고 굵게»가 나온다. */
  const target = Math.max(ECON.minPerDay,
    Math.min(ECON.maxPerDay, Math.ceil(line / ECON.avgStarTarget)));

  const pool = rest.filter((m) => !codes.includes(m.code));
  while (codes.length < ECON.maxPerDay && pool.length) {
    if (sum >= line && codes.length >= ECON.minPerDay) break;
    const slotsLeft = Math.max(1, target - codes.length);
    const want = Math.max(1, Math.ceil(Math.max(0, line - sum) / slotsLeft));
    /* 원하는 크기에 가장 가까운 것. 같으면 «큰 쪽»을 집는다 —
       작은 쪽을 집으면 남은 자리로 예산을 못 채우고 또 개수에 먼저 걸린다. */
    let best = 0;
    for (let i = 1; i < pool.length; i++) {
      const a = Math.abs((pool[i].stars || 1) - want), b = Math.abs((pool[best].stars || 1) - want);
      if (a < b || (a === b && (pool[i].stars || 1) > (pool[best].stars || 1))) best = i;
    }
    const m = pool.splice(best, 1)[0];
    codes.push(m.code); sum += m.stars || 1;
  }

  /* ── 재고가 얇은 밴드·시즌을 위한 보충 ─────────────────────────────
     2026-08-12 실측: **고학년 주말은 사진 아닌 미션이 단 2개**다(사진은 14개).
     즉시형만 고집하면 그런 날은 미션이 두세 개로 끝나 아이가 할 게 없다.
     그래서 예산이 남으면 사진을 **한 장 더까지** 얹는다.
     ⚠ 두 장이 상한이다. 세 장은 미션이 아니라 숙제가 된다(규칙 ②). */
  const MAX_SHOTS = 2;
  if (sum < line && codes.length < ECON.maxPerDay) {
    const more = cand.filter((m) => m.verify === "review" && !codes.includes(m.code));
    while (codes.length < ECON.maxPerDay && sum < line && more.length
           && codes.filter((c) => cand.find((m) => m.code === c && m.verify === "review")).length < MAX_SHOTS) {
      const m = more.shift();
      codes.push(m.code); sum += m.stars || 1;
    }
  }

  const now = nowIso();
  for (const c of codes) {
    await db.prepare(
      "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
    ).bind(child.id, c, ymd, now).run();
  }
  return todayRows(db, child.id, ymd);
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
    done, waiting, total: rows.length, stars: await coinBalance(db, child.id), viewer: isChild ? "child" : "parent",
  });
}

/* ── POST /api/v1/children/{id}/missions/reroll — 🎲 리롤 (지시서 §5②) ──
   «오늘 이거 말고 다른 거» 를 아이가 스스로 한 번 바꾼다. 자율성이 이 기능의 전부다.

   ⚠ **하루 한 번을 화면이 세지 않는다.** 앱을 껐다 켜면 화면 계산은 초기화된다
     (상점 상한·PIN 과 같은 이유). 서버가 막되, 세는 로직을 또 쓰지 않는다 —
     `mission_reroll` 의 PRIMARY KEY(child_id, ymd) 가 «하루 한 번»을 자연히 강제한다.
     INSERT 가 먹으면 오늘 처음이고, 안 먹으면 이미 쓴 것이다.
   ⚠ **이미 손댄 미션은 안 건드린다.** status='open' 인 것만 바꾼다 —
     아이가 해낸 것(waiting/done)을 리롤로 날리면 그건 벌이다.
   ⚠ 방금 있던 코드는 **빼고 뽑는다.** 안 그러면 눌러도 같은 게 나와 «고장»으로 읽힌다. */
async function reroll(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const ymd = ymdKst();

  const ins = await db.prepare(
    "INSERT OR IGNORE INTO mission_reroll (child_id, ymd, created_at) VALUES (?, ?, ?)"
  ).bind(child.id, ymd, nowIso()).run();
  if (!ins.meta.changes) {
    return apiErr("LIMIT_EXCEEDED", null, "오늘은 이미 한 번 바꿨어요. 내일 다시 할 수 있어요.");
  }

  const rows = await todayRows(db, child.id, ymd);
  const open = rows.filter((r) => r.status === "open");
  if (!open.length) {
    return apiErr("VALIDATION", null, "바꿀 수 있는 미션이 없어요.");
  }
  const keep = rows.filter((r) => r.status !== "open").map((r) => r.mission_code);
  const oldCodes = open.map((r) => r.mission_code);

  await db.prepare("DELETE FROM mission_assign WHERE child_id = ? AND ymd = ? AND status = 'open'")
    .bind(child.id, ymd).run();

  // 방금 것 + 남아 있는 것을 빼고 새로 뽑는다
  const exclude = [...new Set([...oldCodes, ...keep])];
  const band = bandOf(child.grade), season = seasonOf();
  const holes = exclude.map(() => "?").join(",") || "''";
  const { results } = await db.prepare(
    `SELECT code FROM missions
      WHERE band = ? AND season = ? AND active = 1 AND code NOT IN (${holes})
      ORDER BY (id * 13 + ?) % 89 LIMIT ?`
  ).bind(band, season, ...exclude, parseInt(ymd, 10) % 89, open.length).all();
  let codes = (results || []).map((x) => x.code);

  /* 뽑을 게 모자라면(카탈로그가 얕은 학년대) **되돌린다.**
     빈 하루를 만드느니 바꾸지 않는 편이 낫다 — 리롤 기록도 지워 다시 쓸 수 있게 한다. */
  if (!codes.length) {
    const now0 = nowIso();
    for (const c of oldCodes) {
      await db.prepare(
        "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
      ).bind(child.id, c, ymd, now0).run();
    }
    await db.prepare("DELETE FROM mission_reroll WHERE child_id = ? AND ymd = ?").bind(child.id, ymd).run();
    return apiErr("VALIDATION", null, "바꿀 만한 다른 미션이 없어요.");
  }

  const now = nowIso();
  for (const c of codes) {
    await db.prepare(
      "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
    ).bind(child.id, c, ymd, now).run();
  }
  const fresh = await todayRows(db, child.id, ymd);
  return apiList(fresh.map(shape), {
    ymd, rerolled: 1, stars: await coinBalance(db, child.id),
    done: fresh.filter((r) => r.status === "done").length,
    waiting: fresh.filter((r) => r.status === "waiting").length,
  });
}

// GET /api/v1/children/{id}/missions/reroll — 오늘 쓸 수 있나(버튼 상태용)
async function rerollState(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const r = await db.prepare("SELECT 1 AS x FROM mission_reroll WHERE child_id = ? AND ymd = ?")
    .bind(child.id, ymdKst()).first();
  return apiOk({ can_reroll: r ? 0 : 1 });
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
  const ymd = ymdKst(), now = nowIso();
  const norm = (v) => (Array.isArray(v) ? [...new Set(v.map(String).filter(Boolean))].slice(0, DAY_PICK) : []);

  /* ── 2026-08-12: «하나만» 바꾸는 길을 연다 ──────────────────────────
     여태 이 API 는 `codes` 로 **오늘 것을 통째로 갈아끼우는** 방식뿐이었다.
     그래서 부모가 미션 하나를 빼거나 더하려 해도 155개 목록을 다시 열어 전부 다시 골라야 했다
     (대표님: 「부모미션을 주는 것도 매우 어렵고」). add/drop 이면 홈에서 한 번에 끝난다.
     ⚠ 셋을 섞어 보내지 마라 — codes 가 오면 그게 정본이고 add/drop 은 무시한다. */
  const codes = norm(b && b.codes);
  const add = norm(b && b.add);
  const drop = norm(b && b.drop);
  const swap = norm(b && b.swap);
  if (!codes.length && !add.length && !drop.length && !swap.length) {
    return apiErr("VALIDATION", { fields: { codes: "미션을 골라 주세요." } });
  }

  /* ── 🔁 이것만 바꾸기 ────────────────────────────────────────────────
     부모가 미션 하나를 마음에 안 들어 할 때 **한 번 눌러 끝나야 한다.**
     여태는 155개 카탈로그를 열어 처음부터 다시 골라야 했다(대표님: 「부모미션 주는 것도 매우 어렵고」).
     비슷한 크기(별)로 갈아 끼운다 — 별이 바뀌면 그날 예산이 어긋난다.
     ⚠ **아직 손대지 않은 것(open)만** 바꾼다. 아이가 이미 한 것을 바꾸면 도장이 사라진다. */
  if (swap.length) {
    const { results: mine } = await db.prepare(
      `SELECT a.mission_code, m.stars, m.verify FROM mission_assign a JOIN missions m ON m.code = a.mission_code
        WHERE a.child_id = ? AND a.ymd = ? AND a.status = 'open'
          AND a.mission_code IN (${swap.map(() => "?").join(",")})`
    ).bind(child.id, ymd, ...swap).all();
    if (!(mine || []).length) return apiErr("VALIDATION", null, "이미 한 미션은 바꿀 수 없어요.");

    const band = bandOf(child.grade), season = seasonOf();
    let changed = 0;
    for (const row of mine) {
      // 오늘 이미 붙어 있는 것은 후보에서 뺀다 — 같은 미션이 두 번 나오면 바뀐 것처럼 안 보인다
      const { results: used } = await db.prepare(
        "SELECT mission_code FROM mission_assign WHERE child_id = ? AND ymd = ?").bind(child.id, ymd).all();
      const skip = (used || []).map((u) => u.mission_code);
      /* 같은 크기를 먼저, 없으면 ±1 까지 넓힌다.
         ⚠ 딱 맞는 별만 찾으면 «후보가 없어 조용히 아무 일도 안 하는» 일이 난다
           (2026-08-12 실측: mid 평일 사진 아닌 ★3 이 한 개뿐이라 바꾸기가 먹통이었다).
         ⚠ 사진 미션은 사진으로, 아닌 것은 아닌 것으로 바꾼다 — 하나뿐인 사진이 사라지면 안 된다. */
      const sameKind = row.verify === "review" ? "= 'review'" : "!= 'review'";
      const { results: alt } = await db.prepare(
        `SELECT code FROM missions
          WHERE band = ? AND season = ? AND active = 1 AND verify ${sameKind}
            AND ABS(stars - ?) <= 1
            AND code NOT IN (${skip.map(() => "?").join(",") || "''"})
          ORDER BY ABS(stars - ?), (id * 13 + ?) % 89 LIMIT 1`
      ).bind(band, season, row.stars, ...skip, row.stars, parseInt(ymd, 10) % 89).all();
      if (!(alt || []).length) continue;   // 바꿀 게 없으면 그냥 둔다 — 빼 버리면 미션이 준다
      await db.prepare("DELETE FROM mission_assign WHERE child_id = ? AND ymd = ? AND mission_code = ? AND status = 'open'")
        .bind(child.id, ymd, row.mission_code).run();
      await db.prepare(
        "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
      ).bind(child.id, alt[0].code, ymd, now).run();
      changed++;
    }
    /* 하나도 못 바꿨으면 **그렇다고 말한다.** 조용히 성공을 돌려주면 부모는 버튼이 고장 난 줄 안다. */
    if (!changed) {
      return apiErr("VALIDATION", { items: (await todayRows(db, child.id, ymd)).map(shape) },
        "바꿀 만한 미션이 더 없어요. 「고르기」에서 직접 골라 주세요.");
    }
    return apiOk({ changed, items: (await todayRows(db, child.id, ymd)).map(shape) });
  }

  if (!codes.length) {
    /* ── 하나만 빼기 / 더하기 ──
       ⚠ **아직 손대지 않은 것(open)만** 뺀다. 아이가 이미 한 것을 부모가 빼면 도장이 사라진다. */
    if (drop.length) {
      await db.prepare(
        `DELETE FROM mission_assign WHERE child_id = ? AND ymd = ? AND status = 'open'
           AND mission_code IN (${drop.map(() => "?").join(",")})`
      ).bind(child.id, ymd, ...drop).run();
    }
    if (add.length) {
      const { results: ok } = await db.prepare(
        `SELECT code FROM missions WHERE active = 1 AND code IN (${add.map(() => "?").join(",")})`
      ).bind(...add).all();
      const cnt = await db.prepare(
        "SELECT COUNT(*) n FROM mission_assign WHERE child_id = ? AND ymd = ?").bind(child.id, ymd).first();
      let room = Math.max(0, ECON.maxPerDay - ((cnt && cnt.n) || 0));
      if (!room && (ok || []).length) {
        return apiErr("LIMIT_EXCEEDED", null, `하루에 ${ECON.maxPerDay}개까지만 줄 수 있어요.`);
      }
      for (const r of (ok || [])) {
        if (room-- <= 0) break;
        await db.prepare(
          "INSERT OR IGNORE INTO mission_assign (child_id, mission_code, ymd, status, created_at) VALUES (?, ?, ?, 'open', ?)"
        ).bind(child.id, r.code, ymd, now).run();
      }
    }
    return apiOk({ items: (await todayRows(db, child.id, ymd)).map(shape) });
  }

  const { results: picked } = await db.prepare(
    `SELECT code, verify FROM missions WHERE active = 1 AND code IN (${codes.map(() => "?").join(",")})`
  ).bind(...codes).all();
  if (!picked.length) return apiErr("VALIDATION", { fields: { codes: "없는 미션이에요." } });
  /* 규칙 ② — 전부 사진이면 아이가 부담스럽다. 사진 세 장은 미션이 아니라 숙제가 된다.
     (2026-08-12: 이제 즉시형은 누르면 바로 별이 나오므로, 즉시형이 하나라도 있어야
      «오늘 뭔가 해냈다»가 그 자리에서 생긴다 — 이 규칙의 이유가 하나 더 늘었다.) */
  if (picked.length > 1 && picked.every((p) => p.verify === "review")) {
    return apiErr("VALIDATION", { fields: { codes: "사진 없이 눌러서 보고하는 것도 하나 넣어 주세요." } });
  }

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

  const now = nowIso();

  /* ── ✅ 즉시 통과 (2026-08-12) ────────────────────────────────────
     `instant` 미션은 **누른 그 자리에서 별이 나온다.**
     2026-08-02 에 의뢰를 전부 부모 확인형으로 바꿨는데, 그 결과 「자동으로 되는 것이 하나도
     없는」 상태가 됐다 — 155개 중 70개가 즉시형인데도 부모가 안 눌러주면 별이 안 나왔다.
     아이는 「했는데 왜 안 줘」를 묻고, 부모는 매일 확인 버튼을 누르는 숙제를 받았다.

     🔑 그럼 «무조건 통과»는 뭐가 막나 — **별 라인**이 막는다.
        아무리 눌러도 하루 총량이 부모가 정한 예산을 못 넘는다(grantStars 가 깎아서 준다).
        미션을 하나하나 검사하는 것보다 이쪽이 부모에게도 아이에게도 싸다.
     ⚠ 되돌리기는 그대로 남는다 — 부모가 `revert` 하면 준 별까지 회수된다(spendStars).
     ⚠ 사진(review)·하루끝(endday)은 **그대로 부모 확인**이다. 즉시형만 바뀐다. */
  if (a.verify === "instant" && ECON.autoPassInstant) {
    const g = await grantStars(db, a.child_id, a.mstars, "mission:" + a.mission_code);
    await db.prepare("UPDATE mission_assign SET status='done', claimed_at=?, decided_at=?, stars=? WHERE id=?")
      .bind(now, now, g.granted, id).run();
    /* ⚠ `stars` 에 **실제로 들어간 양**을 적는다(a.mstars 가 아니라 g.granted).
       상한에 걸려 깎였는데 원래 값을 적으면, 되돌릴 때 안 받은 별까지 회수된다. */
    return apiOk({ status: "done", got: g.granted, capped: g.capped,
                   coin: await coinState(db, a.child_id), stars: g.stars });
  }

  /* 확인형은 여기서 별을 주지 않는다. approve() 나 autoApprove 크론이 준다.
     여기서 주고 나중에 또 주면 두 배가 나간다 — 별 원장은 되돌리기 어렵다. */
  const auto = autoAtIso();
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
  await grantStars(db, auth.childId, 1, "meal-rate");
  return apiOk({ got: 1, total_stars: await coinBalance(db, auth.childId), ymd });
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

  await grantStars(db, auth.childId, 1, "play-log");
  return apiOk({ got: 1, total_stars: await coinBalance(db, auth.childId), ymd });
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

  await grantStars(db, auth.childId, 1, "subject-log");
  return apiOk({ got: 1, total_stars: await coinBalance(db, auth.childId), ymd });
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
  /* ⚠ **먼저 주고, 실제로 들어간 양을 적는다.** 상한에 걸려 깎였는데 원래 값을 적어 두면
     되돌릴 때 안 받은 별까지 회수된다(2026-08-12 즉시통과 붙이며 같이 고침). */
  const g = await grantStars(db, a.child_id, a.mstars, "mission:" + a.mission_code);
  await db.prepare("UPDATE mission_assign SET status='done', decided_at=?, stars=? WHERE id=?")
    .bind(nowIso(), g.granted, id).run();
  return apiOk({ status: "done", got: g.granted, capped: g.capped, stars: g.stars });
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
  if (a.stars) await spendStars(db, a.child_id, a.stars, "revert:" + a.mission_code);
  /* 되돌리면 **사진도 같이 지운다** (2026-08-02 폰 실측으로 잡음).
     decided_at 을 NULL 로 미는 순간 아래 7일 정리 크론의 조건(decided_at IS NOT NULL)에서 빠져
     그 사진은 **아무도 안 지우는 상태로 R2에 영원히 남았다.** 아이 사진이라 더 그러면 안 된다.
     어차피 «다시 해볼까?» 는 그 사진을 무효로 하는 행동이라, 남길 이유도 없다. */
  if (a.photo_key) { try { await env.RECORDS.delete(a.photo_key); } catch (_) {} }
  await db.prepare("UPDATE mission_assign SET status='open', claimed_at=NULL, decided_at=NULL, auto_at=NULL, stars=0, photo_key=NULL WHERE id=?")
    .bind(id).run();
  return apiOk({ status: "open", stars: await coinBalance(db, a.child_id) });
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
    const g = await grantStars(db, d.child_id, s, "mission:" + d.mission_code);
    // 실제로 들어간 양을 적는다 — 상한에 걸린 날 되돌리면 안 받은 별이 회수된다
    await db.prepare("UPDATE mission_assign SET status='done', decided_at=?, stars=? WHERE id=?").bind(now, g.granted, d.id).run();
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

/* ══ 세트 완주 보너스 (2026-08-08, 기획서 v2 §01) ══════════════════════
   아침·방과후 «세트»를 다 깨면 얹어 준다. 학교 세트는 school_missions.js 가 따로 맡는다
   (그건 국내 전용이라 해외판에서 통째로 빠져야 하기 때문이다).

   ⚠ 「한 번만」의 근거는 **원장의 reason 문자열**이다 — `set:<slot>:<ymd>`.
     상태 칼럼을 새로 만들지 않는다. 칼럼과 원장이 어긋나면 되돌릴 근거가 사라진다.
   ⚠ 화면이 «다 했다»고 말해도 믿지 않는다. **여기서 다시 센다.**
   ⚠ 오늘 배정된 미션이 0개면 «완주»가 아니다 — 아무것도 안 하고 보너스를 먹는 길을 막는다. */
const SET_SLOTS = { morning: ["morning"], after: ["after", "evening", "any"] };

async function setState(db, childId, ymd) {
  const { results } = await db.prepare(
    `SELECT m.slot, a.status FROM mission_assign a
       JOIN missions m ON m.code = a.mission_code
      WHERE a.child_id = ? AND a.ymd = ?`
  ).bind(childId, ymd).all();
  const out = {};
  for (const key of Object.keys(SET_SLOTS)) {
    const want = SET_SLOTS[key];
    const rows = (results || []).filter((r) => want.indexOf(r.slot || "any") >= 0);
    out[key] = { done: rows.filter((r) => r.status === "done").length, all: rows.length };
  }
  return out;
}

async function missionSets(request, db, env, childId) {
  const g = await gate(request, db, env, childId);
  if (g.err) return g.err;
  const ymd = ymdKst();
  const st = await setState(db, g.child.id, ymd);
  for (const key of Object.keys(st)) {
    const had = await db.prepare("SELECT 1 x FROM star_ledger WHERE child_id = ? AND reason = ?")
      .bind(g.child.id, "set:" + key + ":" + ymd).first();
    st[key].taken = !!had;
    st[key].bonus = BONUS.setComplete;
  }
  return apiOk({ ymd, sets: st });
}

async function claimSetBonus(request, db, env, childId) {
  const g = await gate(request, db, env, childId);
  if (g.err) return g.err;
  if (g.auth.role !== "child") return apiErr("FORBIDDEN", null, "아이만 받을 수 있어요.");
  const b = await readJson(request);
  const key = String(b?.slot || "");
  if (!SET_SLOTS[key]) return apiErr("VALIDATION", null, "그런 세트는 없어요.");

  const ymd = ymdKst();
  const st = (await setState(db, g.child.id, ymd))[key];
  if (!st.all) return apiErr("VALIDATION", { done: 0, all: 0 }, "오늘은 그 세트가 없어요.");
  if (st.done < st.all) {
    return apiErr("VALIDATION", { done: st.done, all: st.all },
      (st.all - st.done) + "개 더 하면 받을 수 있어요.");
  }

  const reason = "set:" + key + ":" + ymd;
  const had = await db.prepare("SELECT 1 x FROM star_ledger WHERE child_id = ? AND reason = ?")
    .bind(g.child.id, reason).first();
  if (had) return apiOk({ granted: 0, already: true, coin: await coinState(db, g.child.id) });

  const got = await grantStars(db, g.child.id, BONUS.setComplete, reason);
  return apiOk({ granted: got.granted, capped: got.capped, slot: key,
                 coin: await coinState(db, g.child.id) });
}

export async function handleMissionApi(request, db, env, url) {
  const p = url.pathname, m = request.method;

  if (p === "/api/v1/missions" && m === "GET") return listCatalog(request, db, env, url);
  if (p === "/api/v1/missions" && m === "POST") return createCustom(request, db, env);
  const mine = p.match(/^\/api\/v1\/missions\/(U-[0-9a-f]{8})$/);
  if (mine && m === "DELETE") return deleteCustom(request, db, env, mine[1]);

  // ⚙️ 경제 설정 — 앱이 상수를 안 들고 여기서 받아 간다(2026-08-12)
  let x = p.match(/^\/api\/v1\/children\/(\d+)\/econ\/?$/);
  if (x && m === "GET") return econ(request, db, env, x[1]);
  x = p.match(/^\/api\/v1\/children\/(\d+)\/star-line\/?$/);
  if (x && m === "PUT") return setStarLine(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/report\/?$/);
  if (x && m === "GET") return report(request, db, env, x[1]);

  x = p.match(/^\/api\/v1\/children\/(\d+)\/marks\/?$/);
  if (x && m === "GET") return marks(request, db, env, x[1]);

  // 세트 완주 보너스 — ⚠ `/missions/?$` 보다 **먼저**(더 긴 경로가 앞)
  x = p.match(/^\/api\/v1\/children\/(\d+)\/mission-sets\/?$/);
  if (x && m === "GET") return missionSets(request, db, env, x[1]);
  x = p.match(/^\/api\/v1\/children\/(\d+)\/mission-sets\/bonus$/);
  if (x && m === "POST") return claimSetBonus(request, db, env, x[1]);

  // 지난 이레 — ⚠ 아래 `/missions/?$` 보다 **먼저**(더 긴 경로가 앞)
  x = p.match(/^\/api\/v1\/children\/(\d+)\/missions\/week$/);
  if (x && m === "GET") return missionWeek(request, db, env, x[1], url);

  // 🎲 리롤 — ⚠ 아래 `/missions/?$` 보다 **먼저** 잡아야 한다(더 긴 경로가 앞)
  x = p.match(/^\/api\/v1\/children\/(\d+)\/missions\/reroll$/);
  if (x) {
    if (m === "POST") return reroll(request, db, env, x[1]);
    if (m === "GET") return rerollState(request, db, env, x[1]);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }

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
