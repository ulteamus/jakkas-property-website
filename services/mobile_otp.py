import base64
import os
from urllib import parse, request


def _is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _allow_dev_fallback():
    env = os.getenv("ALLOW_DEV_OTP_FALLBACK")
    if env is not None:
        return _is_truthy(env)
    return os.getenv("FLASK_ENV", "").strip().lower() != "production"


def _send_via_twilio(phone, code):
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not (sid and token and from_number):
        return {"ok": False, "message": "Twilio credentials are missing."}

    body = (
        f"Admin verification code: {code}. "
        "Valid for 10 minutes. Do not share this code."
    )
    payload = parse.urlencode(
        {
            "To": phone,
            "From": from_number,
            "Body": body,
        }
    ).encode("utf-8")
    auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("utf-8")
    req = request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(req, timeout=12) as resp:  # nosec B310
            if resp.status in (200, 201):
                return {"ok": True, "fallback": False, "message": "OTP sent by SMS.", "dev_code": None}
    except Exception as exc:
        return {"ok": False, "message": f"Twilio OTP failed: {exc}"}
    return {"ok": False, "message": "Twilio OTP failed with unknown response."}


def send_mobile_otp_code(phone, code, username):
    provider = (os.getenv("SMS_PROVIDER", "twilio").strip().lower() or "twilio")
    if provider == "twilio":
        result = _send_via_twilio(phone, code)
        if result.get("ok"):
            return result

    if _allow_dev_fallback():
        return {
            "ok": True,
            "fallback": True,
            "message": (
                "SMS provider unavailable. Development OTP fallback is active. "
                f"Use code {code} for {username}."
            ),
            "dev_code": code,
        }

    return {
        "ok": False,
        "fallback": False,
        "message": (
            "OTP delivery failed. Configure SMS credentials or enable "
            "ALLOW_DEV_OTP_FALLBACK for development."
        ),
        "dev_code": None,
    }
