"""
Small encryption helper for sensitive settings stored in the database.
"""
import base64
import hashlib
from typing import Optional

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


_FERNET = None


def _get_fernet() -> Fernet:
    global _FERNET
    if _FERNET is None:
        secret = (settings.SECRET_KEY or '').encode('utf-8')
        digest = hashlib.sha256(secret + b':system_settings').digest()
        key = base64.urlsafe_b64encode(digest)
        _FERNET = Fernet(key)
    return _FERNET


def encrypt_value(value: str) -> str:
    fernet = _get_fernet()
    token = fernet.encrypt(value.encode('utf-8'))
    return token.decode('utf-8')


def decrypt_value(token: str) -> Optional[str]:
    fernet = _get_fernet()
    try:
        value = fernet.decrypt(token.encode('utf-8'))
        return value.decode('utf-8')
    except InvalidToken:
        return None
