// ══════════ 🏫 학교 미션 제공자 (2026-08-08, 기획서 v2 §09) ══════════
//
// **이 파일이 「자르는 선」이다.**
//
//   미션 시스템 ──(이 파일)──> 학교정보(급식·친구·시간표)
//
// 미션 시스템은 `meal_ratings`·`play_days`·`subject_log` 를 **직접 조회하지 않는다.**
// 오직 여기를 통해서만 본다. 그래서 **해외판은 이 파일을 안 끼우면** 되고,
// 그러면 아이 홈이 4칸에서 3칸이 되고 나머지는 그대로 돈다.
//
// ⚠ 새 학교 데이터가 생겨도 **여기 말고 다른 곳에서 읽지 마라.** 한 번 새면 다시는 못 뽑아낸다.
// ⚠ 「오늘 했나」의 판단 기준은 **그 표에 오늘 줄이 있는가** 하나뿐이다.
//   별도 상태 칼럼을 만들지 않는다 — 두 곳에 상태가 있으면 반드시 어긋난다.
//
// 미션 자체(별을 주는 POST)는 api_mission.js 의 mealRate/playLog/subjectLog 가 한다.
// 여기는 **읽기와 세트 보너스**만 맡는다.

import { apiOk, apiErr } from "./api_core.js";
import { resolveAuth } from "./auth_core.js";
import { grantStars, coinState, ymdKst, BONUS } from "./star_core.js";

/* api_quiz.js·api_reward.js 와 **같은 방식**으로 쿠키를 읽는다.
   ⚠ 파일마다 다르게 읽으면 아이 토큰이 한쪽에서만 먹혀 «되는 화면과 안 되는 화면»이 생긴다. */
function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

/* 화면에 그대로 쓰이는 정의. 순서도 여기가 정본이다 —
   앱이 제목을 또 적어 두면 나라를 늘릴 때 두 곳을 고쳐야 한다. */
export const SCHOOL_MISSIONS = [
  { key: "meal",    icon: "🍚", name: "오늘 급식",   note: "별점만 누르면 끝",  stars: 1, go: "childmealrate" },
  { key: "friend",  icon: "🙌", name: "오늘 누구랑", note: "친구 이름 고르기",  stars: 1, go: "childfriend" },
  { key: "subject", icon: "✏️", name: "재밌던 수업", note: "시간표에서 고르기", stars: 1, go: "childsubject" },
];

/* 오늘 무엇을 했나 — 표에 오늘 줄이 있으면 «했다» 다. */
export async function schoolMissionState(db, childId, ymd) {
  const day = ymd || ymdKst();
  const [meal, friend, subject] = await Promise.all([
    db.prepare("SELECT 1 x FROM meal_ratings WHERE child_id = ? AND ymd = ?").bind(childId, day).first(),
    db.prepare("SELECT 1 x FROM play_days   WHERE child_id = ? AND ymd = ?").bind(childId, day).first(),
    db.prepare("SELECT 1 x FROM subject_log WHERE child_id = ? AND ymd = ?").bind(childId, day).first(),
  ]);
  const doneBy = { meal: !!meal, friend: !!friend, subject: !!subject };
  const items = SCHOOL_MISSIONS.map((m) => ({ ...m, done: doneBy[m.key] }));
  const done = items.filter((m) => m.done).length;
  return { ymd: day, items, done, all: items.length, bonus: BONUS.setComplete };
}

/* 세트 완주 보너스 — 셋 다 하면 한 번만 얹어 준다.
   ⚠ 「한 번만」의 근거는 **원장의 reason 문자열**이다. 상태 칼럼을 새로 만들지 않는다.
     칼럼과 원장이 어긋나면 되돌릴 근거가 사라진다 — 원장이 정본이다. */
export async function claimSchoolSetBonus(db, childId, ymd) {
  const day = ymd || ymdKst();
  const st = await schoolMissionState(db, childId, day);
  if (st.done < st.all) return { granted: 0, cleared: false };

  const reason = "school-set:" + day;
  const had = await db.prepare(
    "SELECT 1 x FROM star_ledger WHERE child_id = ? AND reason = ?"
  ).bind(childId, reason).first();
  if (had) return { granted: 0, cleared: true, already: true };

  const g = await grantStars(db, childId, BONUS.setComplete, reason);
  return { granted: g.granted, cleared: true, capped: g.capped };
}

async function gate(request, db, env, childId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  const child = await db.prepare(
    "SELECT id, school_id, owner_token FROM children WHERE id = ? AND owner_token = ?"
  ).bind(childId, auth.ownerToken).first();
  if (!child) return { err: apiErr("NOT_FOUND") };
  if (auth.role === "child" && String(auth.childId) !== String(child.id)) return { err: apiErr("FORBIDDEN") };
  return { child, auth };
}

/* GET  /api/v1/children/{id}/school-missions — 오늘 상태(읽기)
   POST /api/v1/children/{id}/school-missions/bonus — 세트 완주 보너스 받기

   ⚠ 부모 토큰으로도 **읽기는** 된다 — 부모가 아이 화면을 미리 볼 수 있어야 한다.
     별을 주는 것(POST)은 아이만. 그건 api_mission.js 쪽 규칙과 같다. */
export async function handleSchoolMissionApi(request, db, env, url) {
  const p = url.pathname, m = request.method;
  let x;

  x = p.match(/^\/api\/v1\/children\/(\d+)\/school-missions\/bonus$/);
  if (x && m === "POST") {
    const { child, auth, err } = await gate(request, db, env, x[1]);
    if (err) return err;
    if (auth.role !== "child") return apiErr("FORBIDDEN", null, "아이만 받을 수 있어요.");
    const r = await claimSchoolSetBonus(db, child.id);
    return apiOk({ ...r, coin: await coinState(db, child.id) });
  }

  x = p.match(/^\/api\/v1\/children\/(\d+)\/school-missions\/?$/);
  if (x && m === "GET") {
    const { child, err } = await gate(request, db, env, x[1]);
    if (err) return err;
    /* 학교가 없으면 이 갈래 자체가 없다 — 화면은 카드를 안 그린다.
       해외판에서 이 파일을 빼면 라우트가 아예 없어져 404 가 되고, 앱은 같은 길로 처리한다. */
    if (!child.school_id) return apiOk({ available: false, items: [], done: 0, all: 0 });
    const st = await schoolMissionState(db, child.id);
    const claimed = await db.prepare(
      "SELECT 1 x FROM star_ledger WHERE child_id = ? AND reason = ?"
    ).bind(child.id, "school-set:" + st.ymd).first();
    return apiOk({ available: true, ...st, bonus_taken: !!claimed });
  }

  return null;
}
