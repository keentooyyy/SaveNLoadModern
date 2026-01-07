"""
System settings helpers for feature flags and integration config.
"""
from typing import Any, Dict, Tuple

from django.db import transaction

from SaveNLoad.models.system_setting import SystemSetting
from SaveNLoad.utils.crypto_utils import encrypt_value, decrypt_value


SETTINGS_SCHEMA: Dict[str, Tuple[type, Any]] = {
    'feature.rawg.enabled': (bool, False),
    'feature.email.enabled': (bool, False),
    'feature.email.registration_required': (bool, True),
    'feature.guest.enabled': (bool, False),
    'feature.guest.ttl_days': (int, 14),
    'rawg.api_key': (str, ''),
    'email.gmail_user': (str, ''),
    'email.gmail_app_password': (str, ''),
    'reset.default_password': (str, ''),
}

SENSITIVE_KEYS = {
    'rawg.api_key',
    'email.gmail_app_password',
    'reset.default_password',
}

MASKED_VALUE = '********'
ENCRYPTED_FIELD = '_enc'


def get_default_settings() -> Dict[str, Any]:
    return {key: default for key, (_, default) in SETTINGS_SCHEMA.items()}


def _coerce_value(expected_type: type, value: Any) -> Any:
    if value is None:
        return None
    if expected_type is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ('true', '1', 'yes', 'on'):
                return True
            if lowered in ('false', '0', 'no', 'off'):
                return False
        return bool(value)
    if expected_type is int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip() == '':
            return 0
        return int(value)
    if expected_type is str:
        return str(value)
    return value


def _normalize_sensitive_value(value: Any) -> Any:
    if isinstance(value, dict) and ENCRYPTED_FIELD in value:
        decrypted = decrypt_value(value.get(ENCRYPTED_FIELD, ''))
        return decrypted if decrypted is not None else ''
    return value


def _mask_sensitive_value(value: Any) -> Any:
    if value in (None, ''):
        return ''
    return MASKED_VALUE


def get_setting_value(key: str, default: Any = None, reveal_sensitive: bool = True) -> Any:
    try:
        setting = SystemSetting.objects.filter(key=key).first()
    except Exception:
        setting = None
    if setting is not None:
        value = setting.value
        if key in SENSITIVE_KEYS:
            normalized = _normalize_sensitive_value(value)
            return normalized if reveal_sensitive else _mask_sensitive_value(normalized)
        return value
    if key in SETTINGS_SCHEMA:
        return SETTINGS_SCHEMA[key][1]
    return default


def get_settings_values(keys=None, reveal_sensitive: bool = False) -> Dict[str, Any]:
    if keys is None:
        keys = list(SETTINGS_SCHEMA.keys())
    settings = {
        key: get_setting_value(
            key,
            SETTINGS_SCHEMA.get(key, (None, None))[1],
            reveal_sensitive=reveal_sensitive
        )
        for key in keys
    }
    return settings


def set_settings_values(values: Dict[str, Any], updated_by=None) -> Dict[str, Any]:
    updated = {}
    with transaction.atomic():
        for key, raw_value in values.items():
            if key not in SETTINGS_SCHEMA:
                continue
            if key in SENSITIVE_KEYS and raw_value == MASKED_VALUE:
                continue
            expected_type, default = SETTINGS_SCHEMA[key]
            coerced = _coerce_value(expected_type, raw_value)
            if coerced is None:
                coerced = default
            if key in SENSITIVE_KEYS:
                if coerced is None:
                    coerced = ''
                encrypted = {ENCRYPTED_FIELD: encrypt_value(str(coerced))}
                coerced = encrypted
            setting, _ = SystemSetting.objects.update_or_create(
                key=key,
                defaults={'value': coerced, 'updated_by': updated_by}
            )
            updated[key] = get_setting_value(key, reveal_sensitive=False)
    return updated


def is_feature_enabled(key: str) -> bool:
    value = get_setting_value(key, False)
    return bool(value)
