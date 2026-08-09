#!/usr/bin/env node
/* 화면 지도 — 각 화면의 «들어오는 길»과 «나가는 길»을 센다.
   2026-08-10 대표님 지적: 「논리적으로 돌아가는 게 왜 자꾸 이상하게 구성되어 있나」.
   말로 세면 또 놓친다. 코드에서 직접 센다.
   ⚠ 두 번 헛다리를 짚었다:
     ① `Screens` 밖(STUB)에도 `school:`·`supplies:` 같은 **같은 이름의 데이터**가 있다
        → 파일 전체에서 찾으면 데이터를 화면 본문으로 착각한다. Screens 안에서만 찾는다.
     ② 화면이 다른 화면·헬퍼에 **위임**하면 뒤로가기가 그쪽에 있다
        (`meal: () => Screens.school()`) → 한 겹 따라간다. */
import { readFileSync } from "node:fs";
const src = readFileSync("app/www/app.js", "utf8");

const S0 = src.indexOf("const Screens = {");
const S1 = src.indexOf("\n};", S0);

const screens = [];
{
  const body = src.slice(S0, S1);
  const re = /\n  ([a-zA-Z][\w-]*)\s*:\s*(\(|async)/g;
  let m; while ((m = re.exec(body))) screens.push(m[1]);
}

const bodyOf = (name) => {
  const i = src.indexOf("\n  " + name + ":", S0);
  if (i < 0 || i > S1) return "";
  let end = S1;
  for (const o of screens) {
    const j = src.indexOf("\n  " + o + ":", i + 3);
    if (j > i && j < end) end = j;
  }
  return src.slice(i, end);
};
const fnBody = (name) => {
  /* 문자열 안의 백슬래시는 한 번 더 써야 정규식이 된다 — "\s+" 는 그냥 s+ 였다.
     그래서 legalScreen·gameCard 같은 헬퍼를 못 찾았고, 그 안에 있던
     뒤로가기를 놓쳐 「나가는 길 없음」이 부풀었다(2026-08-10 세 번째 헛다리). */
  const i = src.indexOf(String.fromCharCode(10) + "function " + name + "(");
  return i < 0 ? "" : src.slice(i, i + 8000);
};
const resolved = (name) => {
  let b = bodyOf(name);
  for (const o of screens) if (o !== name && b.includes("Screens." + o + "(")) b += bodyOf(o);
  for (const m of b.matchAll(/\b([a-zA-Z]\w{3,})\(/g)) b += fnBody(m[1]);
  return b;
};

/* ⚠ 「#이름」이 나온다고 다 **입구**가 아니다. 처음엔 그렇게 셌다가
     game 이 27곳으로 나왔는데, 열어 보니 대부분 **나가는 길**(`href="#game"` 뒤로가기)과
     **라우터 되돌림**(history.replaceState)이었다. 진짜 입구는 홈 카드·★ 둘뿐이다.
   → 뒤로가기·되돌림·주석 줄은 빼고 센다. 안 그러면 «덤불»이 아닌 걸 덤불로 읽는다. */
const NOT_ENTRY = /class="back"|history\.replaceState|goBack|^\s*[/*]|아니다|예전엔/;
const inbound = new Map(screens.map((s) => [s, 0]));
const lines = src.split(String.fromCharCode(10));
/* ⚠ **입구 = 사람이 누르는 것**이다. `onclick=` 이나 `href="#…"` 이 있어야 입구다.
     그냥 `location.hash = "#game";` 한 줄은 **일을 마치고 돌아가는 것**이지 입구가 아니다.
     이걸 안 가르면 game 이 27곳 → 14곳으로만 줄고 여전히 «덤불»로 읽힌다. 실제 입구는 2곳이다. */
const IS_ENTRY = /onclick=|href="#/;
lines.forEach((ln) => {
  if (NOT_ENTRY.test(ln) || !IS_ENTRY.test(ln)) return;
  for (const m of ln.matchAll(/['"`]#([a-zA-Z][\w-]*)['"`]/g)) {
    if (inbound.has(m[1])) inbound.set(m[1], inbound.get(m[1]) + 1);
  }
});

/* 나가는 길 = 뒤로가기 **또는** 그 화면을 끝내는 버튼.
   ⚠ 뒤로 화살표만 찾으면 «막다른 화면이 의도인 곳»까지 잡는다 —
     locked(이용권 사러 가기)·childtheme(테마 고르기)·childexpired(다시 연결하기)는
     화살표는 없어도 나갈 버튼이 있다. 갇히지 않는다. */
const OUT = /subHeader\(|class="back"|App\.goBack\(|gm-back|lg-close|sub-back|hv3-ham|drawerOpen\(|btn-primary|kd3-go|kd2-cta|lk-go/;
const rows = screens.map((s) => ({ name: s, in: inbound.get(s), out: OUT.test(resolved(s)) }));

const noExit = rows.filter((r) => !r.out);

/* ⚠ 「입구 수」는 **믿을 수 없어서 뺐다.**
     세 번 고쳤는데도 못 맞췄다 — 화면으로 가는 길이 세 가지다:
       ① href="#x"  ② onclick="location.hash='#x'"  ③ onclick="App.무언가()" 안에서 이동
     ③ 을 세려면 함수마다 무슨 hash 로 가는지 따라가야 하고, 그건 이 도구 몫이 아니다.
     ①②만 세면 「입구 없음」이 25곳으로 뜬다 — 실제로는 다 열려 있다.
   ⚠ 이 도구가 답할 수 있는 건 하나다: **들어갔는데 못 나오는 화면이 있는가.**
     그것만 답한다. 못 하는 걸 하는 척하면 그 숫자를 믿고 엉뚱한 걸 고치게 된다.
     (실제로 그럴 뻔했다 — 「game 입구 27곳 = 덤불」이라고 보고했는데 진짜 입구는 2곳이었다.) */
console.log("화면 " + rows.length + "개 — 들어갔다가 못 나오는 곳을 찾는다");
console.log(noExit.length ? "❌ 나가는 길이 없다 — " + noExit.length + "곳" : "✅ 모든 화면에 나가는 길이 있다");
noExit.forEach((r) => console.log("   " + r.name));
console.log("");
console.log("※ 막다른 화면이 의도인 곳도 있다(childexpired: 연결이 끝났다는 안내).");
console.log("※ 이 도구는 «입구 수»를 세지 않는다 — 위 주석 참고.");
