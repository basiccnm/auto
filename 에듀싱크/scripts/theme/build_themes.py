# -*- coding: utf-8 -*-
"""테마 배경 18장 → app/www/themes/theme_01~18.webp + 색 토큰 CSS 생성.

  ① 크롭본(1080×2160)을 webp 로 줄인다 — APK 용량이 곧 설치 이탈이다
  ② **그림 하단 단색**에서 배경색을 뽑는다(지시: «그림 하단 추출 = 배경»)
  ③ 밝기로 라이트/다크를 가른다 — 밤 그림은 라이트에서도 어두우면 카드가 종이처럼 뜬다
     (2026-08-03 night 세트에서 겪은 그 문제) → 라이트용은 밝은 파생을 따로 만든다
"""
import glob, os, io, statistics, colorsys
from PIL import Image

SRC = r"G:\내 드라이브\에듀싱크-검수\테마\크롭"
DST = r"C:\Users\hardb\Desktop\블로그수입관련\에듀싱크\app\www\themes"
os.makedirs(DST, exist_ok=True)

def lum(c):
    f = lambda v: (v/255)/12.92 if v/255 <= 0.04045 else (((v/255)+0.055)/1.055)**2.4
    return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2])

def hexs(c): return "#%02X%02X%02X" % tuple(int(max(0, min(255, v))) for v in c)

def mix(a, b, t):   # a→b 를 t 만큼
    return [a[i]*(1-t) + b[i]*t for i in range(3)]

files = sorted(glob.glob(os.path.join(SRC, "*.png")))
rows, total = [], 0
for i, p in enumerate(files, 1):
    im = Image.open(p).convert("RGB")
    W, H = im.size
    px = im.load()
    # 하단 단색 — 맨 아래 12% 에서 중앙값
    vals = [px[x, y] for y in range(int(H*0.88), H, 6) for x in range(0, W, 12)]
    base = [int(statistics.median(v[k] for v in vals)) for k in range(3)]
    L = lum(base)
    dark = L < 0.22                                   # 어두운 그림인가
    name = f"theme_{i:02d}"
    out = os.path.join(DST, name + ".webp")
    im.save(out, "WEBP", quality=72, method=6)
    sz = os.path.getsize(out); total += sz

    # ── 면 3단계 — 배경 < 카드 < (진하게) 드로어. **전부 같은 색조(H)** ──
    # ⚠ 예전엔 배경에 회색(#7C8CA3)을 섞었다. 그러면 색조가 회색 쪽으로 밀려
    #   벚꽃(H351)이 배경에서 H291(보라)로 갔다 — 드로어와 계열이 어긋난다.
    #   이제 H 는 그림에서 그대로 받고 **밝기(L)만** 셋으로 나눈다. 채도는 단계마다 조절.
    # ⚠ 목표는 «상대휘도»다. HSL 의 L 과 다른 값이라 L 을 이진 탐색해 맞춘다.
    import colorsys as _cs
    # ⚠ 상한(SAT_CAP)은 **배경·카드에도 똑같이** 건다(2026-08-03 3차).
    #   드로어만 60 으로 조이면 다크에서 배경 S 0.84 > 드로어 0.59 로 뒤집혀
    #   «배경이 더 쨍하고 드로어가 죽은» 그림이 된다. 셋 다 같은 상한이라야 계열이 산다.
    #   목표가 «상대휘도»라 채도를 깎아도 면 대비는 그대로다(L 을 다시 이진탐색하므로).
    SAT_CAP = 0.585
    def at_lum(c, target, sat_scale=1.0, sat_add=0.0):
        h0, l0, s0 = _cs.rgb_to_hls(*[v/255 for v in c])
        deg = h0 * 360
        if deg >= 348 or deg <= 12: h0 = 338 / 360      # 빨강은 «확인해 주세요» 전용(§3)
        s1 = max(0.0, min(SAT_CAP, s0 * sat_scale + sat_add))
        lo, hi = 0.0, 1.0
        for _ in range(26):
            mid = (lo + hi) / 2
            if lum([v*255 for v in _cs.hls_to_rgb(h0, mid, s1)]) < target: lo = mid
            else: hi = mid
        return [v*255 for v in _cs.hls_to_rgb(h0, (lo+hi)/2, s1)]

    surf_l = at_lum(base, 0.600, sat_scale=0.55)    # 라이트 배경
    # ⚠ 채도를 0.30 으로 깎았더니 **카드가 흰 종이처럼** 보였다(배경 S=40 인데 카드 S=23).
    #   «흰 카드 말고 바탕색 계열로»(2026-08-04 지시) → 채도를 배경 가까이 올린다.
    #   at_lum 은 목표 «상대휘도»를 이진탐색하므로, 채도를 올리면 L 이 알아서 내려가
    #   **면 대비(1.30~1.55)는 그대로 유지된다.**
    # ⚠ 0.865 는 «거의 흰색»이다 — 카드가 테마와 무관한 **흰 종이**로 보였다.
    #   «흰 카드 말고 테마색보다 1~2톤 진하게»(2026-08-04 지시) →
    #   배경(0.600)보다 **아래로** 내린다. 면 대비는 그대로 1.35~1.45 로 관리된다.
    # ⚠ 채도 0.78 은 **카드가 테마색을 진하게 물어** 그림과 색이 경쟁했다.
    #   «회색 계열로 어울리게»(2026-08-04 지시) → 밝기는 그대로 두고 **색기만 뺀다**.
    #   색이 완전히 빠지면 테마와 무관한 회색이 되므로 0.20 은 남긴다.
    # ⚠ 0.20 까지 깎았더니 **18개가 전부 무채색으로 수렴해 테마 구분이 사라졌다**
    #   (2026-08-04 «왜 카드색이 다 똑같냐»). 회색 쪽으로 «눌러» 두되 색은 남겨야 한다.
    #   0.45 = 서재는 갈색빛, 벚꽃은 분홍빛이 분명히 보이면서도 그림과 안 싸우는 지점.
    card_l = at_lum(base, 0.435, sat_scale=0.45)    # 라이트 카드 — 테마색 그대로, 1~2톤 진하게
    surf_d = at_lum(base, 0.030, sat_scale=0.85)    # 다크 배경
    card_d = at_lum(base, 0.062, sat_scale=0.50)    # 다크 카드 — 같은 기준
    # 포인트 — 그림 색상(hue)을 살리되 대비가 나오게 채도·명도를 고정
    h, s0, v0 = colorsys.rgb_to_hsv(*[c/255 for c in base])
    acc_l = [c*255 for c in colorsys.hsv_to_rgb(h, 0.74, 0.44)]   # 0.55 는 작은 글씨에서 3.86:1
    acc_d = [c*255 for c in colorsys.hsv_to_rgb(h, 0.44, 0.98)]   # 카드가 밝아져 0.92 는 3.8:1 이었다
    # ── 드로어 — «짙은 잉크로 그 색을 우려낸» 톤 (2026-08-03 3차 지시) ──
    # ⚠ 채도를 1.0 까지 올렸더니 **경고색**이 됐다(벚꽃 #B9001D = 사실상 빨강, 라벤더 = 형광).
    #   기준으로 삼은 것: 밤 마을·눈 오두막·별 산맥·등대·바다 요트 — 깊고 차분하되 색이 산다.
    #   규칙: **S 는 60% 를 넘지 않는다. L 은 22~32% 안에 둔다.**
    # ⚠ **빨강(H 350~10 + 고채도)은 「확인해 주세요」 신호 전용**이다.
    #   면(드로어·배경·카드)에 그 범위가 나오면 안 된다 → 분홍(H 338)으로 민다.
    RED_LO, RED_HI, PINK = 348, 12, 338 / 360
    def safe_hue(h):
        deg = h * 360
        if deg >= RED_LO or deg <= RED_HI: return PINK
        return h
    # ⚠ 상한을 0.60 으로 두면 **8비트 hex 로 굳는 순간 60.5 로 올라간다**(반올림).
    #   지시가 «60 초과 금지» 라 상한 자체를 0.585 로 낮춰 굳은 뒤에도 60 아래에 있게 한다.
    def ink(c, l_hi=0.32, l_lo=0.22, sat_cap=0.585, sat_add=0.20, need=4.5):
        h0, l0, s0 = _cs.rgb_to_hls(*[v/255 for v in c])
        h1 = safe_hue(h0)
        s1 = min(sat_cap, s0 + sat_add)
        # 밝은 쪽(l_hi)부터 내려가며 **흰 글씨와 프로필 카드**가 둘 다 4.5:1 을 넘는 첫 값을 쓴다.
        # 범위를 다 내려가도 안 되면 더 내린다 — 읽히는 것이 톤보다 먼저다.
        L = l_hi
        while L > 0.06:
            rgb = [v*255 for v in _cs.hls_to_rgb(h1, L, s1)]
            prof = [255*0.10 + rgb[i]*0.90 for i in range(3)]   # .hv3-drwho = 흰색 10% 오버레이
            r1 = (max(lum([255,255,255]), lum(rgb)) + 0.05) / (min(lum([255,255,255]), lum(rgb)) + 0.05)
            r2 = (max(lum([255,255,255]), lum(prof)) + 0.05) / (min(lum([255,255,255]), lum(prof)) + 0.05)
            if r1 >= need and r2 >= need and L <= l_hi: return rgb
            L -= 0.004
        return [v*255 for v in _cs.hls_to_rgb(h1, l_lo, s1)]
    # ── 톤 예외 (2026-08-03 4차 지시) ──────────────────────────────────
    # ⚠ 대비 검사만으로는 **톤이 안 맞는다.** 보라 계열은 명도가 낮아 L=32 에서 곧바로
    #   4.5:1 을 넘겨 버려 상한에 그대로 머물고, 노랑·연두는 대비를 맞추느라 28~29 까지 내려간다.
    #   그래서 규칙 안에 있어도 **라벤더만 혼자 쨍하게** 도드라졌다.
    #   → 눈으로 확인해 어긋난 테마만 명도를 따로 지정한다. **채도·색조는 건드리지 않는다.**
    #   숨은 보정이 아니라 표로 드러내 둔다 — 나중에 다시 볼 때 이유가 남아야 한다.
    TONE_L = {"theme_17": 0.23}          # 라벤더 들판 — 등대·밤 마을과 진하기를 맞춘다
    drawer_l = ink(base, l_hi=TONE_L.get(name, 0.32))
    drawer_d = ink(base, l_hi=min(0.26, TONE_L.get(name, 0.26)), l_lo=0.18)
    rows.append(dict(key=name, base=hexs(base), dark=dark, sz=sz,
                     drawer_l=hexs(drawer_l), drawer_d=hexs(drawer_d),
                     surf_l=hexs(surf_l), card_l=hexs(card_l), acc_l=hexs(acc_l),
                     surf_d=hexs(surf_d), card_d=hexs(card_d), acc_d=hexs(acc_d),
                     ink_l="#1A1A1F", ink_d="#EEF1F5"))
    print(f"  {name}  하단={hexs(base)}  {'어두움' if dark else '밝음'}  {sz/1024:6.0f}KB")

print(f"\n18장 총합 {total/1024/1024:.2f}MB  (장당 평균 {total/len(rows)/1024:.0f}KB)")
io.open("theme_tokens.json", "w", encoding="utf-8").write(__import__("json").dumps(rows, ensure_ascii=False, indent=1))
