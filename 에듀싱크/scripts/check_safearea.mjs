#!/usr/bin/env node
/* 안전영역 검사 — 화면 가장자리에 «떠 있는» 요소가 `env(safe-area-inset-*)` 를
   **바닥값 없이** 쓰는 곳을 찾는다.

   🔴 2026-08-10 하루에 **네 번** 같은 원인으로 버튼이 죽었다:
        하단 3버튼(달력·★) · 상단 ☰ · 로그인 ✕ · 서랍 바닥 「내 정보·설정」.
      갤럭시 Z 폴드6 웹뷰는 `env(safe-area-inset-*)` 를 **0 으로 준다.**
      그러면 «+12px» 같은 여백만 남아 요소가 상태바·네비바 밑에 깔리고,
      **화면에는 보이는데 터치를 시스템이 가져간다.** 눈으로는 못 잡는 부류다.

   ⚠ 흐름 안의 그냥 여백은 잡지 않는다 — 0 이어도 좀 좁을 뿐 터치를 안 뺏긴다.
     position: fixed / sticky / absolute 인 블록만 본다.
   ⚠ 뒤쪽에서 같은 선택자를 max() 로 덮어썼으면 통과로 본다 — 우리는 그렇게 고쳐 왔다.
     선택자와 값이 다른 줄에 있어서 한 줄만 봐서는 못 찾는다.
     오탐이 쌓이면 아무도 안 본다(오늘 화면 지도에서 네 번 헛다리를 짚고 배웠다).

   → 고치는 법: max(calc(env(...) + N), 바닥값) */
import { readFileSync } from "node:fs";

const NL = String.fromCharCode(10);
const lines = readFileSync("app/www/style.css", "utf8").split(NL);
const RE_OPEN = /\{/g;
const RE_CLOSE = /\}/g;
const RE_NAME = /[.#][\w-]+/g;
const RE_ENV = /env\(safe-area-inset-/;
/* «감쌌다»고 볼 수 있는 두 가지:
     ① max(...) 로 바닥값을 깐 것 — 옛 방식. 네비바 없는 기기에서 과하게 뜬다.
     ② var(--sa-t / --sa-b) — 네이티브가 준 진짜 값. 지금 정본이다(MainActivity.bridgeSafeArea).
   ⚠ 새 화면은 ②를 쓸 것. env() 를 직접 쓰면 이 검사가 잡는다. */
const RE_MAX = { test: (t) => t.includes("max(") || t.includes("var(--sa-") || t.includes("--sa-t:") || t.includes("--sa-b:") };
const RE_FLOAT = /position:\s*(fixed|sticky|absolute)/;

/* CSS 를 블록 단위로 훑으며 콜백에 (선택자줄번호, 블록내용) 을 준다. */
function eachBlock(fn) {
  let depth = 0, start = -1, buf = [];
  lines.forEach((ln) => {
    const opens = (ln.match(RE_OPEN) || []).length;
    const closes = (ln.match(RE_CLOSE) || []).length;
    if (depth === 0 && opens) { start = lines.indexOf(ln, Math.max(0, start)); }
    if (depth > 0 || opens) buf.push(ln);
    depth += opens - closes;
    if (depth <= 0 && buf.length) { fn(buf[0], buf.join(NL)); depth = 0; buf = []; }
  });
}

// ① 이미 max() 로 감싼 규칙의 이름들을 먼저 모은다
const guarded = new Set();
const guardedSels = new Set();
eachBlock((selLine, block) => {
  /* ⚠ 새 방식(var(--sa-b))에는 env() 가 아예 없다 — env 를 요구하면 수집이 안 된다.
     «안전영역을 제대로 다룬 규칙»이면 수집한다. */
  if (RE_MAX.test(block)) {
    const s0 = String(selLine).split("{")[0].trim();
    (s0.match(RE_NAME) || []).forEach((n) => guarded.add(n));
    guardedSels.add(s0.replace(/^:root\s+/, ""));
  }
});

// ② 떠 있는데 바닥값이 없고, 뒤에서 덮어쓰지도 않은 것
const bad = [];
eachBlock((selLine, block) => {
  if (!RE_FLOAT.test(block) || !RE_ENV.test(block) || RE_MAX.test(block)) return;
  const sel = String(selLine).split("{")[0].trim().slice(0, 70);
  /* body::before 처럼 클래스·id 가 없는 선택자는 이름으로 못 맞춘다 —
     선택자 문자열 자체로도 대조한다. 안 그러면 이미 고친 것을 영원히 다시 잡는다. */
  const names = sel.match(RE_NAME) || [];
  if (!names.length && guardedSels.has(sel.replace(/^:root\s+/, ""))) return;
  if (names.length && names.every((n) => guarded.has(n))) return;
  bad.push(sel);
});

console.log("안전영역 검사 — 떠 있는 요소가 바닥값 없이 env() 를 쓰는 곳" + NL);
if (!bad.length) {
  console.log("✅ 없음");
} else {
  console.log("⚠ " + bad.length + "곳 — 안전영역을 0 으로 주는 폰에서 «보이는데 안 눌리는» 요소가 된다");
  bad.forEach((b) => console.log("   " + b));
  console.log(NL + "→ max(calc(env(...) + N), 바닥값) 으로 감쌀 것.");
}
