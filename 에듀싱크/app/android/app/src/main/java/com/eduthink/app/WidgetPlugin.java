package com.eduthink.app;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.content.SharedPreferences;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * 앱(JS) → 바탕화면 위젯 데이터 통로 (2026-07-27)
 *
 * 위젯은 웹뷰와 다른 프로세스라 localStorage 를 못 읽는다.
 * 그래서 앱이 화면을 그릴 때 여기로 값을 넘겨 SharedPreferences 에 적어 두고,
 * 위젯(SchoolWidget)이 그걸 읽는다.
 *
 * @capacitor/preferences 를 쓰지 않고 직접 만든 이유:
 *  · 그 플러그인은 «CapacitorStorage» 라는 공용 저장소에 앱 값과 섞여 들어간다
 *  · 값을 쓴 뒤 **위젯을 즉시 갱신**하려면 어차피 네이티브 브로드캐스트가 필요하다
 *    (안드로이드 자동 갱신 주기는 최소 30분이라 «방금 넣은 준비물»이 안 보인다)
 * 두 가지를 한 곳에서 해결하려고 40줄짜리 플러그인 하나를 둔다.
 */
@CapacitorPlugin(name = "SchoolWidget")
public class WidgetPlugin extends Plugin {

    @PluginMethod
    public void update(PluginCall call) {
        Context ctx = getContext();
        SharedPreferences.Editor e = ctx
                .getSharedPreferences(SchoolWidget.PREFS, Context.MODE_PRIVATE).edit();

        // 넘어온 값만 덮어쓴다 — 한 줄만 바뀌었는데 나머지를 빈 값으로 지우면 안 된다.
        put(e, call, "child", SchoolWidget.K_CHILD);
        put(e, call, "date", SchoolWidget.K_DATE);
        // rows 는 줄 목록 JSON 문자열. 종류가 늘어도 여기는 안 고친다 —
        // «무엇을 보여줄지»는 앱이 정하고 위젯은 받은 대로 그린다.
        put(e, call, "rows", SchoolWidget.K_ROWS);
        e.apply();

        SchoolWidget.refreshAll(ctx);

        JSObject ret = new JSObject();
        ret.put("ok", true);
        call.resolve(ret);
    }

    /**
     * 위젯에서 체크한 준비물 id 들을 앱이 받아간다. **받아가면 비운다** —
     * 안 비우면 앱을 열 때마다 같은 항목을 다시 뒤집어 켜졌다 꺼졌다 한다.
     */
    @PluginMethod
    public void takePending(PluginCall call) {
        Context ctx = getContext();
        SharedPreferences sp = ctx.getSharedPreferences(SchoolWidget.PREFS, Context.MODE_PRIVATE);
        String raw = sp.getString(SchoolWidget.K_PENDING, "[]");
        sp.edit().putString(SchoolWidget.K_PENDING, "[]").apply();
        JSObject ret = new JSObject();
        ret.put("ids", raw);
        call.resolve(ret);
    }

    /**
     * 바깥 브라우저로 열기 (2026-07-27).
     * @capacitor/browser 는 «앱 안 탭»이라 사용자가 기대하는 기본 브라우저가 아니다.
     * 안드로이드에 그냥 넘겨서 사용자가 정해 둔 브라우저가 열리게 한다.
     * http/https 만 통과시킨다 — 다른 스킴을 그대로 넘기면 아무 앱이나 열리는 통로가 된다.
     */
    @PluginMethod
    public void openUrl(PluginCall call) {
        String url = call.getString("url");
        if (url == null || !(url.startsWith("http://") || url.startsWith("https://"))) {
            call.reject("http/https 주소만 열 수 있어요");
            return;
        }
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
            call.resolve();
        } catch (Exception e) {
            call.reject("브라우저를 열지 못했어요");
        }
    }

    private void put(SharedPreferences.Editor e, PluginCall call, String from, String key) {
        String v = call.getString(from);
        if (v != null) e.putString(key, v);
    }
}
