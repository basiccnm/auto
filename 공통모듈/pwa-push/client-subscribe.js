// 클라이언트(브라우저) 구독 스니펫 — 권한 요청 → /sw.js 등록 → pushManager 구독 → 서버에 저장.
// 출처: 에듀싱크 templates.js(알림설정 페이지·달력 위젯) — 2026-07-16 실기기 검증본을 범용화.
//
// 붙이는 법: 이 파일을 페이지 <script>에 인라인하거나 정적 파일로 포함하고,
//   PUSH_CFG.vapidPublic에 서버가 내려준 env.VAPID_PUBLIC을 넣은 뒤
//   버튼 클릭 핸들러에서 enablePush()를 호출한다.
// iOS(사파리)는 홈 화면에 추가(PWA 설치)한 상태에서만 웹푸시가 동작한다 — 안내 문구 유지할 것.

var PUSH_CFG = {
  vapidPublic: "",                       // 서버 템플릿에서 주입: env.VAPID_PUBLIC
  subscribeUrl: "/api/push/subscribe",   // 구독 저장 라우트 (routes-example.js)
  swUrl: "/sw.js",                       // 서비스워커 경로 (반드시 사이트 루트)
};

// base64url → Uint8Array (applicationServerKey용)
function pushB64u8(b) {
  b = b.replace(/-/g, "+").replace(/_/g, "/");
  var p = "=".repeat((4 - (b.length % 4)) % 4);
  var raw = atob(b + p);
  var a = new Uint8Array(raw.length);
  for (var i = 0; i < raw.length; i++) a[i] = raw.charCodeAt(i);
  return a;
}

// 이 기기의 알림 상태(브라우저 권한 기준). 켜짐 표시용.
function pushReady() { return ("Notification" in window) && Notification.permission === "granted"; }

// 알림 켜기 전체 흐름. 성공 true / 실패 false 반환 (실패 사유는 alert로 사용자에게 표시).
async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    alert("이 브라우저는 웹푸시를 지원하지 않아요. 아이폰은 홈 화면에 추가(설치) 후 다시 시도해 주세요.");
    return false;
  }
  if (!PUSH_CFG.vapidPublic) { alert("알림 설정이 준비되지 않았어요."); return false; }
  try {
    var perm = await Notification.requestPermission();
    if (perm !== "granted") { alert("알림 권한이 허용되지 않았어요. 브라우저 설정에서 허용해 주세요."); return false; }
    var reg = await navigator.serviceWorker.register(PUSH_CFG.swUrl);
    await navigator.serviceWorker.ready;
    var sub = await reg.pushManager.getSubscription();
    if (!sub) { sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: pushB64u8(PUSH_CFG.vapidPublic) }); }
    var r = await fetch(PUSH_CFG.subscribeUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(sub) });
    if (r.ok) return true;
    alert("알림 등록 저장에 실패했어요.");
    return false;
  } catch (e) {
    alert("알림 켜기에 실패했어요: " + e);
    return false;
  }
}
