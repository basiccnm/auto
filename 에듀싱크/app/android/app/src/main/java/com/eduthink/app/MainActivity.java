package com.eduthink.app;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebView;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 위젯 데이터 통로. registerPlugin 은 super.onCreate 앞에서 불러야 브리지에 실린다.
        registerPlugin(WidgetPlugin.class);
        super.onCreate(savedInstanceState);
        /* 🔴 엣지-투-엣지 (2026-08-10 대표님: 「전체 색상이 안 맞어」).
           웹뷰가 상태바 **밑에서** 시작하고 그 위 띠는 네이티브 배경색(베이지)이었다.
           베이지 화면에서는 안 보이는데 파란 미션 세계에서는 **베이지 띠**로 드러났다 —
           화면 위 띠 색을 CSS 로는 못 바꾼다(웹 바깥이다).
           → 웹뷰를 화면 끝까지 펴고 상태바·네비바를 투명으로. 콘텐츠 여백은
             이미 있는 --sa-top/--sa-bottom 다리(bridgeSafeArea)가 책임진다. */
        androidx.core.view.WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        getWindow().setStatusBarColor(android.graphics.Color.TRANSPARENT);
        getWindow().setNavigationBarColor(android.graphics.Color.TRANSPARENT);
        // 상태바 아이콘은 진하게 — 라이트 테마가 기본이고, 다크에서도 파스텔이라 읽힌다
        new androidx.core.view.WindowInsetsControllerCompat(getWindow(), getWindow().getDecorView())
            .setAppearanceLightStatusBars(true);
        bridgeSafeArea();
        handleWidget(getIntent());
    }


    /**
     * 🔴 **안전영역을 웹으로 넘긴다** (2026-08-10).
     *
     * CSS `env(safe-area-inset-*)` 는 믿을 수 없다 — 갤럭시 Z 폴드6(안드로이드 16)에서
     * **네비게이션 바가 있는데도 0** 으로 왔다. 그래서 버튼이 네비바 밑에 깔려
     * «보이는데 안 눌리는» 상태가 됐다(하루에 네 번 겪었다).
     *
     * CSS 로는 «0 인데 바가 있는 기기»와 «0 이 정답인 기기»를 구분할 수 없다 —
     * 값이 똑같이 0 인데 뜻이 반대다. 바닥값(max)을 깔면 네비바 없는 기기에서 과하게 뜬다.
     *
     * → 안드로이드는 진짜 값을 안다. 그 값을 --sa-top / --sa-bottom 으로 넘긴다.
     *   CSS 는 var(--sa-bottom, env(safe-area-inset-bottom)) 처럼 쓴다(넘어오기 전엔 env 로).
     *
     * ⚠ 화면 회전·폴더블 접기·키보드에 따라 값이 바뀐다 → 리스너로 «바뀔 때마다» 넘긴다.
     * ⚠ 그림이 상태바 뒤로 흐르는 디자인은 그대로 둔다 — 웹뷰를 잘라내지 않고 **값만** 준다.
     */
    private void bridgeSafeArea() {
        final WebView web = getBridge() == null ? null : getBridge().getWebView();
        if (web == null) return;
        ViewCompat.setOnApplyWindowInsetsListener(web, (v, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            float d = getResources().getDisplayMetrics().density;
            if (d <= 0) d = 1f;
            final int top = Math.round(bars.top / d);
            final int bottom = Math.round(bars.bottom / d);
            pushSafeArea();   // 값은 pushSafeArea 가 직접 읽는다
            return insets;
        });
        ViewCompat.requestApplyInsets(web);
    }

    /**
     * ⚠ 인셋은 **웹뷰가 index.html 을 읽기 전에** 먼저 온다.
     *   그때 넣으면 about:blank 에 넣는 셈이라 **그대로 사라진다**(2026-08-10 에뮬 실측 —
     *   변수가 «안 넘어옴» 이었다). 그래서 값을 들고 있다가 **몇 번 더** 넣는다.
     * ⚠ 여러 번 넣어도 같은 값이라 부작용이 없다. 한 번만 넣는 쪽이 훨씬 위험하다.
     */
    /**
     * ⚠ 리스너만 믿으면 안 된다 — 이 에뮬(안드로이드 14)에서는 인셋이 **웹뷰까지 오지 않아**
     *   리스너가 한 번도 안 불렸다(2026-08-10 실측: 변수가 «안 넘어옴»).
     *   → 넣을 때마다 **직접 읽는다.** 리스너는 «바뀌었을 때 다시 넣는» 신호로만 쓴다.
     * ⚠ 웹뷰가 index.html 을 읽기 전에 넣으면 그대로 사라진다 → 몇 번 더 넣는다.
     *   같은 값이라 여러 번 넣어도 부작용이 없다. 한 번만 넣는 쪽이 훨씬 위험하다.
     */
    private void pushSafeArea() {
        final WebView web = getBridge() == null ? null : getBridge().getWebView();
        if (web == null) return;
        for (int delay : new int[] { 0, 300, 1200, 2500 }) {
            web.postDelayed(() -> {
                WindowInsetsCompat wi = ViewCompat.getRootWindowInsets(web);
                if (wi == null) return;
                Insets bars = wi.getInsets(WindowInsetsCompat.Type.systemBars());
                float d = getResources().getDisplayMetrics().density;
                if (d <= 0) d = 1f;
                int top = Math.round(bars.top / d);
                int bottom = Math.round(bars.bottom / d);
                String js =
                    "document.documentElement.style.setProperty('--sa-top','" + top + "px');" +
                    "document.documentElement.style.setProperty('--sa-bottom','" + bottom + "px');";
                web.evaluateJavascript(js, null);
            }, delay);
        }
    }


    @Override
    public void onResume() {
        super.onResume();
        // 화면 회전·접기·다른 앱 다녀오기 — 그때마다 값이 바뀔 수 있다
        final WebView web = getBridge() == null ? null : getBridge().getWebView();
        if (web != null) ViewCompat.requestApplyInsets(web);
        pushSafeArea();
    }

    /** 앱이 이미 떠 있을 때 위젯을 누르면 onCreate 가 아니라 여기로 온다(launchMode=singleTask). */
    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleWidget(intent);
    }

    /**
     * 위젯의 어느 줄을 눌렀는지를 웹뷰에 넘긴다.
     * 웹은 window.__widgetGo 를 보고 그 화면을 연다(app.js). 값을 바로 못 읽을 수도 있어
     * 전역에 남겨 두기만 하고, 여는 것은 웹 쪽에서 준비가 됐을 때 한다.
     */
    private void handleWidget(Intent intent) {
        if (intent == null) return;
        String go = intent.getStringExtra("widget_go");
        if (go == null || go.isEmpty()) return;
        final String safe = go.replace("\\", "").replace("'", "");
        // 웹뷰가 아직 안 떴을 수 있다 — 로드가 끝난 뒤 실행되도록 post 로 미룬다.
        getBridge().getWebView().post(() ->
            getBridge().getWebView().evaluateJavascript(
                "window.__widgetGo='" + safe + "';window.dispatchEvent(new Event('widgetgo'))", null));
    }
}
