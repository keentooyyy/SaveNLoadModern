import secrets

from SaveNLoad.utils.redis_client import get_redis_client

UI_WS_TOKEN_TTL_SECONDS = 120


def issue_ui_ws_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    redis_client = get_redis_client()
    redis_client.setex(f'ui_ws_token:{token}', UI_WS_TOKEN_TTL_SECONDS, str(user_id))
    return token


def validate_ui_ws_token(token: str) -> int | None:
    if not token:
        return None
    redis_client = get_redis_client()
    key = f'ui_ws_token:{token}'
    user_id = redis_client.get(key)
    if not user_id:
        return None
    # Single-use tokens to avoid replay on reconnects.
    redis_client.delete(key)
    try:
        if isinstance(user_id, bytes):
            user_id = user_id.decode('utf-8')
        return int(user_id)
    except (TypeError, ValueError):
        return None
