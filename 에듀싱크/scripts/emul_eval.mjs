// ============================================================
// 에뮬레이터 웹뷰에 JS 를 밀어넣고 결과를 받는다 (2026-08-07)
//
//   node scripts/emul_eval.mjs "JS 식"
//   node scripts/emul_eval.mjs --file 파일경로
//
// 왜 필요한가
//   에뮬은 «실기»지만 손으로 누르면 상태를 만드는 데 매번 몇 분이 든다.
//   로그인·시험 데이터 주입·화면 이동을 여기서 한 줄로 한다.
//   ⚠ 스크린샷만 보고 판단하지 말 것 — 여기서 **값을 재서** 확인한다.
//
// 준비 (한 번만)
//   adb forward tcp:9333 localabstract:webview_devtools_remote_<pid>
//   adb reverse tcp:8788 tcp:8788      ← 에뮬의 localhost:8788 을 PC 로 넘긴다
//   ⚠ pid 는 앱을 다시 띄울 때마다 바뀐다. /proc/net/unix 에서 다시 찾아야 한다.
//
// ⚠ 디버깅 소켓은 **디버그 빌드에서만** 열린다. 출시본에서는 닫혀 있어야 한다
//   (STATUS «앱 긁힘 방어선» — 웹뷰 디버깅 OFF).
// ============================================================
const PORT = process.env.CDP_PORT || 9333;

const arg = process.argv[2];
let expr;
if (arg === "--file") {
  const { readFileSync } = await import("node:fs");
  expr = readFileSync(process.argv[3], "utf8");
} else {
  expr = arg;
}
if (!expr) { console.error("쓸 JS 를 주세요."); process.exit(1); }

const list = await fetch(`http://127.0.0.1:${PORT}/json/list`).then(r => r.json());
const page = list.find(t => t.type === "page") || list[0];
if (!page) { console.error("웹뷰를 못 찾았습니다. adb forward 가 걸려 있나요?"); process.exit(1); }

const ws = new WebSocket(page.webSocketDebuggerUrl);
const done = new Promise((resolve, reject) => {
  // 전 화면 순회 같은 긴 검사는 30초를 넘는다 — CDP_TIMEOUT 으로 늘린다(기본 30초)
  const timer = setTimeout(() => reject(new Error("시간 초과")), +(process.env.CDP_TIMEOUT || 30000));
  ws.onopen = () => ws.send(JSON.stringify({
    id: 1, method: "Runtime.evaluate",
    params: { expression: expr, awaitPromise: true, returnByValue: true },
  }));
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id !== 1) return;
    clearTimeout(timer);
    if (m.result?.exceptionDetails) {
      reject(new Error(m.result.exceptionDetails.exception?.description || "예외"));
    } else {
      resolve(m.result?.result?.value);
    }
    ws.close();
  };
  ws.onerror = (e) => { clearTimeout(timer); reject(new Error("웹소켓 오류")); };
});

try {
  const v = await done;
  console.log(typeof v === "string" ? v : JSON.stringify(v, null, 2));
} catch (e) {
  console.error("실패:", e.message);
  process.exit(1);
}
