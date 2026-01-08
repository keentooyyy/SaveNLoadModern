import json
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()


def _load_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _collect_css(manifest: dict, entry_name: str, visited: set[str] | None = None) -> list[str]:
    if visited is None:
        visited = set()
    if entry_name in visited:
        return []
    visited.add(entry_name)

    entry = manifest.get(entry_name) or {}
    css_files = list(entry.get('css', []))
    for imported in entry.get('imports', []):
        css_files.extend(_collect_css(manifest, imported, visited))
    return css_files


@register.simple_tag
def vite_asset(path: str) -> str:
    dev_server = getattr(settings, 'VITE_DEV_SERVER', '')
    if settings.DEBUG and dev_server:
        return f"{dev_server.rstrip('/')}/{path.lstrip('/')}"
    base_url = getattr(settings, 'VITE_STATIC_URL', '/static/vite/')
    return static(f"{base_url.strip('/')}/{path.lstrip('/')}")


@register.simple_tag
def vite_entry(entry_name: str) -> str:
    dev_server = getattr(settings, 'VITE_DEV_SERVER', '')
    if settings.DEBUG and dev_server:
        script_tag = f'<script type="module" src="{dev_server.rstrip("/")}/{entry_name}"></script>'
        return mark_safe(script_tag)

    manifest_path = Path(getattr(settings, 'VITE_MANIFEST_PATH', ''))
    manifest = _load_manifest(manifest_path)
    entry = manifest.get(entry_name)
    if not entry:
        return ''

    tags = []
    file_name = entry.get('file')
    if file_name:
        src = static(f"{getattr(settings, 'VITE_STATIC_URL', '/static/vite/').strip('/')}/{file_name}")
        tags.append(f'<script type="module" src="{src}"></script>')

    for css_file in _collect_css(manifest, entry_name):
        href = static(f"{getattr(settings, 'VITE_STATIC_URL', '/static/vite/').strip('/')}/{css_file}")
        tags.append(f'<link rel="stylesheet" href="{href}">')

    return mark_safe('\n'.join(tags))
