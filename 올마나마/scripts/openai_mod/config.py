# -*- coding: utf-8 -*-
# OpenAI 공통 설정 — 키는 코드에 절대 박지 않는다 (2026-07-20)
#
# 🔴 키 조달 순서: ① 환경변수 OPENAI_API_KEY  ② 같은 폴더/상위의 .env 파일
#    .env는 .gitignore에 넣는다. (레시피파이프라인 지시서 §1)
#    2026-07-20 채팅에 평문 노출된 키가 있었으므로 그 키는 폐기하고 새 키를 쓸 것.
import os

_ENV_CACHE = None


def _load_dotenv():
    """가장 가까운 .env를 한 번만 읽어 dict로. python-dotenv 의존 없이 최소 파싱."""
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    _ENV_CACHE = {}
    here = os.path.dirname(os.path.abspath(__file__))
    # 이 폴더 → 상위 2단계까지 .env 탐색(프로젝트로 복사해 써도 찾히게)
    for d in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        p = os.path.join(d, ".env")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                _ENV_CACHE.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break
    return _ENV_CACHE


def get(name, default=None):
    return os.environ.get(name) or _load_dotenv().get(name) or default


def api_key():
    k = get("OPENAI_API_KEY")
    if not k:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다.\n"
            "  방법 1) PowerShell:  setx OPENAI_API_KEY \"sk-...\"   (새 창부터 적용)\n"
            "  방법 2) 이 폴더에 .env 파일 생성 후:  OPENAI_API_KEY=sk-...\n"
            "  ※ .env는 .gitignore에 등록할 것")
    return k


# 모델 — 지시서는 텍스트에 'GPT-5.6 Terra'를 지정했다.
#  ⚠️ 이 모델명이 계정에서 실제 호출 가능한지는 list_models()로 확인해야 한다(모델 카탈로그는
#     수시로 바뀌고, 잘못된 이름을 박아두면 런타임에서야 404가 난다). 그래서 env로 덮어쓰게 둔다.
TEXT_MODEL = get("OPENAI_TEXT_MODEL", "gpt-5.6-terra")
IMAGE_MODEL = get("OPENAI_IMAGE_MODEL", "gpt-image-1")

# 레시피는 분량 정확도가 생명 → 창의성 낮게 (지시서 §2)
TEMPERATURE = float(get("OPENAI_TEMPERATURE", "0.35"))
MAX_TOKENS = int(get("OPENAI_MAX_TOKENS", "2500"))
TIMEOUT = int(get("OPENAI_TIMEOUT", "180"))
