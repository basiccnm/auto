/**
 * OAuth provider 레지스트리 (2026-07-27)
 *
 * ★ provider 를 하나 늘리는 비용 = 파일 1개 + 여기 1줄 + 시크릿 2개.
 *   state 검증·세션 발급·계정 생성은 전부 routes/auth.js(코어)가 한다.
 *   provider 파일은 **세 함수만** 구현한다: authorizeUrl / exchange / profile
 *
 * 세 사가 실제로 다른 건 딱 세 가지다 —
 *   ① authorize 쿼리 파라미터 이름  ② 토큰 교환 body 형식  ③ 프로필 JSON 경로
 *   그래서 그 셋만 어댑터에 가둔다.
 *
 * 3단계에서 google.js · naver.js 를 추가한다.
 *   🔴 네이버는 **검색 API 와 별도 앱**으로 등록할 것 — scripts/naver/config.py 에
 *      "같은 앱에 로그인을 추가하면 검색 API 가 막히는 사례" 경고가 있고,
 *      호출 한도도 앱 단위라 로그인 트래픽이 시세 수집을 죽일 수 있다.
 */
import kakao from './kakao.js';

const REGISTRY = { kakao };

export function getProvider(id) {
  return Object.prototype.hasOwnProperty.call(REGISTRY, id) ? REGISTRY[id] : null;
}

export function providerIds() {
  return Object.keys(REGISTRY);
}
