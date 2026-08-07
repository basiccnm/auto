/* 자녀 화면 색 12벌을 **표 하나에서** 만든다 — 앱 정의와 CSS 를 같이 뽑는다.
   12벌을 손으로 적으면 하나 고칠 때마다 12군데를 고쳐야 하고 반드시 한 군데를 빠뜨린다.

   ⚠ 12벌은 **색만 다르다.** 구조도 말도 같다(별·별의 길). 나이가 아니라 취향으로 고른다 —
      나이로 자동 배정하지 않는다. 「너는 여덟 살이니까 이거」는 아이가 제일 싫어하는 말이다.
   여섯씩 두 줄로 묶어 두었을 뿐, 어느 줄에서 골라도 된다. */
import fs from "node:fs";

// [키, 이름, 묶음, 밝기, 바탕, 카드, 글자, 흐린글자, 선, 강조, 연한강조바탕, 강조 위 글자]
// 밝은 테마의 --k 는 배지 같은 작은 글씨엔 흐리다. 검정을 32% 섞어 진한 짝을 만든다
const mixDark = (hex) => "#" + [1,3,5].map((i) => {
  const v = parseInt(hex.substr(i, 2), 16);
  return Math.round(v * 0.68).toString(16).padStart(2, "0");
}).join("");

const T = [
  // ── ㄱ 줄 ──
  ["rose",   "로즈",   "a", "light", "#FFF8FA", "#FFFFFF", "#2A1B22", "#7C6871", "#F3E1E8", "#D93B72", "#FBE3EC", "#FFFFFF"],
  ["lilac",  "라일락", "a", "light", "#FAF8FF", "#FFFFFF", "#241F33", "#6F6A85", "#E7E3F5", "#7C5BE0", "#EBE5FB", "#FFFFFF"],
  ["mint",   "민트",   "a", "light", "#F5FCFA", "#FFFFFF", "#132923", "#5E7A72", "#DCEFE9", "#0F9E86", "#DDF3EE", "#FFFFFF"],
  ["peach",  "피치",   "a", "light", "#FFFAF6", "#FFFFFF", "#2B1E17", "#7E6A5F", "#F3E5D9", "#D2661F", "#FBE7D8", "#FFFFFF"],
  ["butter", "버터",   "a", "light", "#FFFDF3", "#FFFFFF", "#2A2513", "#77705A", "#EFE9D2", "#B08400", "#F7EFCF", "#FFFFFF"],
  ["aqua",   "아쿠아", "a", "light", "#F4FBFC", "#FFFFFF", "#122A2E", "#5A757C", "#D9EBEE", "#0E8FA8", "#DBF0F4", "#FFFFFF"],
  // ── ㄴ 줄 ──
  ["gold",   "골드",   "b", "dark",  "#17181C", "#232529", "#F2F3F6", "#9AA0AC", "#33363D", "#FFC531", "#2E2812", "#241C05"],
  ["cyan",   "시안",   "b", "dark",  "#0E1320", "#1A2133", "#EEF2FA", "#93A0B8", "#2C3549", "#42D6F5", "#0F2E3A", "#04222C"],
  ["lime",   "라임",   "b", "dark",  "#0A0F0C", "#151C17", "#E7F5EA", "#8AA192", "#26332A", "#9DFF57", "#22330F", "#132200"],
  ["magenta","마젠타", "b", "dark",  "#0B0B0E", "#17171D", "#F5F5F8", "#8E8E9C", "#2A2A33", "#FF4FD8", "#330C2A", "#26001C"],
  ["orange", "오렌지", "b", "dark",  "#141110", "#201C1A", "#F6F1EE", "#9C918A", "#332C28", "#FF8A3D", "#33200F", "#241200"],
  ["violet", "바이올렛","b", "dark", "#12121C", "#1D1D2B", "#EDEDF7", "#9494AC", "#2E2E42", "#B79CFF", "#28204A", "#150E2E"],
];

const appDef =
`/* ── 자녀 화면 색 12벌 (2026-08-03) ─────────────────────────────
   여덟 살과 열세 살을 **한 화면으로 맞추려던 게 애초에 무리**였다. 평균을 잡으면 둘 다 어색해진다.
   그래서 **색만** 여러 벌 두고 아이가 고르게 한다 — 구조도 말도 하나다(별 · 별의 길).
   ⚠ 나이·성별로 자동 배정하지 않는다. 두 줄로 묶어 놓았을 뿐 어느 줄에서 골라도 된다.
      「너는 여덟 살이니까 이거」는 아이가 제일 싫어하는 말이다.
   ⚠ 이 표와 style.css 의 :root[data-kid-theme=…] 는 **짝이다.**
      둘 다 scripts/gen-themes.mjs 가 뽑는다. 손으로 고치지 말 것. */
const KID_THEMES = {
${T.map(([k, nm, g]) => `  ${(k + ":").padEnd(9)} { name: "${nm}", group: "${g}" },`).join("\n")}
};
const KID_THEME_KEYS = Object.keys(KID_THEMES);
/* 말은 한 벌뿐이다. 색이 바뀐다고 세는 단위가 바뀌면 아이가 헷갈리고,
   서버 star_ledger·「별의 길」과도 어긋난다. */
const KID_WORDS = { unit: "별", collect: "모은 별", board: "별의 길",
  done: "오늘 끝!", submit: "보내기", act: "" };
const kw = (k) => KID_WORDS[k] || "";
const kidBoard = () => "path";
`;

const css = ["\n/* ═══ 자녀 화면 색 12벌 — scripts/gen-themes.mjs 가 뽑은 블록 ══════════\n" +
  "   손으로 고치지 말 것. 색을 바꾸려면 스크립트의 표를 고치고 다시 뽑는다. */"];
for (const [k, , , scheme, bg, card, ink, muted, line, kk, ksoft, onkk] of T) {
  css.push(`:root[data-kid-theme="${k}"] {
  color-scheme: ${scheme};
  --bg: ${bg}; --card: ${card}; --ink: ${ink}; --muted: ${muted}; --line: ${line};
  --k: ${kk}; --k-soft: ${ksoft}; --on-kk: ${onkk}; --k-star: ${kk};
  /* 연한 바탕 위 «작은 글씨»용 진한 짝 — --k 그대로 쓰면 12px 배지가 4.5:1 을 못 넘는다 */
  --k-ink: ${scheme === "light" ? mixDark(kk) : kk};
}`);
  // 고르기 화면 미리보기 — 칸 자체에 색을 실어야 이름만 보고 고르는 일이 없다
  css.push(`.kd2-prev[data-kid-theme="${k}"] { --bg: ${bg}; --card: ${card}; --ink: ${ink}; --line: ${line}; --k: ${kk}; --k-star: ${kk}; }`);
}

fs.writeFileSync(process.argv[2], appDef, "utf8");
fs.writeFileSync(process.argv[3], css.join("\n") + "\n", "utf8");
console.log("색 " + T.length + "벌");
