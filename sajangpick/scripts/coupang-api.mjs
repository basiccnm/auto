// 쿠팡 파트너스 Open API 연동 모듈 — 골격만 만들어 둔 상태.
//
// 왜 지금 만들어 두나: 파트너스 최종승인(누적 판매 15만원)이 나면 키가 생기는데,
// 그때 키만 넣으면 바로 돌아가게 하려는 것. 지금은 네트워크 호출을 하지 않는다.
//
// 키 넣는 법: 프로젝트 루트에 .env 파일을 만들고 아래 두 줄을 적는다.
//   COUPANG_ACCESS_KEY=...
//   COUPANG_SECRET_KEY=...
// .env는 git에 올라가지 않는다(.gitignore에 등록됨).
//
// ⚠ 엔드포인트 경로는 공식 문서에서 확인한 값으로 채워야 한다.
//    추측해서 호출하면 안 된다(경로를 무작위로 찔러보면 차단 대상이 된다).
//    키를 받는 시점에 파트너스 개발자 문서를 열어 PATHS를 확정할 것.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const HOST = 'https://api-gateway.coupang.com';

// 문서 확인 후 확정할 것. 지금 값은 자리표시자다.
const PATHS = {
  search: '/v2/providers/affiliate_open_api/apis/openapi/products/search',
  deeplink: '/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink',
};

// .env를 아주 단순하게 읽는다(라이브러리 추가 없이).
function loadEnv() {
  const file = path.join(ROOT, '.env');
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

export function getKeys() {
  const env = { ...loadEnv(), ...process.env };
  const accessKey = env.COUPANG_ACCESS_KEY;
  const secretKey = env.COUPANG_SECRET_KEY;
  return { accessKey, secretKey, ready: Boolean(accessKey && secretKey) };
}

// 쿠팡은 요청마다 HMAC 서명을 요구한다.
// 서명 대상 문자열 = 시각 + HTTP메서드 + 경로 + 쿼리스트링
function buildAuthHeader({ method, urlPath, query = '', accessKey, secretKey }) {
  // yyMMddTHHmmssZ (GMT)
  const signedDate = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, 'Z').slice(2);
  const message = signedDate + method + urlPath + query;
  const signature = crypto.createHmac('sha256', secretKey).update(message).digest('hex');
  return `CEA algorithm=HmacSHA256, access-key=${accessKey}, signed-date=${signedDate}, signature=${signature}`;
}

async function request({ method, urlPath, query = '', body = null }) {
  const { accessKey, secretKey, ready } = getKeys();
  if (!ready) {
    throw new Error('쿠팡 파트너스 API 키가 없습니다 (.env의 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY)');
  }

  const auth = buildAuthHeader({ method, urlPath, query, accessKey, secretKey });
  const res = await fetch(`${HOST}${urlPath}${query ? `?${query}` : ''}`, {
    method,
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) throw new Error(`쿠팡 API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

// 상품 검색 → 이미지 URL 확보용.
// 반환 형태는 실제 응답을 보고 맞춰야 하므로 지금은 원본을 그대로 넘긴다.
export async function searchProduct(keyword, limit = 5) {
  const query = `keyword=${encodeURIComponent(keyword)}&limit=${limit}`;
  return request({ method: 'GET', urlPath: PATHS.search, query });
}

// 상품 URL을 파트너스 추적 링크로 바꾼다.
export async function createDeeplink(urls) {
  return request({ method: 'POST', urlPath: PATHS.deeplink, body: { coupangUrls: urls } });
}

// 렌더 파이프라인이 부르는 자리.
// 키가 없으면 이미지 없이 진행하라고 알려주고 넘어간다(렌더를 막지 않는다).
export async function fetchProductImages(plan) {
  const { ready } = getKeys();
  if (!ready) {
    return { ok: false, reason: 'API 키 미발급 — 이미지 없이 렌더', images: [] };
  }
  const result = await searchProduct(plan.product_name);
  return { ok: true, raw: result, images: [] }; // 응답 구조 확인 후 images 매핑을 채울 것
}
