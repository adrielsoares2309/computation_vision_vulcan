"""Componente de KPI compacto e acessível para painéis industriais MES/SCADA."""

from __future__ import annotations

from html import escape
import streamlit as st

from frontend.components.icons import svg_icon
from frontend.styles import DESIGN_TOKENS


def render_kpi(
    label: str,
    value: str,
    note: str = "",
    icon: str = "verified",
    tone: str = "primary",
) -> None:
    """Renderiza um cartão KPI denso com indicador cromático superior e ícone vetorial."""
    c = DESIGN_TOKENS["colors"]
    tone_cls = {
        "primary": "",
        "success": "vt-kpi-success",
        "warning": "vt-kpi-warning",
        "danger": "vt-kpi-danger",
        "neutral": "vt-kpi-neutral",
    }.get(tone, "")
    icon_color = {
        "primary": c["primary"],
        "success": c["success_text"],
        "warning": c["warning_text"],
        "danger": c["danger_text"],
        "neutral": c["text_secondary"],
    }.get(tone, c["primary"])

    st.markdown(
        f'<div class="vt-kpi {tone_cls}">'
        f'<div class="vt-kpi-label"><span>{escape(label)}</span>{svg_icon(icon, icon_color, 16)}</div>'
        f'<div class="vt-kpi-value">{escape(value)}</div>'
        f'<div class="vt-kpi-note" title="{escape(note)}">{escape(note)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
