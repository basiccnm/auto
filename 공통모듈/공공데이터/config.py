# 얼마남아 B2B — 공공시세 연동 공통 설정
# 키는 전부 환경변수 오버라이드 가능. 기본값은 B2C에서 검증된 발급키.
import os
import ssl

# KAMIS (농림수산식품교육문화정보원 농산물유통정보) — 농축산물 도매/소매
KAMIS_CERT_KEY = os.environ.get("KAMIS_CERT_KEY", "638151fe-2bcd-45dc-90d4-60983e536c91")
KAMIS_CERT_ID = os.environ.get("KAMIS_CERT_ID", "dndmotor1@gmail.com")

# 축산물품질평가원(축평원) — 축산물 소비자가격 (data.go.kr 키)
EKAPE_KEY = os.environ.get(
    "EKAPE_KEY", "01d41ee31954bf8a99a618c1c206dd53aff2ce5fe2e53cec92fd3bd371e70dda"
)

# 참가격(한국소비자원) — 가공식품 소비자가격 (data.go.kr 키, EKAPE와 동일)
CHAMGA_KEY = os.environ.get("CHAMGA_KEY", EKAPE_KEY)

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
