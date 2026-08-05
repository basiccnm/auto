/**
 * 카카오 로그인 (2026-07-27)
 *
 * 콘솔 설정은 이미 되어 있다 — 로그인 사용설정 ON, redirect_uri 등록 완료,
 * REST 키는 .env 의 KAKAO_REST_KEY 에 있다(→ 워커 시크릿으로 옮겨 씀).
 *
 * ⚠️ 카카오는 이메일 동의가 **선택**이다. 동의를 안 해도 로그인은 성공하고
 *    kakao_account.email 이 없다. 그걸 실패로 처리하면 가입이 막힌다 → email 은 null 허용.
 */
const AUTHORIZE = 'https://kauth.kakao.com/oauth/authorize';
const TOKEN = 'https://kauth.kakao.com/oauth/token';
const ME = 'https://kapi.kakao.com/v2/user/me';

export default {
  id: 'kakao',
  label: '카카오',
  supportsPKCE: true,

  authorizeUrl(env, { state, codeChallenge, redirectUri }) {
    const q = new URLSearchParams({
      client_id: env.KAKAO_REST_KEY,
      redirect_uri: redirectUri,
      response_type: 'code',
      state,
      // 닉네임은 필수, 이메일은 선택 동의. 콘솔에서 '선택 동의'로 열어두면 사용자가 거를 수 있다.
      scope: 'profile_nickname,account_email',
    });
    if (codeChallenge) {
      q.set('code_challenge', codeChallenge);
      q.set('code_challenge_method', 'S256');
    }
    return `${AUTHORIZE}?${q}`;
  },

  async exchange(env, { code, codeVerifier, redirectUri }) {
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: env.KAKAO_REST_KEY,
      redirect_uri: redirectUri,
      code,
    });
    if (codeVerifier) body.set('code_verifier', codeVerifier);
    // REST 키만으로도 동작한다(Client Secret 사용을 켰다면 아래를 추가)
    if (env.KAKAO_CLIENT_SECRET) body.set('client_secret', env.KAKAO_CLIENT_SECRET);

    const r = await fetch(TOKEN, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body,
    });
    const j = await r.json();
    if (!r.ok || !j.access_token) {
      throw new Error('kakao token 실패: ' + r.status + ' ' + JSON.stringify(j).slice(0, 200));
    }
    return { accessToken: j.access_token, raw: j };
  },

  async profile(env, { accessToken }) {
    const r = await fetch(ME, { headers: { Authorization: 'Bearer ' + accessToken } });
    const j = await r.json();
    if (!r.ok || !j.id) {
      throw new Error('kakao profile 실패: ' + r.status + ' ' + JSON.stringify(j).slice(0, 200));
    }
    const acc = j.kakao_account || {};
    return {
      uid: String(j.id),                                  // 숫자로 오므로 문자열로 통일
      email: acc.email || null,                           // 동의 안 하면 없다 — 정상이다
      nickname: (acc.profile && acc.profile.nickname) || null,
      raw: j,
    };
  },
};
