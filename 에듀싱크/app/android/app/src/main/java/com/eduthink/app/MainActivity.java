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
        /* 내비바 자리는 이제 웹뷰가 안 덮는다(applyBottomInset) — 그 자리에 보일 색을
           앱 바탕(#f2f3f6)으로 맞춰 둔다. 투명으로 두면 창 기본색(검정)이 비친다. */
        getWindow().setNavigationBarColor(0xFFF2F3F6);
        getWindow().setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(0xFFF2F3F6));
        new androidx.core.view.WindowInsetsControllerCompat(getWindow(), getWindow().getDecorView())
            .setAppearanceLightNavigationBars(true);   // 밝은 바탕이라 아이콘은 진하게
        /* ⚠ 삼성 One UI 는 투명 바 위에 **대비 보정 막**을 자동으로 깐다(API 29+).
           끄지 않으면 바 자리가 늘 뿌옇게 떠서 «색이 안 맞는» 띠로 보인다(폴드6 실측). */
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            getWindow().setStatusBarContrastEnforced(false);
            getWindow().setNavigationBarContrastEnforced(false);
        }
        // 상태바 아이콘은 진하게 — 라이트 테마가 기본이고, 다크에서도 파스텔이라 읽힌다
        new androidx.core.view.WindowInsetsControllerCompat(getWindow(), getWindow().getDecorView())
            .setAppearanceLightStatusBars(true);
        bridgeSafeArea();
        /* 🔴 글자 배율 고정 (2026-08-11 폴드6 실측).
           시스템 «글자 크게»가 웹뷰 textZoom 을 1.15~1.3배로 끌어올려
           px 로 잰 화면이 전부 부풀었다(시계 60→69px, 홈 55px 넘침).
           우리 디자인은 화면 크기에 비례해 **스스로** 글자를 키우는 체계라
           이중 배율이 걸리면 어떤 폰에서도 어긋난다 → 100 고정. */
        WebView wv = (WebView) bridge.getWebView();
        if (wv != null) {
            wv.getSettings().setTextZoom(100);
            /* 🔴 «웹이 물어보는» 통로 (2026-08-11 폴드6 실기).
               네이티브가 **밀어넣는** 방식만으로는 값이 사라진다 — 앱 안에서 새로고침이
               일어나면(로그인 등) 되풀이 창(0~8초)이 이미 지나 있어서 --sa-bottom 이 0 이 된다.
               그러면 내비바가 있는데도 0 이 되어 **입력바·하단 바가 내비바를 침범한다**
               (대표님이 폴드6 실기에서 발견 — 그 순간 실측 saB=0).
               위쪽은 CSS 바닥값 24px 이 막지만 아래쪽은 바닥값을 못 깐다(제스처 폰은 0 이 정답).
               → 웹이 **아무 때나 직접 물어볼 수 있게** 한다. 밀어넣기는 그대로 두고 겹친다. */
            wv.addJavascriptInterface(new Object() {
                @android.webkit.JavascriptInterface
                public String get() {
                    WindowInsetsCompat wi = ViewCompat.getRootWindowInsets(wv);
                    if (wi == null) return "";
                    Insets b = wi.getInsets(WindowInsetsCompat.Type.systemBars());
                    float d = getResources().getDisplayMetrics().density;
                    if (d <= 0) d = 1f;
                    /* 아래는 늘 0 이다 — 웹뷰를 내비바 «위»에서 끝내므로(applyBottomInset)
                       웹이 따로 비워 둘 자리가 없다. 위는 그대로 넘긴다(상태바 뒤로 그림이 흐른다). */
                    return Math.round(b.top / d) + ",0";
                }
            }, "NativeInsets");
        }
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
            pushSafeArea();   // 값 적용은 pushSafeArea 가 직접 한다(이 리스너는 신호일 뿐)
            return insets;
        });
        ViewCompat.requestApplyInsets(web);
    }

    /* 🔴 내비바 자리는 **웹뷰를 잘라서** 비운다 (2026-08-11 대표님:
       「출력이 하단 메뉴 위에까지만 · 하단메뉴까지 출력되지 않게」).
       CSS 여백으로 비우면 스크롤할 때 내용이 내비바 «뒤로 흘러» 겹쳐 보인다.
       ⚠ 웹뷰 자신의 padding 은 안 먹는다(폴드6 실측 — innerHeight 그대로 905).
         **부모 컨테이너**에 padding 을 줘야 웹뷰가 실제로 줄어든다.
       ⚠ 위(상태바)는 안 자른다 — 시계 그림이 상태바 뒤로 흐르는 건 의도된 디자인이다. */
    private int lastBottomPx = -1;
    private void applyBottomInset(int bottomPx) {
        if (bottomPx == lastBottomPx) return;
        final WebView web = getBridge() == null ? null : getBridge().getWebView();
        if (web == null) return;
        /* ⚠ 부모 padding 도 안 먹었다(실측 innerHeight 그대로) — 웹뷰의 **레이아웃 마진**으로 자른다.
           마진은 측정 단계에서 빠지므로 웹뷰가 반드시 줄어든다. */
        android.view.ViewGroup.LayoutParams lp0 = web.getLayoutParams();
        if (!(lp0 instanceof android.view.ViewGroup.MarginLayoutParams)) return;
        android.view.ViewGroup.MarginLayoutParams lp = (android.view.ViewGroup.MarginLayoutParams) lp0;
        lp.bottomMargin = bottomPx;
        web.setLayoutParams(lp);
        if (web.getParent() instanceof View) ((View) web.getParent()).setBackgroundColor(0xFFF2F3F6);
        android.util.Log.d("아이서랍인셋", "bottomMargin=" + bottomPx);
        lastBottomPx = bottomPx;
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
        /* 🔴 2026-08-11 — 되풀이를 늘렸다. 에뮬 3대 중 **2대에서 값이 아예 안 들어갔다**
           (`--sa-top` 이 빈 값 → 머리가 상태바 밑으로 들어감). 4번으로는 모자랐다.
           위쪽은 CSS 에 바닥값 24px 이 있어 최악을 막지만, **아래쪽은 바닥값을 못 깐다**
           (제스처 폰은 0 이 정답) — 그래서 아래를 살리려면 이 다리가 반드시 닿아야 한다.
           같은 값을 여러 번 넣는 건 부작용이 없다. 한 번만 넣는 쪽이 훨씬 위험하다. */
        for (int delay : new int[] { 0, 150, 400, 900, 1800, 3000, 5000, 8000 }) {
            web.postDelayed(() -> {
                WindowInsetsCompat wi = ViewCompat.getRootWindowInsets(web);
                if (wi == null) return;
                Insets bars = wi.getInsets(WindowInsetsCompat.Type.systemBars());
                float d = getResources().getDisplayMetrics().density;
                if (d <= 0) d = 1f;
                int top = Math.round(bars.top / d);
                applyBottomInset(bars.bottom);   // 웹뷰를 내비바 위에서 끊는다(px 단위)
                /* 아래는 0 — 웹뷰가 이미 잘려 있으므로 웹이 또 비우면 이중이 된다 */
                String js =
                    "document.documentElement.style.setProperty('--sa-top','" + top + "px');" +
                    "document.documentElement.style.setProperty('--sa-bottom','0px');";
                web.evaluateJavascript(js, null);
            }, delay);
        }
    }

    /** 접기·펴기·회전 — 폴더블은 여기서 인셋이 통째로 바뀐다(폴드6 내부/외부 화면) */
    @Override
    public void onConfigurationChanged(android.content.res.Configuration cfg) {
        super.onConfigurationChanged(cfg);
        final WebView web = getBridge() == null ? null : getBridge().getWebView();
        if (web != null) ViewCompat.requestApplyInsets(web);
        pushSafeArea();
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
