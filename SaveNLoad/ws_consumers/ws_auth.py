from typing import Dict, Optional

from django.conf import settings

from django.apps import apps


def _parse_cookies(headers) -> Dict[str, str]:
    cookie_header = ''
    for name, value in headers or []:
        if name == b'cookie':
            cookie_header = value.decode('utf-8', errors='ignore')
            break

    cookies: Dict[str, str] = {}
    for part in cookie_header.split(';'):
        if '=' not in part:
            continue
        key, val = part.split('=', 1)
        cookies[key.strip()] = val.strip()
    return cookies


def get_ws_user(scope) -> Optional[object]:
    """
    Resolve the current user from WS scope cookies using JWT auth.

    Args:
        scope: Channels scope dict.

    Returns:
        SimpleUsers or None
    """
    cookies = _parse_cookies(scope.get('headers'))
    access_name = settings.AUTH_ACCESS_COOKIE_NAME
    refresh_name = settings.AUTH_REFRESH_COOKIE_NAME
    token = cookies.get(access_name)
    token_kind = 'access'
    if not token:
        token = cookies.get(refresh_name)
        token_kind = 'refresh'
    if not token:
        if settings.DEBUG:
            cookie_names = ','.join(sorted(cookies.keys()))
            print(f"WS auth failed: missing {access_name} cookie (cookies: {cookie_names})")
        return None
    try:
        from SaveNLoad.utils.jwt_utils import decode_token
        payload = decode_token(token, token_kind)
        user_id = int(payload.get('sub', 0))
    except Exception:
        return None
    if user_id <= 0:
        return None
    try:
        user_model = apps.get_model('SaveNLoad', 'SimpleUsers')
        return user_model.objects.get(id=user_id)
    except user_model.DoesNotExist:
        return None
