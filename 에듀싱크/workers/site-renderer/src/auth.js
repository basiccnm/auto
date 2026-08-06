// 소셜 로그인(카카오·구글·네이버) OAuth 공통 처리.
// - 키는 env에서 읽고, 키가 없는 제공자는 providersFrom()에서 빠져 버튼이 자동으로 숨는다(부분 오픈).
// - 수집 범위: 회원 고유번호 + 닉네임만(이메일·전화 없음) → 3사 모두 심사 없는/가장 가벼운 범위.
// - 네이버는 검수 통과 전엔 등록된 테스터만 로그인됨(개발 단계 제약, 코드는 동일).

const PROVIDER_LABEL = { kakao: "카카오", google: "Google", naver: "네이버" };

export function providerLabel(p) {
  return PROVIDER_LABEL[p] || p;
}

// env에 키가 있는 제공자 목록 — 이 목록 기준으로 로그인 버튼이 그려진다.
export function providersFrom(env) {
  const list = [];
  if (env.KAKAO_REST_KEY) list.push("kakao");
  if (env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET) list.push("google");
  if (env.NAVER_CLIENT_ID && env.NAVER_CLIENT_SECRET) list.push("naver");
  return list;
}

function redirectUriOf(provider, origin) {
  return `${origin}/auth/${provider}/callback`;
}

// 1단계: 제공자 로그인 화면으로 보낼 URL. state는 CSRF 방지용(쿠키와 대조).
export function authorizeUrl(provider, env, origin, state) {
  const redirect = encodeURIComponent(redirectUriOf(provider, origin));
  if (provider === "kakao") {
    return `https://kauth.kakao.com/oauth/authorize?client_id=${env.KAKAO_REST_KEY}&redirect_uri=${redirect}&response_type=code&state=${state}`;
  }
  if (provider === "google") {
    return `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(env.GOOGLE_CLIENT_ID)}&redirect_uri=${redirect}&response_type=code&scope=${encodeURIComponent("openid profile")}&state=${state}`;
  }
  if (provider === "naver") {
    return `https://nid.naver.com/oauth2.0/authorize?client_id=${encodeURIComponent(env.NAVER_CLIENT_ID)}&redirect_uri=${redirect}&response_type=code&state=${state}`;
  }
  return null;
}

// 실패 원인을 삼키지 않도록 상태·본문을 함께 돌려준다(로그인 실패 진단용).
async function postForm(url, params) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(params),
  });
  const text = await resp.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* 비JSON 응답(에러 HTML 등) */ }
  return { ok: resp.ok, status: resp.status, json, text };
}

// 2단계: 콜백으로 받은 code를 액세스 토큰으로 교환한 뒤 프로필 조회.
// 반환: { uid, nickname } — 실패 시 { error } (호출부가 로그로 남기고 오류 페이지 처리).
// ⚠️ 실패를 조용히 null로 뭉개면 원인 추적이 불가능해 반드시 error 문자열을 채워 돌려준다.
export async function fetchIdentity(provider, env, origin, code, state) {
  const redirect = redirectUriOf(provider, origin);

  if (provider === "kakao") {
    // 카카오 콘솔에서 "클라이언트 시크릿"이 ON이면 토큰 요청에 client_secret이 없을 때 KOE010으로 거부된다.
    // 키가 설정돼 있을 때만 실어 보내 시크릿 ON/OFF 양쪽 모두에서 동작하게 한다(2026-07-17 실패 원인).
    const kakaoParams = {
      grant_type: "authorization_code",
      client_id: env.KAKAO_REST_KEY,
      redirect_uri: redirect,
      code,
    };
    if (env.KAKAO_CLIENT_SECRET) kakaoParams.client_secret = env.KAKAO_CLIENT_SECRET;
    const tok = await postForm("https://kauth.kakao.com/oauth/token", kakaoParams);
    if (!tok.json || !tok.json.access_token) {
      return { error: `kakao token ${tok.status}: ${tok.text.slice(0, 300)}` };
    }
    const resp = await fetch("https://kapi.kakao.com/v2/user/me", {
      headers: { Authorization: `Bearer ${tok.json.access_token}` },
    });
    const meText = await resp.text();
    if (!resp.ok) return { error: `kakao me ${resp.status}: ${meText.slice(0, 300)}` };
    let me = null;
    try { me = JSON.parse(meText); } catch { return { error: `kakao me parse: ${meText.slice(0, 200)}` }; }
    if (!me || me.id == null) return { error: `kakao me no-id: ${meText.slice(0, 300)}` };
    const nickname = (me.properties && me.properties.nickname) || (me.kakao_account && me.kakao_account.profile && me.kakao_account.profile.nickname) || null;
    return { uid: String(me.id), nickname };
  }

  if (provider === "google") {
    const tok = await postForm("https://oauth2.googleapis.com/token", {
      grant_type: "authorization_code",
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      redirect_uri: redirect,
      code,
    });
    if (!tok.json || !tok.json.access_token) {
      return { error: `google token ${tok.status}: ${tok.text.slice(0, 300)}` };
    }
    const resp = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
      headers: { Authorization: `Bearer ${tok.json.access_token}` },
    });
    const meText = await resp.text();
    if (!resp.ok) return { error: `google me ${resp.status}: ${meText.slice(0, 300)}` };
    let me = null;
    try { me = JSON.parse(meText); } catch { return { error: `google me parse: ${meText.slice(0, 200)}` }; }
    if (!me || !me.sub) return { error: `google me no-sub: ${meText.slice(0, 300)}` };
    return { uid: String(me.sub), nickname: me.name || null };
  }

  if (provider === "naver") {
    const tok = await postForm("https://nid.naver.com/oauth2.0/token", {
      grant_type: "authorization_code",
      client_id: env.NAVER_CLIENT_ID,
      client_secret: env.NAVER_CLIENT_SECRET,
      code,
      state,
    });
    if (!tok.json || !tok.json.access_token) {
      return { error: `naver token ${tok.status}: ${tok.text.slice(0, 300)}` };
    }
    const resp = await fetch("https://openapi.naver.com/v1/nid/me", {
      headers: { Authorization: `Bearer ${tok.json.access_token}` },
    });
    const meText = await resp.text();
    if (!resp.ok) return { error: `naver me ${resp.status}: ${meText.slice(0, 300)}` };
    let me = null;
    try { me = JSON.parse(meText); } catch { return { error: `naver me parse: ${meText.slice(0, 200)}` }; }
    const r = me && me.response;
    if (!r || !r.id) return { error: `naver me no-id: ${meText.slice(0, 300)}` };
    return { uid: String(r.id), nickname: r.nickname || null };
  }

  return { error: `unknown provider: ${provider}` };
}
