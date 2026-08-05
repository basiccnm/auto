"""
phone_adapters.py — 휴대폰 인증 '발송 채널' 어댑터.

핵심 설계: 인증 로직(OTP 생성/검증)은 auth_core에 있고, 여기서는 '어떻게 코드를
사용자에게 전달하느냐'만 담당합니다. 나중에 결제용 본인인증(PASS/통신사 실명확인,
CI/DI 발급)이 필요해지면 아래 PhoneVerifier 인터페이스를 구현한 어댑터를 새로
추가하고 config에서 provider만 바꿔 끼우면 됩니다.

  provider = "dev"   -> 코드 발송 대신 응답/로그로 노출 (로컬 개발·테스트)
  provider = "sens"  -> 네이버 클라우드 SENS SMS (실서비스 예시, 키 필요)
  provider = "aligo" -> 알리고 SMS (실서비스 예시, 키 필요)
  provider = "nice"  -> [향후] NICE 본인인증. OTP가 아니라 CI/DI 반환 방식.
"""
from abc import ABC, abstractmethod


class PhoneVerifier(ABC):
    """SMS OTP 계열 어댑터 공통 인터페이스."""

    # 본인인증(CI/DI) 계열인지. True면 서버는 OTP 대신 리다이렉트 플로우를 탄다.
    is_identity_verification = False

    @abstractmethod
    def send_code(self, phone: str, code: str) -> dict:
        """인증번호(code)를 phone으로 발송. {ok: bool, ...} 반환."""
        raise NotImplementedError


class DevVerifier(PhoneVerifier):
    """개발용: 실제 발송 없이 코드를 콘솔에 찍고 응답으로도 돌려준다.
    운영에서는 절대 쓰지 말 것 (config.reveal_code=false로 강제)."""

    def send_code(self, phone: str, code: str) -> dict:
        print(f"[DEV-OTP] {phone} -> {code}")
        return {"ok": True, "dev_code": code}


class SensVerifier(PhoneVerifier):
    """네이버 클라우드 플랫폼 SENS SMS. 실제 운영용 예시 스텁.
    config: sens.access_key / sens.secret_key / sens.service_id / sens.from_number"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def send_code(self, phone: str, code: str) -> dict:
        import time, hmac, hashlib, base64, json
        try:
            import requests
        except ImportError:
            return {"ok": False, "error": "requests 미설치 (pip install requests)"}

        access_key = self.cfg["access_key"]
        secret_key = self.cfg["secret_key"]
        service_id = self.cfg["service_id"]
        from_number = self.cfg["from_number"].replace("+82", "0").replace("+", "")
        to = phone.replace("+82", "0")

        uri = f"/sms/v2/services/{service_id}/messages"
        url = "https://sens.apigw.ntruss.com" + uri
        ts = str(int(time.time() * 1000))
        msg = f"POST {uri}\n{ts}\n{access_key}"
        sig = base64.b64encode(
            hmac.new(secret_key.encode(), msg.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "x-ncp-apigw-timestamp": ts,
            "x-ncp-iam-access-key": access_key,
            "x-ncp-apigw-signature-v2": sig,
        }
        body = {
            "type": "SMS",
            "from": from_number,
            "content": f"[인증번호] {code} 를 입력해주세요.",
            "messages": [{"to": to}],
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            if r.status_code == 202:
                return {"ok": True}
            return {"ok": False, "error": f"SENS {r.status_code}: {r.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class AligoVerifier(PhoneVerifier):
    """알리고 SMS. 실제 운영용 예시 스텁.
    config: aligo.api_key / aligo.user_id / aligo.sender"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def send_code(self, phone: str, code: str) -> dict:
        try:
            import requests
        except ImportError:
            return {"ok": False, "error": "requests 미설치 (pip install requests)"}
        try:
            r = requests.post(
                "https://apis.aligo.in/send/",
                data={
                    "key": self.cfg["api_key"],
                    "user_id": self.cfg["user_id"],
                    "sender": self.cfg["sender"],
                    "receiver": phone.replace("+82", "0"),
                    "msg": f"[인증번호] {code} 를 입력해주세요.",
                },
                timeout=10,
            )
            data = r.json()
            if str(data.get("result_code")) == "1":
                return {"ok": True}
            return {"ok": False, "error": data.get("message", "알리고 발송 실패")}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------

def get_verifier(cfg: dict) -> PhoneVerifier:
    """config의 phone.provider 값에 따라 어댑터 인스턴스 반환."""
    phone_cfg = cfg.get("phone", {})
    provider = phone_cfg.get("provider", "dev")
    if provider == "dev":
        return DevVerifier()
    if provider == "sens":
        return SensVerifier(phone_cfg.get("sens", {}))
    if provider == "aligo":
        return AligoVerifier(phone_cfg.get("aligo", {}))
    raise ValueError(f"알 수 없는 phone.provider: {provider}")
