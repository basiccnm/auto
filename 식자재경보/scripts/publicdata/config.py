# 공공시세 연동 설정 (식자재경보 복사본)
#
# 🔴 **키를 코드에 적지 않는다** (2026-08-02, 깃허브에 올리기 직전에 잡음).
#    원본 공통모듈에는 발급키가 기본값으로 박혀 있었다. 로컬 전용일 땐 편했지만
#    이 폴더는 깃허브로 나간다. 비공개 저장소라도 키를 커밋하면 이력에 영영 남는다.
#    → `.env` 또는 환경변수에서만 읽는다. 없으면 그 API 는 그냥 안 쓰는 것으로 친다.
#
# 로컬:    .env 에 KAMIS_CERT_KEY / KAMIS_CERT_ID / EKAPE_KEY
# 액션:    저장소 Settings > Secrets 에 같은 이름으로
import os
import ssl


def _env(name, *, required=False):
    v = os.environ.get(name, "")
    if not v and required:
        raise RuntimeError(
            f"{name} 가 없다. .env 에 넣거나 환경변수로 주고 다시 실행할 것. "
            "키를 코드에 적지 말 것."
        )
    return v


def _load_dotenv():
    """프로젝트 루트의 .env 를 읽어 환경변수에 채운다. 이미 있는 값은 안 덮는다."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# KAMIS (농산물유통정보) — 농산물 도매/소매
KAMIS_CERT_KEY = _env("KAMIS_CERT_KEY")
KAMIS_CERT_ID = _env("KAMIS_CERT_ID")

# 축산물품질평가원 — 축산물 가격 (data.go.kr 키)
EKAPE_KEY = _env("EKAPE_KEY")

# 참가격(한국소비자원) — 가공식품 가격. data.go.kr 키라 축평원과 같은 값을 쓴다
CHAMGA_KEY = os.environ.get("CHAMGA_KEY") or EKAPE_KEY

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/
PROJECT_ROOT = os.path.dirname(_HERE)
DB_PATH = os.environ.get("EOLMANAMA_B2B_DB", os.path.join(PROJECT_ROOT, "data", "eolmanama_b2b.db"))
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "schema.sql")

HTTP_TIMEOUT = int(os.environ.get("PUBLICDATA_TIMEOUT", "30"))
USER_AGENT = "Mozilla/5.0"  # KAMIS는 UA 없으면 차단됨. 필수.

# 공공 API 다수가 인증서 체인이 불완전해 검증 비활성 (http 평문이라 어차피 동일 수준)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
