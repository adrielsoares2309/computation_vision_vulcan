"""Ícones SVG vetoriais consistentes para interface industrial (compatíveis offline)."""

from __future__ import annotations

ICONS: dict[str, str] = {
    "speed": '<path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 14l4-5"/><path d="M6 18h12"/>',
    "visibility": '<path d="M2.5 12s3.2-6 9.5-6 9.5 6 9.5 6-3.2 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.7"/>',
    "factory": '<path d="M3 21V9l6 3V8l6 4V5h4v16H3Z"/><path d="M7 17h2m3 0h2m3 0h1"/>',
    "refresh": '<path d="M20 7v5h-5"/><path d="M4.5 10a7.5 7.5 0 0 1 13-3L20 12M4 17v-5h5"/><path d="M19.5 14a7.5 7.5 0 0 1-13 3L4 12"/>',
    "verified": '<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/>',
    "check_circle": '<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/>',
    "cancel": '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6m0-6 6 6"/>',
    "error": '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6m0-6 6 6"/>',
    "indeterminate": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    "sensors": '<path d="M5 8a10 10 0 0 0 0 8m14-8a10 10 0 0 1 0 8M8 10a5 5 0 0 0 0 4m8-4a5 5 0 0 1 0 4"/><circle cx="12" cy="12" r="1.4"/>',
    "warning": '<path d="M12 3 2.8 19h18.4L12 3Z"/><path d="M12 9v4m0 3h.01"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "box": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3"/>',
}


def svg_icon(name: str, color: str = "currentColor", size: int = 20) -> str:
    """Retorna um SVG inline compacto com atributo aria-label acessível."""
    paths = ICONS.get(name, ICONS["verified"])
    return (
        f'<svg class="vt-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'role="img" aria-label="{name}">{paths}</svg>'
    )
