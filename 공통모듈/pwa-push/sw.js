// 서비스워커 — 무페이로드 푸시 수신 → (선택) 서버에서 최신 알림 내용 조회 → 알림 표시. 클릭 시 URL로 이동.
// 출처: 에듀싱크 site-renderer의 SERVICE_WORKER_JS 상수 — 2026-07-16 실기기 검증본을 범용화.
//
// 붙이는 법: 아래 CONFIG만 프로젝트에 맞게 고치고, Workers 라우트에서
//   if (path === "/sw.js") return new Response(SW_JS, { headers: { "Content-Type": "application/javascript", "Cache-Control": "no-cache" } });
// 처럼 서빙하거나(문자열로 import), 정적 파일이면 사이트 루트에 그대로 둔다 (스코프 때문에 반드시 루트).

var CONFIG = {
  // 무페이로드 푸시라 알림 문구는 여기서 정한다.
  fallback: { title: "서비스 이름", body: "새 소식을 확인하세요", url: "/" },
  // 발송 직전 알림의 실제 문구를 내려주는 API (없으면 "" — fallback만 사용).
  // 응답 형식: { ok:true, title:"...", body:"...", url:"/..." }
  latestUrl: "/api/push/latest",
  tag: "reminder", // 같은 tag의 알림은 겹쳐 쌓이지 않고 교체됨
};

self.addEventListener("push", function (e) {
  var fallback = CONFIG.fallback;
  if (!CONFIG.latestUrl) {
    e.waitUntil(self.registration.showNotification(fallback.title, { body: fallback.body, data: { url: fallback.url }, tag: CONFIG.tag }));
    return;
  }
  e.waitUntil(
    fetch(CONFIG.latestUrl, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var n = (d && d.ok && d.title) ? d : fallback;
        return self.registration.showNotification(n.title, { body: n.body, data: { url: n.url }, tag: CONFIG.tag });
      })
      .catch(function () { return self.registration.showNotification(fallback.title, { body: fallback.body, data: { url: fallback.url }, tag: CONFIG.tag }); })
  );
});

self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window" }).then(function (cs) {
    var u = (e.notification.data && e.notification.data.url) || CONFIG.fallback.url;
    for (var i = 0; i < cs.length; i++) { if ("focus" in cs[i]) return cs[i].focus(); }
    if (clients.openWindow) return clients.openWindow(u);
  }));
});
