import os
import hmac
import hashlib
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SECRET_KEY = os.getenv("SECRET_KEY", "depo-yonetimi-varsayilan-anahtar-lutfen-degistir")
TOKEN_GECERLILIK_SANIYE = 60 * 60 * 24 * 7  # 7 gün

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="depo-yonetimi-auth")


def sifre_hashle(sifre: str) -> str:
    tuz = secrets.token_hex(16)
    hash_degeri = hashlib.pbkdf2_hmac("sha256", sifre.encode(), bytes.fromhex(tuz), 200_000)
    return f"{tuz}${hash_degeri.hex()}"


def sifre_dogrula(sifre: str, hashlenmis: str) -> bool:
    try:
        tuz, hash_hex = hashlenmis.split("$")
    except ValueError:
        return False
    hesaplanan = hashlib.pbkdf2_hmac("sha256", sifre.encode(), bytes.fromhex(tuz), 200_000)
    return hmac.compare_digest(hesaplanan.hex(), hash_hex)


def token_olustur(kullanici_adi: str, rol: str) -> str:
    return _serializer.dumps({"kullanici_adi": kullanici_adi, "rol": rol})


def token_dogrula(token: str):
    """Token geçerliyse {'kullanici_adi':..., 'rol':...} döner, değilse None."""
    try:
        return _serializer.loads(token, max_age=TOKEN_GECERLILIK_SANIYE)
    except (BadSignature, SignatureExpired):
        return None
