package com.eduthink.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.view.View;
import android.widget.RemoteViews;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * 바탕화면 위젯 (2026-07-27)
 *
 * 왜 만드는가: 학부모가 하루에 앱을 몇 번이나 열겠나. 「오늘 급식·시간표·일정·내일 준비물」은
 * 앱을 안 열고 봐야 값어치가 있다.
 *
 * 무엇을 보여줄지는 **사용자가 고른다**(앱의 홈 편집 → 바탕화면 위젯).
 * 그래서 이 클래스는 «급식»·«시간표» 같은 종류를 하나도 모른다 —
 * 앱이 만들어 보낸 줄 목록(JSON)을 그대로 그릴 뿐이다.
 * 종류가 늘어도 여기는 안 고친다. 아이가 둘이면 보고 싶은 것도 다르다.
 *
 * 데이터 통로: 위젯은 웹뷰와 **다른 프로세스**라 localStorage 를 못 읽는다.
 * 앱이 WidgetPlugin.update() 로 SharedPreferences 에 써 두고 여기서 읽는다.
 */
public class SchoolWidget extends AppWidgetProvider {

    /** 앱(JS)과 위젯이 같이 보는 저장소 이름. WidgetPlugin 과 반드시 같아야 한다. */
    public static final String PREFS = "eduthink_widget";

    public static final String K_CHILD = "child";
    public static final String K_DATE = "date";
    /** 줄 목록 JSON: [{"icon":"🍚","text":"…","go":"#school/meal","check":"12"}, …] 최대 6개
     *  check 가 있으면 «준비물 한 개»다 — 누르면 앱을 여는 대신 그 자리에서 체크된다. */
    public static final String K_ROWS = "rows";
    /** 위젯에서 체크했지만 아직 앱이 못 받아간 준비물 id 들(JSON 배열). */
    public static final String K_PENDING = "pending";

    /** 위젯에서 준비물을 눌렀을 때 자기 자신에게 쏘는 방송. */
    public static final String ACTION_TOGGLE = "com.eduthink.app.TOGGLE_SUPPLY";
    public static final String EXTRA_SID = "sid";

    private static final int[] ROW = { R.id.w_row1, R.id.w_row2, R.id.w_row3, R.id.w_row4, R.id.w_row5, R.id.w_row6 };
    private static final int[] ICO = { R.id.w_ico1, R.id.w_ico2, R.id.w_ico3, R.id.w_ico4, R.id.w_ico5, R.id.w_ico6 };
    private static final int[] TXT = { R.id.w_txt1, R.id.w_txt2, R.id.w_txt3, R.id.w_txt4, R.id.w_txt5, R.id.w_txt6 };

    @Override
    public void onUpdate(Context context, AppWidgetManager mgr, int[] ids) {
        for (int id : ids) render(context, mgr, id);
    }

    /**
     * 준비물 줄을 눌렀을 때 (2026-07-27 「위젯에서 체크되게」).
     *
     * 여기서 서버까지 보내지 않는다 — 방송 수신기는 몇 초 안에 죽는 자리라
     * 네트워크를 태우면 조용히 실패하기 딱 좋다. 대신 **눌렀다는 사실만** 적어 두고
     * 화면을 즉시 ✅ 로 바꾼다. 앱이 다음에 열릴 때 그걸 받아가 서버까지 반영한다.
     * 사용자 입장에선 «눌렀더니 체크됐다»로 끝난다.
     */
    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (intent == null || !ACTION_TOGGLE.equals(intent.getAction())) return;
        String sid = intent.getStringExtra(EXTRA_SID);
        if (sid == null || sid.isEmpty()) return;

        SharedPreferences p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        JSONArray pending = new JSONArray();
        try { pending = new JSONArray(p.getString(K_PENDING, "[]")); } catch (Exception ignored) {}

        // 이미 눌렀던 것을 또 누르면 취소한다 — 잘못 누르고 앱을 열 때까지 못 되돌리면 안 된다.
        JSONArray next = new JSONArray();
        boolean had = false;
        for (int i = 0; i < pending.length(); i++) {
            String v = pending.optString(i, "");
            if (sid.equals(v)) { had = true; continue; }
            next.put(v);
        }
        if (!had) next.put(sid);

        p.edit().putString(K_PENDING, next.toString()).apply();
        refreshAll(context);
    }

    /** 앱에서 값이 바뀌면 WidgetPlugin 이 부른다 — 안드로이드 자동 갱신(최소 30분)을 기다리지 않는다. */
    public static void refreshAll(Context context) {
        AppWidgetManager mgr = AppWidgetManager.getInstance(context);
        int[] ids = mgr.getAppWidgetIds(new ComponentName(context, SchoolWidget.class));
        for (int id : ids) render(context, mgr, id);
    }

    private static void render(Context context, AppWidgetManager mgr, int widgetId) {
        SharedPreferences p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        RemoteViews v = new RemoteViews(context.getPackageName(), R.layout.widget_school);

        v.setTextViewText(R.id.w_child, p.getString(K_CHILD, "우리아이학교정보"));
        v.setTextViewText(R.id.w_date, p.getString(K_DATE, ""));
        v.setOnClickPendingIntent(R.id.w_root, open(context, "#home", 0));

        JSONArray rows = null;
        try {
            rows = new JSONArray(p.getString(K_ROWS, "[]"));
        } catch (Exception ignored) { /* 값이 깨졌으면 «앱을 열어주세요»로 떨어진다 */ }

        JSONArray pendingIds = new JSONArray();
        try { pendingIds = new JSONArray(p.getString(K_PENDING, "[]")); } catch (Exception ignored) {}

        // 한 번도 안 채워졌을 때 — 빈 위젯은 고장으로 보인다. 무엇을 해야 하는지 알려준다.
        if (rows == null || rows.length() == 0) {
            v.setViewVisibility(ROW[0], View.VISIBLE);
            v.setTextViewText(ICO[0], "👋");
            v.setTextViewText(TXT[0], "앱을 한 번 열어주세요");
            for (int i = 1; i < ROW.length; i++) v.setViewVisibility(ROW[i], View.GONE);
            mgr.updateAppWidget(widgetId, v);
            return;
        }

        for (int i = 0; i < ROW.length; i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) {
                // 안 고른 줄은 감춘다. INVISIBLE 이면 자리를 그대로 먹어 위가 뜬다 — GONE 이어야 한다.
                v.setViewVisibility(ROW[i], View.GONE);
                continue;
            }
            v.setViewVisibility(ROW[i], View.VISIBLE);
            v.setTextViewText(TXT[i], row.optString("text", ""));

            String sid = row.optString("check", "");
            if (!sid.isEmpty()) {
                // 준비물 한 개 — 누르면 앱을 여는 대신 그 자리에서 체크된다.
                boolean checked = has(pendingIds, sid);
                v.setTextViewText(ICO[i], checked ? "✅" : "⬜");
                v.setOnClickPendingIntent(ROW[i], toggle(context, sid, 100 + i));
            } else {
                v.setTextViewText(ICO[i], row.optString("icon", ""));
                String go = row.optString("go", "#home");
                // requestCode 가 줄마다 달라야 한다 — 같으면 안드로이드가 PendingIntent 를 재사용해
                // 네 줄이 모두 첫 번째 화면으로 간다(흔한 함정).
                v.setOnClickPendingIntent(ROW[i], open(context, go, i + 1));
            }
        }

        mgr.updateAppWidget(widgetId, v);
    }

    private static boolean has(JSONArray arr, String v) {
        for (int i = 0; i < arr.length(); i++) if (v.equals(arr.optString(i, ""))) return true;
        return false;
    }

    /** 준비물 체크 — 앱을 열지 않고 자기 자신에게 방송을 쏜다. */
    private static PendingIntent toggle(Context context, String sid, int requestCode) {
        Intent i = new Intent(context, SchoolWidget.class);
        i.setAction(ACTION_TOGGLE);
        i.putExtra(EXTRA_SID, sid);
        i.setData(Uri.parse("eduthink://check/" + sid));   // 줄마다 다른 Intent 로 보이게
        return PendingIntent.getBroadcast(context, requestCode, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    /** 앱을 열면서 «어느 화면인지»를 같이 넘긴다. */
    private static PendingIntent open(Context context, String go, int requestCode) {
        Intent i = new Intent(context, MainActivity.class);
        i.setAction(Intent.ACTION_VIEW);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        i.putExtra("widget_go", go);
        // 같은 Intent 로 보이지 않게 데이터에도 넣는다(filterEquals 는 extras 를 안 본다)
        i.setData(Uri.parse("eduthink://widget/" + requestCode));
        return PendingIntent.getActivity(context, requestCode, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }
}
