package com.eduthink.app;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 위젯 데이터 통로. registerPlugin 은 super.onCreate 앞에서 불러야 브리지에 실린다.
        registerPlugin(WidgetPlugin.class);
        super.onCreate(savedInstanceState);
        handleWidget(getIntent());
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
