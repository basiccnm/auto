# 사진 → 카툰 배경 (2026-07-22)
#
# 🔴 왜 필요한가: 참고 채널(폴란드볼)은 그려진 배경 위에 볼을 얹는다.
#    사진을 그대로 깔면 ① 실사와 캐릭터가 따로 놀고 ② 자막·숫자가 묻힌다.
# 🔴 AI 이미지 생성이 아니라 **필터**다. 사진 구도는 그대로 남는다.
#    아이소메트릭 선화처럼 되지는 않는다. 그건 이미지 생성 모델이 있어야 한다.
# 🔴 배경은 **주인공이 아니다.** 채도를 죽이고 살짝 어둡게 해야 볼과 자막이 산다.
#
#   사용법:  python cartoonize.py in.jpg            → in_cartoon.png
#            python cartoonize.py 폴더              → 폴더 안 이미지 전부
#            python cartoonize.py in.jpg --strong   → 선 더 굵게, 색 더 뭉갬
import sys
from pathlib import Path

import cv2
import numpy as np

# 쇼츠 세로 규격. 배경은 이 크기로 잘라 둬야 Remotion에서 안 늘어난다
W, H = 1080, 1920

# 배경용 보정 — 🔴 이 세 값이 "배경답게" 만드는 핵심이다
SAT = 0.78      # 채도 (1.0=원본). 🔴 너무 낮추면 회갈색으로 탁해진다(2026-07-22)
BRIGHT = 1.10   # 밝기
GAMMA = 0.68    # 🔴 1보다 작으면 **어두운 부분만** 들어올린다. 매장 사진의 뭉갠 그림자를 살린다
EDGE_W = 2      # 윤곽선 굵기

# 🔴 홀 전체를 찍은 사진은 정보가 너무 많아 볼을 얹을 자리가 없다(2026-07-22).
#    아래쪽에 어두운 그라데이션을 깔아 **캐릭터·자막이 앉을 빈 자리**를 인위적으로 만든다.
#    실사 배경 쇼츠가 다 쓰는 방법이다.
VIGNETTE = 0.62   # 아래쪽을 얼마나 어둡게 (0=안 함, 1=새까맣게)
VIG_START = 0.34  # 화면 위에서 몇 %부터 어두워지기 시작할지


def fill_crop(img, w, h):
    """비율 유지하며 꽉 채우고 가운데를 자른다(레터박스 없음)."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    img = cv2.resize(img, (int(iw * s + 0.5), int(ih * s + 0.5)), interpolation=cv2.INTER_AREA)
    ih, iw = img.shape[:2]
    x, y = (iw - w) // 2, (ih - h) // 2
    return img[y:y + h, x:x + w]


def cartoonize(img, strong=False):
    img = fill_crop(img, W, H)

    # ⓪ 감마 — 색을 뭉개기 **전에** 어두운 부분을 들어올린다.
    #    뭉갠 뒤에 올리면 이미 하나로 합쳐진 검은 면이 통째로 회색이 된다.
    lut = np.array([((i / 255.0) ** GAMMA) * 255 for i in range(256)], dtype=np.uint8)
    img = cv2.LUT(img, lut)

    # ① 색 뭉개기 — bilateral을 여러 번 돌리면 면이 평평해진다(만화 채색 느낌)
    small = cv2.pyrDown(img)
    for _ in range(7 if strong else 5):
        small = cv2.bilateralFilter(small, 9, 60, 60)
    flat = cv2.pyrUp(small, dstsize=(img.shape[1], img.shape[0]))

    # ② 색 단계 줄이기 — 그라데이션을 없애 판판한 색면으로
    levels = 5 if strong else 7
    q = np.round(flat / (255 / levels)) * (255 / levels)
    flat = np.clip(q, 0, 255).astype(np.uint8)

    # ③ 윤곽선 — adaptiveThreshold가 연필선처럼 나온다
    # 🔴 타일·격자 같은 잔무늬에서 지직거리는 선이 잔뜩 나왔다(2026-07-22).
    #    blur를 키우고 blockSize를 키우면 큰 윤곽만 남고 잔선이 죽는다.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 11 if strong else 9)
    edge = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
        21 if strong else 17, 9,
    )
    # 점처럼 남은 잔선 제거 — 열림 연산
    edge = cv2.morphologyEx(edge, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if EDGE_W > 1:
        edge = cv2.erode(edge, np.ones((EDGE_W, EDGE_W), np.uint8))
    edge = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)

    out = cv2.bitwise_and(flat, edge)

    # ④ 배경으로 물러나게 — 채도↓ 밝기 보정
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= SAT
    hsv[..., 2] *= BRIGHT
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    # ⑤ 아래쪽 어둡게 — 캐릭터·자막이 앉을 자리를 비운다
    if VIGNETTE > 0:
        y = np.linspace(0, 1, H, dtype=np.float32)
        ramp = np.clip((y - VIG_START) / (1 - VIG_START), 0, 1) ** 1.5
        mask = (1 - ramp * VIGNETTE)[:, None, None]
        out = np.clip(out.astype(np.float32) * mask, 0, 255).astype(np.uint8)

    return out


def run(path, strong):
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print(f"못 읽음: {path}")
        return
    out = path.with_name(path.stem + "_cartoon.png")
    ok, buf = cv2.imencode(".png", cartoonize(img, strong))
    buf.tofile(str(out))
    print(f"완료: {out.name}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strong = "--strong" in sys.argv
    target = Path(args[0]) if args else Path(__file__).parent

    if target.is_dir():
        for f in sorted(target.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and "_cartoon" not in f.stem:
                run(f, strong)
    else:
        run(target, strong)
