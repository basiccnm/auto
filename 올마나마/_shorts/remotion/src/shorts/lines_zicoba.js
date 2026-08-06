// 지코바 순살양념구이 원가편 대사 — 이거 얼마남아 5 (2026-07-28)
//
// 🔴 여성향 톤. 올마=여자(핑크, 진행) / 사장님=남자(노랑).
//    목소리 올마 SunHi(여) / 사장님 InJoon(남), 둘 다 +70%.
//
// 🔴 sec / head 는 voice/trim.json 실측값. 음성 public/voiceZ1/01~12.mp3
// 🔴 화면 글은 아라비아 숫자, TTS 대본만 한글 숫자.
// 🔴 LEAD 0.2 고정 — 늘리면 쇼츠가 죽는다(배달편 11회 사고).
//
// 🔴 숫자는 **도매(매장 매입) 기준**. 합 5,673원 · 원가율 24%.
// 🔴 훅에서 원가를 **까지 않는다** — 궁금증만 남기고 8번에서 공개한다.
//
// ── 화면(page) 인덱스 (pages_yeopgi.js) ──
//   0 닭·소스  1 나머지 재료  2 원가공개  3 인사이트

export const LEAD = 0.2;

export const LINES = [
  {
    // 훅 — 첫 프레임이 썸네일
    who: "올마", with: "사장님", sec: 2.73, head: 0.0, gap: 0.25, bg: "soft",
    parts: [
      { text: "23,500원 지코바 순살, 재료값 얼마일 것 같아?", face: "놀람", sec: 0.12, hook: true, noBubble: true },
      { text: "23,500원 지코바 순살,", face: "놀람", sec: 1.36, emo: { who: "올마", text: "헉" } },
      { text: "재료값 얼마일 것 같아?", face: "웃음", sec: 1.25, of: "당황" },
    ],
  },
  {
    // 공지 — 선긋기
    who: "올마", with: "사장님", sec: 1.87, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "우린 재료값만 봐. 만드는 품은 몰라", face: "웃음", sec: 1.87, of: "시치미" }],
  },
  {
    // 재료 ① — 소스·떡
    who: "올마", with: "사장님", sec: 1.74, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "닭다리살 800g 4,200원", face: "놀람", sec: 1.74, page: 0, of: "시치미" }],
  },
  {
    // 재료 ① 마무리 — 숫자만 말하고 판단은 안 한다
    who: "올마", with: "사장님", sec: 1.94, head: 0.0, gap: 0.22, bg: "soft",
    parts: [{ text: "이거 하나가 74%야", face: "놀람", sec: 1.94, page: 0, of: "당황", emo: { who: "올마", text: "74%!" } }],
  },
  {
    // 사장 반응 ① — 변명
    who: "사장님", with: "올마", sec: 1.7, head: 0.056, gap: 0.22, bg: "soft",
    parts: [{ text: "저흰 숯불에 굽는 게 달라요", face: "변명", sec: 1.7, page: 0, of: "웃음" }],
  },
  {
    // 재료 ②
    who: "올마", with: "사장님", sec: 2.54, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "양념소스 960원, 치킨무 353원", face: "웃음", sec: 2.54, page: 1, of: "식은땀" }],
  },
  {
    // 재료 ③
    who: "올마", with: "사장님", sec: 1.46, head: 0.0, gap: 0.2, bg: "soft",
    parts: [{ text: "구이용 밀떡까지 다 더해도", face: "웃음", sec: 1.46, page: 1, of: "화들짝" }],
  },
  {
    // 원가 공개 — 정점. 뒤에 0.4초 정적
    who: "올마", with: "사장님", sec: 2.31, head: 0.0, gap: 0.4, bg: "soft",
    parts: [{ text: "5,673원. 원가율 24%야", face: "놀람", sec: 2.31, page: 2, of: "경악", emo: { who: "올마", text: "24%" } }],
  },
  {
    // 사장 버럭
    who: "사장님", with: "올마", sec: 3.53, head: 0.036, gap: 0.2, bg: "soft",
    parts: [{ text: "숯불 관리! 인건비! 그건요!", face: "발끈", sec: 3.53, of: "화들짝", emo: { who: "사장님", text: "부들부들" } }],
  },
  {
    // 인사이트 — 소비자 이득
    who: "올마", with: "사장님", sec: 2.3, head: 0.0, gap: 0.28, bg: "soft",
    parts: [{ text: "근데 뼈는 국산인데 순살은 수입산", face: "웃음", sec: 2.3, page: 3, of: "좌절" }],
  },
  {
    // 사장 머쓱
    who: "사장님", with: "올마", sec: 2.76, head: 0.053, gap: 0.28, bg: "soft",
    parts: [{ text: "작년에 원산지로 걸린 뒤에 바꿨어요", face: "뿌듯", sec: 2.76, of: "웃음", emo: { who: "사장님", text: "히힣" } }],
  },
  {
    // 마무리 — 사이트
    who: "올마", with: "사장님", sec: 2.95, head: 0.0, gap: 0.8, bg: "soft",
    parts: [{ text: "다음은 초간단 지코바 레시피", face: "웃음", sec: 2.95, site: true, of: "뿌듯" }],
  },
];
