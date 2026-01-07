from datetime import datetime, timedelta, timezone
import hashlib
import uuid

import jwt
from django.conf import settings

from SaveNLoad.models.refresh_token import RefreshToken


def _utcnow():
    return datetime.now(timezone.utc)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])


def issue_access_token(user) -> str:
    now = _utcnow()
    exp = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)
    payload = {
        'sub': str(user.id),
        'role': user.role,
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'jti': str(uuid.uuid4())
    }
    return _encode(payload)


def issue_refresh_token(user, days: int, user_agent: str | None = None, ip_address: str | None = None) -> str:
    now = _utcnow()
    exp = now + timedelta(days=days)
    return issue_refresh_token_with_exp(user, exp, user_agent=user_agent, ip_address=ip_address)


def issue_refresh_token_with_exp(user, exp: datetime, user_agent: str | None = None, ip_address: str | None = None) -> str:
    now = _utcnow()
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    jti = uuid.uuid4()
    payload = {
        'sub': str(user.id),
        'type': 'refresh',
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'jti': str(jti)
    }
    ua_hash = hashlib.sha256((user_agent or '').encode('utf-8')).hexdigest()
    RefreshToken.objects.create(
        user=user,
        jti=jti,
        user_agent_hash=ua_hash,
        ip_address=ip_address,
        expires_at=exp
    )
    return _encode(payload)


def issue_reset_token(user, otp_id) -> str:
    now = _utcnow()
    exp = now + timedelta(minutes=settings.AUTH_RESET_TOKEN_MINUTES)
    payload = {
        'sub': str(user.id),
        'type': 'reset',
        'otp_id': str(otp_id),
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'jti': str(uuid.uuid4())
    }
    return _encode(payload)


def decode_token(token: str, expected_type: str) -> dict:
    payload = _decode(token)
    if payload.get('type') != expected_type:
        raise jwt.InvalidTokenError('Invalid token type')
    return payload


def revoke_refresh_token(jti: str, replaced_by: str | None = None) -> None:
    try:
        token = RefreshToken.objects.get(jti=jti)
        token.revoke(replaced_by=replaced_by)
    except RefreshToken.DoesNotExist:
        return


def find_active_refresh_token(jti: str) -> RefreshToken | None:
    try:
        token = RefreshToken.objects.get(jti=jti)
    except RefreshToken.DoesNotExist:
        return None
    return token if token.is_active() else None


def revoke_all_refresh_tokens(user_id: int) -> None:
    RefreshToken.objects.filter(user_id=user_id, revoked_at__isnull=True).update(revoked_at=_utcnow())
