import base64
import hashlib
import hmac

def hmac_sha256_base64url(
    text: str,
    secret: str,
    length_bytes: int = 12,
) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        text.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.urlsafe_b64encode(
        digest[:length_bytes]
    ).decode("utf-8").rstrip("=")