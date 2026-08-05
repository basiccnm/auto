# -*- coding: utf-8 -*-
# OpenAI 클라이언트 공통 래퍼 (2026-07-20)
#  - 텍스트 생성 / 이미지 생성 / 모델 목록
#  - 재시도·백오프 포함(공공데이터 모듈의 http.py와 같은 방침)
#  - 키는 config.py가 env/.env에서만 읽는다. 코드에 박지 않는다.
#
# 사용법:
#   from openai_mod.client import complete, gen_images, list_models
#   txt = complete("시스템 프롬프트", "사용자 프롬프트")
#   paths = gen_images(["프롬프트1", "프롬프트2"], out_dir="images", prefix="chicken")
import base64
import os
import time

from openai import OpenAI

import config as _cfg   # 같은 폴더 복사 사용 전제(공공데이터 모듈과 동일 방식)

_client = None


def client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=_cfg.api_key(), timeout=_cfg.TIMEOUT)
    return _client


def list_models(prefix=None):
    """계정에서 실제 호출 가능한 모델 목록. 지시서의 모델명이 유효한지 확인용."""
    ms = sorted(m.id for m in client().models.list().data)
    return [m for m in ms if not prefix or m.startswith(prefix)]


def _retry(fn, tries=3, base=2.0, label=""):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            msg = str(e)
            # 재시도해도 소용없는 오류는 즉시 올린다(키 오류·모델명 오타·정책 위반)
            if any(w in msg for w in ("invalid_api_key", "401", "does not exist",
                                      "model_not_found", "content_policy")):
                raise
            if i < tries - 1:
                wait = base * (2 ** i)
                print(f"  [재시도 {i+1}/{tries-1}] {label} — {msg[:120]} ({wait:.0f}초 후)")
                time.sleep(wait)
    raise last


def complete(system, user, model=None, temperature=None, max_tokens=None):
    """텍스트 1회 생성 → 문자열.

    ⚠️ 모델별 파라미터 편차를 런타임에 흡수한다(2026-07-20 실측):
       - 신형 모델은 max_tokens를 거부하고 max_completion_tokens를 요구한다.
       - 일부 신형 모델은 temperature 커스텀을 아예 거부한다(기본값만 허용).
       모델 카탈로그가 자주 바뀌므로 이름으로 분기하지 않고, 400 응답을 보고 한 번씩 떨궈서 재시도한다.
    """
    model = model or _cfg.TEXT_MODEL
    kw = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": _cfg.TEMPERATURE if temperature is None else temperature,
        "max_completion_tokens": _cfg.MAX_TOKENS if max_tokens is None else max_tokens,
    }

    def _go():
        # 파라미터 거부(400)는 재시도가 아니라 '고쳐서 다시'가 정답이라 여기서 처리한다.
        for _ in range(3):
            try:
                r = client().chat.completions.create(**kw)
                return r.choices[0].message.content
            except Exception as e:
                m = str(e)
                if "unsupported_parameter" not in m and "Unsupported parameter" not in m \
                        and "unsupported_value" not in m:
                    raise
                if "max_completion_tokens" in m and "max_completion_tokens" in kw:
                    kw["max_tokens"] = kw.pop("max_completion_tokens")
                    print("  [적응] max_completion_tokens → max_tokens (구형 모델)")
                elif "max_tokens" in m and "max_tokens" in kw:
                    kw["max_completion_tokens"] = kw.pop("max_tokens")
                    print("  [적응] max_tokens → max_completion_tokens (신형 모델)")
                elif "temperature" in m and "temperature" in kw:
                    kw.pop("temperature")
                    print("  [적응] temperature 미지원 모델 → 기본값 사용")
                else:
                    raise
        raise RuntimeError("파라미터 적응 3회 실패")
    return _retry(_go, label=f"complete({model})")


def gen_images(prompts, out_dir, prefix, model=None, size="1024x1024"):
    """프롬프트 리스트 → 이미지 파일 경로 리스트. 한 장씩 생성(모델별 n 지원 편차 회피)."""
    model = model or _cfg.IMAGE_MODEL
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, p in enumerate(prompts, 1):
        def _go():
            return client().images.generate(model=model, prompt=p, size=size, n=1)
        r = _retry(_go, label=f"image {i}/{len(prompts)}")
        d = r.data[0]
        path = os.path.join(out_dir, f"{prefix}_{i}.png")
        if getattr(d, "b64_json", None):
            with open(path, "wb") as f:
                f.write(base64.b64decode(d.b64_json))
        else:   # url로 오는 모델 대응
            import urllib.request
            urllib.request.urlretrieve(d.url, path)
        paths.append(path)
        print(f"  이미지 {i}/{len(prompts)} 저장: {path}")
    return paths
