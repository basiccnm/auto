// ================= 인증 API (블록1) =================
// 계약: docs/API계약-v1.md §3
// 경로: /api/v1/auth/* · /api/v1/me
//
// 기존 HTML 로그인(/login, /auth/kakao)은 **그대로 살아 있다**. 병존이다.
// 다만 소셜 콜백이 accounts를 함께 만들도록 index.js에서 한 줄 연결한다(무손실 승계).

import { apiOk, apiErr, validate, readJson } from "./api_core.js";
import {
  hashPassword, verifyPassword, signToken, verifyToken, authSecret, TOKEN_TTL,
  findAccountById, findAccountByAuth, createAccount, addAuthMethod, touchLogin,
  revokeToken, isRevoked, resolveAuth, verifyReauth,
} from "./auth_core.js";
// (탈퇴 즉시 파기는 2026-07-31에 3개월 유예로 바뀌었다 — withdrawAccount는 이제 크론(index.js)이 부른다)

/* ── 부모 기기 (2026-08-01) ──────────────────────────────────
   엄마·아빠가 각자 폰에서 같은 계정을 본다 → **2대까지** 허용한다.
   3번째가 로그인하면 **가장 오래 안 쓴 기기**가 밀려난다(그 폰 토큰은 즉시 죽는다).
   자녀(1대)와 규칙은 같지만 표를 따로 둔다 — 자녀는 children 칸에 박혀 있어 2대를 못 담는다. */
const MAX_PARENT_DEVICES = 2;

async function newDevice(db, accountId, label) {
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  await db.prepare(
    "INSERT INTO account_devices (id, account_id, label, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?)"
  ).bind(id, accountId, String(label || "").slice(0, 60) || null, now, now).run();

  // 2대를 넘으면 오래된 것부터 지운다. 지워진 기기의 토큰은 다음 요청에서 막힌다.
  const { results } = await db.prepare(
    "SELECT id FROM account_devices WHERE account_id = ? ORDER BY last_seen_at DESC"
  ).bind(accountId).all();
  const over = (results || []).slice(MAX_PARENT_DEVICES);
  for (const d of over) {
    await db.prepare("DELETE FROM account_devices WHERE id = ?").bind(d.id).run();
  }
  return id;
}

// ── 토큰 한 쌍 발급 ─────────────────────────────────────────
// dev 를 주면 그 기기를 이어 쓴다(refresh). 안 주면 새 기기를 만든다(로그인·가입).
async function issueTokens(env, account, db, { device = null, label = "" } = {}) {
  const secret = authSecret(env);
  let dev = device;
  if (db && !dev) dev = await newDevice(db, account.id, label);
  else if (db && dev) {
    await db.prepare("UPDATE account_devices SET last_seen_at = ? WHERE id = ?")
      .bind(new Date().toISOString(), dev).run();
  }
  const [access, refresh] = await Promise.all([
    signToken({ sub: account.id, typ: "access", tok: account.owner_token, dev }, secret, TOKEN_TTL.access),
    signToken({ sub: account.id, typ: "refresh", dev }, secret, TOKEN_TTL.refresh),
  ]);
  return { access_token: access, refresh_token: refresh, expires_in: TOKEN_TTL.access, token_type: "Bearer" };
}

function publicAccount(a) {
  return {
    id: a.id,
    display_name: a.display_name,
    email: a.email,
    phone: a.phone,
    phone_verified: !!a.phone_verified,
    created_at: a.created_at,
  };
}

// ── 입력 규칙 ───────────────────────────────────────────────
const RE_LOGIN_ID = /^[a-z0-9_]{4,20}$/i;
const RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RE_YMD = /^\d{8}$/;
const RE_PHONE = /^01[0-9]{8,9}$/;

// ── POST /api/v1/auth/register — ID 회원가입 (계약 §3.3) ────
async function register(request, db, env) {
  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const loginId = String(b.login_id || "").trim();
  const password = String(b.password || "");
  const name = String(b.name || "").trim();
  const birthYmd = String(b.birth_ymd || "").replace(/-/g, "").trim();
  const email = String(b.email || "").trim().toLowerCase();
  const phone = String(b.phone || "").replace(/-/g, "").trim();

  // 약관·방침 동의는 **법적 필수**라 서버에서도 검사한다. 프론트 체크만 믿으면 직접 POST로 우회된다.
  const fields = validate([
    ["login_id", RE_LOGIN_ID.test(loginId), "영문·숫자 4~20자로 입력해 주세요."],
    ["password", password.length >= 8, "8자 이상으로 입력해 주세요."],
    ["name", name.length >= 1 && name.length <= 30, name.length > 30 ? "이름은 30자까지 넣을 수 있어요." : "이름을 입력해 주세요."],
    ["birth_ymd", RE_YMD.test(birthYmd), "생년월일을 YYYYMMDD로 입력해 주세요."],
    ["email", RE_EMAIL.test(email), "이메일 형식을 확인해 주세요."],
    // 2026-08-12 대표님: 휴대폰 필수 — 프론트만 막으면 직접 POST 로 우회된다
    ["phone", !!phone && RE_PHONE.test(phone), phone ? "휴대폰 번호를 확인해 주세요." : "휴대폰 번호를 입력해 주세요."],
    ["agree_terms", b.agree_terms === true, "이용약관에 동의해 주세요."],
    ["agree_privacy", b.agree_privacy === true, "개인정보처리방침에 동의해 주세요."],
  ]);
  if (fields) return apiErr("VALIDATION", { fields });

  // 중복 검사 — 아이디는 auth_methods, 이메일은 accounts.
  const dupId = await db.prepare("SELECT 1 AS x FROM auth_methods WHERE kind='id_password' AND identifier=?").bind(loginId).first();
  if (dupId) return apiErr("DUPLICATE", { fields: { login_id: "이미 사용 중인 아이디예요." } });
  const dupEmail = await db.prepare("SELECT 1 AS x FROM accounts WHERE email=?").bind(email).first();
  if (dupEmail) return apiErr("DUPLICATE", { fields: { email: "이미 가입된 이메일이에요." } });

  // dry_run — **만들지 않고 검사만** 한다(2026-07-25).
  // 가입 화면이 "이 아이디 쓸 수 있나"를 미리 물어보는 용도(계약 §3.3 중복확인).
  // 목업이 클릭 검수 중에 진짜 계정을 만들어버리면 안 되기 때문에도 필요하다.
  if (b.dry_run === true) return apiOk({ available: true });

  // 이 기기에 쓰던 owner_token이 있으면 **그대로 승계**한다 — 익명으로 등록한 자녀·기록이 딸려온다.
  // 새 토큰을 만들면 그 데이터가 끊긴다(정본 §4 무손실 승계).
  const cookieToken = readCookie(request, "owner_token");

  const acc = await createAccount(db, {
    ownerToken: cookieToken || null,
    displayName: name,
    email,
    phone: phone || null,
    birthYmd,
  });
  await addAuthMethod(db, acc.id, "id_password", loginId, await hashPassword(password), 1);

  /* 광고성 정보 수신(선택 동의, 2026-07-31) — 채널별(메일·문자·전화)로 받고,
     동의 일시를 같이 적는다(정보통신망법 §50 — 동의 기록을 남겨야 한다). 미동의도 기록. */
  const mk = b.marketing && typeof b.marketing === "object" ? b.marketing : {};
  await db.prepare("UPDATE accounts SET marketing=? WHERE id=?").bind(
    JSON.stringify({ email: mk.email === true, sms: mk.sms === true, call: mk.call === true, updated_at: new Date().toISOString() }),
    acc.id
  ).run();

  const account = await findAccountById(db, acc.id);
  const tokens = await issueTokens(env, account, db, { label: b.device_label });
  return apiOk({ account: publicAccount(account), ...tokens }, 201);
}

// ── 로그인 시도 제한 (2026-07-25) ───────────────────────────
// 비밀번호를 무제한 대입할 수 있었다 → **10회 실패하면 10분 잠금**(사장님 지시).
// 세는 단위는 아이디다. 없는 아이디도 똑같이 센다 — 안 그러면 "이 아이디는 존재한다"가 새어나간다.
// 30분 안에 새 실패가 없으면 카운트는 저절로 풀린다(오타 몇 번으로 계정이 굳지 않게).
const LOGIN_MAX_FAILS = 10;
const LOGIN_LOCK_SEC = 600;      // 10분
const LOGIN_WINDOW_SEC = 1800;   // 30분

async function loginLockCheck(db, identifier) {
  const now = Math.floor(Date.now() / 1000);
  const r = await db.prepare("SELECT fails, first_fail, locked_until FROM login_attempts WHERE identifier=?").bind(identifier).first();
  if (!r) return { locked: false, fails: 0, now };
  if (r.locked_until && r.locked_until > now) return { locked: true, retryAfter: r.locked_until - now, now };
  // 잠금이 풀렸거나, 마지막 실패가 오래됐으면 카운트를 0부터 다시 센다
  const stale = !r.first_fail || now - r.first_fail > LOGIN_WINDOW_SEC;
  return { locked: false, fails: stale || r.locked_until ? 0 : r.fails, now };
}

async function loginFail(db, identifier, fails, now) {
  const next = fails + 1;
  const lockUntil = next >= LOGIN_MAX_FAILS ? now + LOGIN_LOCK_SEC : null;
  await db.prepare(
    `INSERT INTO login_attempts (identifier, fails, first_fail, locked_until) VALUES (?, ?, ?, ?)
     ON CONFLICT(identifier) DO UPDATE SET fails=excluded.fails, first_fail=excluded.first_fail, locked_until=excluded.locked_until`
  ).bind(identifier, next, now, lockUntil).run();
  return { locked: !!lockUntil, left: Math.max(0, LOGIN_MAX_FAILS - next) };
}

// 성공하면 기록을 지운다 — 다음부터 다시 10회
const loginOk = (db, identifier) =>
  db.prepare("DELETE FROM login_attempts WHERE identifier=?").bind(identifier).run();

// ── POST /api/v1/auth/login ─────────────────────────────────
async function login(request, db, env) {
  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });
  const loginId = String(b.login_id || "").trim();
  const password = String(b.password || "");
  if (!loginId || !password) return apiErr("VALIDATION", { fields: { login_id: "아이디와 비밀번호를 입력해 주세요." } });

  // 잠긴 아이디는 **비밀번호를 맞혀도** 들여보내지 않는다
  const gate = await loginLockCheck(db, loginId);
  if (gate.locked) {
    const min = Math.ceil(gate.retryAfter / 60);
    return apiErr("LIMIT_EXCEEDED", { retry_after: gate.retryAfter },
      `로그인을 여러 번 실패했어요. ${min}분 뒤에 다시 시도해 주세요.`);
  }

  const m = await db.prepare("SELECT * FROM auth_methods WHERE kind='id_password' AND identifier=?").bind(loginId).first();
  // 아이디가 없어도 비번 검증을 돌린다 — 응답 시간 차이로 "그 아이디가 있다"를 알아내지 못하게.
  const ok = await verifyPassword(password, m ? m.secret : "pbkdf2$100000$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
  if (!m || !ok) {
    const f = await loginFail(db, loginId, gate.fails, gate.now);
    return apiErr("AUTH_INVALID", { attempts_left: f.left }, f.locked
      ? `로그인을 ${LOGIN_MAX_FAILS}번 실패해 ${LOGIN_LOCK_SEC / 60}분간 잠갔어요.`
      : "아이디 또는 비밀번호가 올바르지 않아요.");
  }

  const account = await findAccountById(db, m.account_id);
  if (!account) {
    // 비번까지 맞았는데 계정이 안 나온다 = status 필터에 걸린 것. 탈퇴 유예 중이면 사실대로 말한다.
    const raw = await db.prepare("SELECT status FROM accounts WHERE id=?").bind(m.account_id).first();
    if (raw?.status === "withdrawn_pending") {
      return apiErr("AUTH_INVALID", null, "탈퇴한 계정이에요. 탈퇴 후 3개월간 보관된 뒤 완전히 삭제돼요. 복구를 원하면 문의해 주세요.");
    }
    await loginFail(db, loginId, gate.fails, gate.now);
    return apiErr("AUTH_INVALID", null, "아이디 또는 비밀번호가 올바르지 않아요.");
  }

  await loginOk(db, loginId);
  await touchLogin(db, account.id, "id_password", loginId);
  const tokens = await issueTokens(env, account, db, { label: b.device_label });
  return apiOk({ account: publicAccount(account), ...tokens });
}

// ── POST /api/v1/auth/refresh ───────────────────────────────
async function refresh(request, db, env) {
  const b = await readJson(request);
  const rt = b && b.refresh_token;
  if (!rt) return apiErr("VALIDATION", { fields: { refresh_token: "refresh_token이 필요해요." } });

  const v = await verifyToken(rt, authSecret(env));
  if (!v.ok) return apiErr(v.reason === "expired" ? "AUTH_EXPIRED" : "AUTH_INVALID");
  if (v.payload.typ !== "refresh") return apiErr("AUTH_INVALID");
  if (await isRevoked(db, v.payload.jti)) return apiErr("AUTH_INVALID");

  const account = await findAccountById(db, v.payload.sub);
  if (!account) return apiErr("AUTH_INVALID");

  // 회전(rotation) — 쓴 refresh는 즉시 폐기하고 새로 준다.
  // 탈취된 토큰이 무한정 재사용되는 걸 막는다.
  await revokeToken(db, v.payload.jti, account.id, v.payload.exp);
  /* 기기는 이어 쓴다 — 갱신할 때마다 새 기기가 되면 2대 자리가 금방 찬다.
     이미 밀려난 기기(표에 없음)면 여기서 끊는다. 그래야 3번째 폰이 갱신으로 되살아나지 않는다. */
  if (v.payload.dev) {
    const d = await db.prepare("SELECT id FROM account_devices WHERE id = ? AND account_id = ?")
      .bind(v.payload.dev, account.id).first();
    if (!d) return apiErr("AUTH_INVALID", null, "다른 기기에서 로그인해서 연결이 끊겼어요. 다시 로그인해 주세요.");
  }
  const tokens = await issueTokens(env, account, db, { device: v.payload.dev || null });
  return apiOk(tokens);
}

// ── POST /api/v1/auth/reauth — 재인증 토큰 (계약 §3.4) ──────
// 수정·삭제 직전에 비밀번호를 다시 받아 5분짜리 토큰을 준다.
// 소셜 전용 계정(비번 없음)은 생체 인증을 앱이 처리하고 여기선 통과시킨다.
async function reauth(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");

  const b = await readJson(request);
  const pw = b && b.password;
  const m = await db.prepare("SELECT * FROM auth_methods WHERE account_id=? AND kind='id_password'").bind(auth.account.id).first();

  /* 2026-07-31 — 비번 계정도 **기기 생체 확인이면 통과**시킨다(«삭제 팝업 5번» 정리).
     소셜 계정은 원래 biometric:true 를 믿어왔다 — 신뢰 수준을 계정 종류와 무관하게 통일한 것.
     (서버는 생체가 진짜 있었는지 알 수 없다 — access 토큰 소지 + 기기 잠금이 실질 방어선이다.
      더 세게 잠그려면 두 계정 유형 모두에서 같이 세게 잠가야 한다.) */
  if (b && b.biometric === true) {
    // 통과 — 앱이 지문·얼굴을 확인했다
  } else if (m) {
    if (!pw) return apiErr("VALIDATION", { fields: { password: "비밀번호를 입력해 주세요." } });
    if (!(await verifyPassword(pw, m.secret))) {
      return apiErr("AUTH_INVALID", null, "비밀번호가 올바르지 않아요.");
    }
  } else {
    // 소셜 전용 계정은 비번이 없다. 앱이 생체로 확인했다는 신호를 보내야 한다.
    return apiErr("VALIDATION", { fields: { biometric: "본인 확인이 필요해요." } });
  }

  const token = await signToken({ sub: auth.account.id, typ: "reauth" }, authSecret(env), TOKEN_TTL.reauth);
  return apiOk({ reauth_token: token, expires_in: TOKEN_TTL.reauth });
}

// ── POST /api/v1/auth/logout ────────────────────────────────
async function logout(request, db, env) {
  const b = await readJson(request);
  const rt = b && b.refresh_token;
  if (rt) {
    const v = await verifyToken(rt, authSecret(env));
    if (v.ok && v.payload.jti) await revokeToken(db, v.payload.jti, v.payload.sub, v.payload.exp);
  }
  return apiOk({ logged_out: true });
}

// ── GET /api/v1/me ──────────────────────────────────────────
async function me(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");

  const { results: methods } = await db
    .prepare("SELECT kind, identifier, verified FROM auth_methods WHERE account_id=?")
    .bind(auth.account.id).all();

  // 자녀 요약 — 이름(identifiers)은 여기 넣지 않는다. 목록에서는 별명만(정본 §3-5).
  const { results: kids } = await db
    .prepare(
      `SELECT c.id, c.nickname, c.grade, c.class_name, c.trial_expires_at, c.child_device, c.child_device_at,
              s.name AS school_name, s.slug AS school_slug
       FROM children c JOIN schools s ON s.id=c.school_id
       WHERE c.owner_token=? ORDER BY c.created_at`
    )
    .bind(auth.account.owner_token).all();

  /* 연결된 기기 목록(2026-08-01) — 엄마·아빠 폰을 내 정보에서 확인하고 끊을 수 있게.
     id 를 그대로 내보낸다: 이건 «내 계정 안에서만» 뜻이 있는 값이고, 끊으려면 어느 것인지 지목해야 한다.
     this_device 로 지금 보고 있는 폰을 표시해 준다 — 안 그러면 자기 폰을 끊어버린다. */
  const { results: devices } = await db
    .prepare("SELECT id, label, created_at, last_seen_at FROM account_devices WHERE account_id = ? ORDER BY last_seen_at DESC")
    .bind(auth.account.id).all();
  const thisDev = auth.deviceId || null;

  /* 유료 여부(2026-08-10) — trial_expires_at 한 칸에 체험·유료 만료일이 **섞여 있어서**
     앱이 유료 이용권도 「1주일 무료체험 쓰는 중」으로 그렸다(최종 검수 실측: 44일 남은 유료가 체험으로).
     돈을 냈다는 근거는 orders 뿐이다(hasActivePass 와 같은 규칙) — 자녀별로 표시만 갈라 준다. */
  const { results: paidRows } = await db
    .prepare("SELECT DISTINCT child_id FROM orders WHERE account_id = ? AND status = 'active' AND expires_at > ?")
    .bind(auth.account.id, new Date().toISOString()).all();
  const paidSet = new Set((paidRows || []).map((r) => r.child_id));

  return apiOk({
    account: publicAccount(auth.account),
    marketing: (() => { try { return JSON.parse(auth.account.marketing || "null"); } catch (e) { return null; } })(),
    auth_methods: methods.map((m) => ({ kind: m.kind, verified: !!m.verified })),
    devices: (devices || []).map((d) => ({
      id: d.id, label: d.label, last_seen_at: d.last_seen_at, this_device: d.id === thisDev,
    })),
    device_limit: MAX_PARENT_DEVICES,
    children: kids.map((k) => ({
      id: k.id, nickname: k.nickname, grade: k.grade, class_name: k.class_name,
      school: { slug: k.school_slug, name: k.school_name },
      pass_expires_at: k.trial_expires_at,
      pass_paid: paidSet.has(k.id),        // true = 결제 이용권 / false = 무료체험 (표시용)
      // 자녀폰 연결 상태(2026-07-31) — 기기 표식은 내보내지 않는다. 붙었나·언제만 알려준다.
      child_device: !!k.child_device, child_device_at: k.child_device_at || null,
    })),
  });
}

// ── DELETE /api/v1/me/devices/{id} — 그 폰 끊기 ─────────────
// 내 계정의 기기만 지운다. 지우는 즉시 그 폰의 토큰이 죽는다(auth_core 가 표를 본다).
async function removeDevice(request, db, env, id) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");
  const row = await db.prepare("SELECT id FROM account_devices WHERE id = ? AND account_id = ?")
    .bind(id, auth.account.id).first();
  if (!row) return apiErr("NOT_FOUND");
  await db.prepare("DELETE FROM account_devices WHERE id = ?").bind(id).run();
  return apiOk({ removed: true, id });
}

/* ── PATCH /api/v1/me — 내 정보 고치기 (2026-07-27) ──────────
   지금은 **이름만** 바꾼다. 가입할 때 한글 입력이 깨져 «ㄱㅣㅁ» 으로 저장된 사람이 있는데
   고칠 길이 아예 없었다(사장님 발견).

   이메일·전화는 여기서 안 받는다 — 그건 본인 확인이 걸린 값이라
   비밀번호 찾기·알림 수신처가 통째로 바뀐다. 별도 흐름으로 다룰 것.
   그래서 재인증(X-Reauth-Token)도 요구하지 않는다. 이름은 되돌릴 수 있는 값이다. */
async function patchMe(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");

  const b = await readJson(request);
  const name = String((b && b.display_name) || "").trim().replace(/\s+/g, " ");
  // 위아래 한도만 본다 — 이름 규칙을 빡빡하게 잡으면 외국 이름·성만 쓰는 이름이 막힌다
  if (name.length < 1 || name.length > 20) {
    return apiErr("VALIDATION", { fields: { display_name: "이름은 1~20자로 적어주세요." } });
  }
  await db.prepare("UPDATE accounts SET display_name = ? WHERE id = ?").bind(name, auth.account.id).run();
  const after = await findAccountById(db, auth.account.id);
  return apiOk({ account: publicAccount(after) });
}

// ── DELETE /api/v1/me — 회원 탈퇴 (계약 §3.2 추가, 회신24) ──
// 되돌릴 수 없는 요청의 끝판이라 **access + reauth 둘 다** 요구한다(계약 §3.4).
// 앱은 생체/비번 재확인 → /auth/reauth → X-Reauth-Token 헤더로 재시도한다.
//
// 2026-07-31 방침 확정: **즉시 파기 → 3개월 유예 후 파기.**
// 여기서는 잠그기만 한다 — status가 'active'가 아니면 로그인·조회가 전부 막힌다
// (findAccountById/ByAuth/ByToken이 다 status='active' 필터를 타므로 추가 차단이 필요 없다).
// 실제 파기는 크론이 90일 지난 계정을 withdrawAccount(단일 파기 경로)로 지운다.
// 웹 /mypage/purge는 그대로 즉시 파기 — «지금 당장 지워달라»는 요구의 통로로 남긴다.
const WITHDRAW_KEEP_DAYS = 90;
async function withdrawMe(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");
  const ok = await verifyReauth(request, env, auth.account.id);
  if (!ok) return apiErr("REAUTH_REQUIRED");

  await db.prepare("UPDATE accounts SET status='withdrawn_pending', withdrawn_at=? WHERE id=?")
    .bind(new Date().toISOString(), auth.account.id).run();
  return apiOk({ withdrawn: true, purge_after_days: WITHDRAW_KEEP_DAYS });
}

// ── PATCH /api/v1/me/marketing — 광고성 정보 수신 동의 변경 ──
// 철회 수단을 두는 것은 선택이 아니라 의무다(정보통신망법 §50③). 앱 내정보에서 부른다.
async function patchMarketing(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.account) return apiErr("AUTH_REQUIRED");

  const b = await readJson(request);
  const mk = b && b.marketing;
  if (!mk || typeof mk !== "object") return apiErr("VALIDATION", { fields: { marketing: "수신 설정이 필요해요." } });
  const val = { email: mk.email === true, sms: mk.sms === true, call: mk.call === true, updated_at: new Date().toISOString() };
  await db.prepare("UPDATE accounts SET marketing=? WHERE id=?").bind(JSON.stringify(val), auth.account.id).run();
  return apiOk({ marketing: val });
}

// ── 쿠키 읽기 (index.js의 getCookie와 같은 동작, 의존 없이) ──
function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

// ── 라우터 ──────────────────────────────────────────────────
export async function handleAuthApi(request, db, env, url) {
  const p = url.pathname;
  const m = request.method;

  if (p === "/api/v1/auth/register" && m === "POST") return register(request, db, env);
  if (p === "/api/v1/auth/login" && m === "POST") return login(request, db, env);
  if (p === "/api/v1/auth/refresh" && m === "POST") return refresh(request, db, env);
  if (p === "/api/v1/auth/reauth" && m === "POST") return reauth(request, db, env);
  if (p === "/api/v1/auth/logout" && m === "POST") return logout(request, db, env);
  if (p === "/api/v1/me" && m === "GET") return me(request, db, env);
  if (p === "/api/v1/me" && m === "PATCH") return patchMe(request, db, env);
  if (p === "/api/v1/me/marketing" && m === "PATCH") return patchMarketing(request, db, env);
  if (p === "/api/v1/me" && m === "DELETE") return withdrawMe(request, db, env);
  const mDev = p.match(/^\/api\/v1\/me\/devices\/([0-9a-f-]{8,})$/i);
  if (mDev && m === "DELETE") return removeDevice(request, db, env, mDev[1]);

  return apiErr("NOT_FOUND");
}

// ── 소셜 로그인 승계 (index.js 콜백에서 호출) ───────────────
// 정본 §4의 핵심. 기존 콜백은 users에만 쓰고 있었다 — 그 뒤에 이 함수를 부르면
// accounts가 생기고 owner_token이 **그대로** 이어진다. children·records·R2 전부 살아남는다.
export async function linkSocialAccount(db, provider, uid, nickname, ownerToken) {
  const kind = `social_${provider}`;
  let account = await findAccountByAuth(db, kind, uid);
  if (account) {
    await touchLogin(db, account.id, kind, uid);
    return account;
  }
  // 이 owner_token으로 만든 계정이 이미 있나(다른 소셜로 먼저 가입한 경우) — 있으면 수단만 덧붙인다.
  account = await db.prepare("SELECT * FROM accounts WHERE owner_token=?").bind(ownerToken).first();
  if (!account) {
    const created = await createAccount(db, { ownerToken, displayName: nickname });
    account = await findAccountById(db, created.id);
  }
  await addAuthMethod(db, account.id, kind, uid, null, 1);
  await touchLogin(db, account.id, kind, uid);
  return account;
}
