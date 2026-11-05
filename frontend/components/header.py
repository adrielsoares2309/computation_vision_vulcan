"""Cabeçalho operacional discreto estilo MES/SCADA."""

from __future__ import annotations

from html import escape
from typing import Callable

import streamlit as st

from frontend.components.icons import svg_icon
from frontend.styles import DESIGN_TOKENS, render_status_badge


def render_header(
    title: str,
    description: str,
    icon: str,
    last_update: str | None = None,
    refresh_callback: Callable[[], None] | None = None,
    context_badge: tuple[str, str] | None = None,
) -> None:
    """Renderiza barra superior compacta do módulo com contexto operacional e botão de atualização."""
    c = DESIGN_TOKENS["colors"]
    left, right = st.columns([6.2, 1.0], vertical_alignment="center")
    with left:
        update_label = f"Último registro: {escape(last_update[:19].replace('T', ' '))}" if last_update else "Sincronizado sob demanda"
        badge_html = ""
        if context_badge:
            badge_html = render_status_badge(context_badge[0], tone=context_badge[1])
        st.markdown(
            f'<div class="vt-header-bar">'
            f'<div class="vt-header-main">'
            f'{svg_icon(icon, c["primary"], 24)}'
            f'<div><div class="vt-page-title">{escape(title)}</div>'
            f'<div class="vt-page-subtitle">{escape(description)}</div></div>'
            f'</div>'
            f'<div class="vt-header-meta">{badge_html}<span>{update_label}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Atualizar", key=f"refresh-{icon}-{title}", width="stretch"):
            if refresh_callback:
                refresh_callback()
            st.rerun()
