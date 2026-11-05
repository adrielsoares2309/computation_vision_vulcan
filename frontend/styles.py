"""Camada centralizada de Design Tokens, identidade visual industrial (AeroMotion / MES / SCADA) e auditoria WCAG 2.2."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from frontend.components.icons import svg_icon

PLOTLY_TEMPLATE = "plotly_white"

# Design Tokens centralizados — Paleta Industrial de Alto Contraste (WCAG 2.2 AA/AAA)
# Baseada na arquitetura visual AeroMotion Dynamics (Fundo branco/claro + Azul-escuro industrial)
DESIGN_TOKENS: dict[str, Any] = {
    "colors": {
        # Superfícies principais (Fundo claro e limpo)
        "bg_app": "#F7F9FC",
        "bg_surface": "#FFFFFF",
        "bg_surface_alt": "#F8FAFC",
        "bg_sidebar": "#FFFFFF",
        "bg_sidebar_hover": "#F0F4F8",
        "bg_sidebar_active": "#0B4F9F",
        "bg_sidebar_active_pale": "#E3F0FF",
        "bg_sidebar_active_border": "#B9D7FB",
        # Textos sobre superfícies claras
        "text_primary": "#102A43",      # 14.81:1 sobre #FFFFFF
        "text_secondary": "#183B56",    # 11.45:1 sobre #FFFFFF
        "text_muted": "#334E68",        # 8.46:1 sobre #FFFFFF
        # Textos sobre sidebar clara (#FFFFFF)
        "sidebar_text": "#102A43",      # 14.81:1 sobre #FFFFFF | 13.34:1 sobre #F0F4F8
        "sidebar_muted": "#334E68",     # 8.46:1 sobre #FFFFFF
        "sidebar_section": "#183B56",   # 11.45:1 sobre #FFFFFF
        "sidebar_border": "#DCE4EE",
        # Botões e interações
        "primary": "#0B4F9F",           # 8.32:1 com texto #FFFFFF
        "primary_hover": "#083B7A",     # 10.89:1 com texto #FFFFFF
        "primary_text": "#FFFFFF",
        "secondary_bg": "#FFFFFF",
        "secondary_hover_bg": "#EFF6FF",
        "secondary_text": "#102A43",
        "secondary_border": "#64748B",  # 4.76:1 sobre #FFFFFF
        "disabled_bg": "#E2E8F0",
        "disabled_text": "#475569",     # 5.74:1 sobre #E2E8F0
        "focus_ring": "#1565C0",        # 5.75:1 sobre #FFFFFF
        # Bordas e divisores
        "border": "#D9E2EC",
        "border_strong": "#94A3B8",
        # Estados semânticos (Texto/Ícone escuro sobre fundo pastel de alto contraste)
        "success_text": "#065F46",      # 7.53:1 sobre #ECFDF5
        "success_bg": "#ECFDF5",
        "success_border": "#059669",
        "warning_text": "#78350F",      # 8.44:1 sobre #FFFBEB
        "warning_bg": "#FFFBEB",
        "warning_border": "#D97706",
        "danger_text": "#991B1B",       # 7.73:1 sobre #FEF2F2
        "danger_bg": "#FEF2F2",
        "danger_border": "#DC2626",
        "neutral_text": "#334155",      # 9.16:1 sobre #F1F5F9
        "neutral_bg": "#F1F5F9",
        "neutral_border": "#64748B",
        "info_text": "#1E3A8A",         # 8.92:1 sobre #EFF6FF
        "info_bg": "#EFF6FF",
        "info_border": "#2563EB",
        # Paleta de gráficos (distinta e com contraste >= 3:1 sobre fundo branco)
        "chart_blue": "#0B4F9F",        # 8.32:1
        "chart_teal": "#0F766E",        # 5.44:1
        "chart_amber": "#B45309",       # 5.02:1
        "chart_red": "#B91C1C",         # 6.47:1
        "chart_slate": "#334155",       # 10.21:1
        "chart_purple": "#6D28D9",      # 6.53:1
    },
    "typography": {
        "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "font_mono": "'JetBrains Mono', 'Consolas', monospace",
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
    },
    "radius": {
        "sm": "4px",
        "md": "6px",
    },
}

# Alias de compatibilidade (VulcanTech + AeroMotion)
COLORS: dict[str, str] = {
    "primary": DESIGN_TOKENS["colors"]["primary"],
    "blue_primary": "#1565C0",
    "blue_hover": "#0D47A1",
    "blue_pale": "#E3F0FF",
    "blue_border": "#B9D7FB",
    "navy": "#102A43",
    "mid_blue": DESIGN_TOKENS["colors"]["chart_teal"],
    "light_blue": DESIGN_TOKENS["colors"]["info_bg"],
    "text": DESIGN_TOKENS["colors"]["text_primary"],
    "text_title": "#102A43",
    "text_primary": "#102A43",
    "text_heading": "#183B56",
    "text_body": "#334E68",
    "text_secondary": "#475569",
    "muted": DESIGN_TOKENS["colors"]["text_muted"],
    "subtle": DESIGN_TOKENS["colors"]["text_secondary"],
    "border": DESIGN_TOKENS["colors"]["border"],
    "border_sidebar": "#DCE4EE",
    "border_light": "#EDF2F7",
    "surface": DESIGN_TOKENS["colors"]["bg_surface_alt"],
    "bg_page": "#F7F9FC",
    "bg_card": "#FFFFFF",
    "bg_sidebar": "#FFFFFF",
    "bg_hover": "#F0F4F8",
    "sidebar": DESIGN_TOKENS["colors"]["bg_sidebar"],
    "green": DESIGN_TOKENS["colors"]["success_text"],
    "green_bg": "#ECFDF5",
    "green_border": "#A7F3D0",
    "red": DESIGN_TOKENS["colors"]["danger_text"],
    "red_bg": "#FEF2F2",
    "red_border": "#FECACA",
    "yellow": DESIGN_TOKENS["colors"]["warning_text"],
    "yellow_bg": "#FFFBEB",
    "yellow_border": "#FDE68A",
    "orange": "#E65100",
    "purple": "#6A1B9A",
    "teal": "#00796B",
}


def relative_luminance(hex_color: str) -> float:
    """Calcula a luminância relativa WCAG 2.2 de uma cor hexadecimal (#RRGGBB)."""
    clean = hex_color.lstrip("#")
    if len(clean) == 3:
        clean = "".join(ch * 2 for ch in clean)
    r, g, b = (int(clean[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def _channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(hex_fg: str, hex_bg: str) -> float:
    """Calcula a razão de contraste WCAG 2.2 entre primeiro plano e fundo."""
    l1 = relative_luminance(hex_fg)
    l2 = relative_luminance(hex_bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def verify_all_token_contrasts() -> list[dict[str, Any]]:
    """Audita sistematicamente os pares de cores da interface segundo a norma WCAG 2.2."""
    c = DESIGN_TOKENS["colors"]
    pairs = [
        ("Texto principal sobre superfície (#FFFFFF)", c["text_primary"], c["bg_surface"], 4.5),
        ("Texto principal sobre fundo do app (#F7F9FC)", c["text_primary"], c["bg_app"], 4.5),
        ("Texto secundário sobre superfície (#FFFFFF)", c["text_secondary"], c["bg_surface"], 4.5),
        ("Texto secundário sobre painel (#F8FAFC)", c["text_secondary"], c["bg_surface_alt"], 4.5),
        ("Rótulos/captions (muted) sobre superfície (#FFFFFF)", c["text_muted"], c["bg_surface"], 4.5),
        ("Rótulos/captions (muted) sobre painel (#F8FAFC)", c["text_muted"], c["bg_surface_alt"], 4.5),
        ("Rótulos/captions (muted) sobre fundo (#F7F9FC)", c["text_muted"], c["bg_app"], 4.5),
        ("Sidebar: texto principal sobre fundo (#FFFFFF)", c["sidebar_text"], c["bg_sidebar"], 4.5),
        ("Sidebar: texto secundário sobre fundo (#FFFFFF)", c["sidebar_muted"], c["bg_sidebar"], 4.5),
        ("Sidebar: título de seção sobre fundo (#FFFFFF)", c["sidebar_section"], c["bg_sidebar"], 4.5),
        ("Sidebar: item selecionado (#FFFFFF sobre #0B4F9F)", "#FFFFFF", c["bg_sidebar_active"], 4.5),
        ("Sidebar: item em hover (#102A43 sobre #F0F4F8)", c["sidebar_text"], c["bg_sidebar_hover"], 4.5),
        ("Botão primário normal (#FFFFFF sobre #0B4F9F)", c["primary_text"], c["primary"], 4.5),
        ("Botão primário hover (#FFFFFF sobre #083B7A)", c["primary_text"], c["primary_hover"], 4.5),
        ("Botão secundário normal (#102A43 sobre #FFFFFF)", c["secondary_text"], c["secondary_bg"], 4.5),
        ("Botão secundário hover (#102A43 sobre #EFF6FF)", c["secondary_text"], c["secondary_hover_bg"], 4.5),
        ("Botão desabilitado (#475569 sobre #E2E8F0)", c["disabled_text"], c["disabled_bg"], 4.5),
        ("Badge Sucesso/APROVADA (#065F46 sobre #ECFDF5)", c["success_text"], c["success_bg"], 4.5),
        ("Badge Atenção/ALERTA (#78350F sobre #FFFBEB)", c["warning_text"], c["warning_bg"], 4.5),
        ("Badge Erro/REPROVADA (#991B1B sobre #FEF2F2)", c["danger_text"], c["danger_bg"], 4.5),
        ("Badge Neutro/INDETERMINADA (#334155 sobre #F1F5F9)", c["neutral_text"], c["neutral_bg"], 4.5),
        ("Badge Info/SIMULADO (#1E3A8A sobre #EFF6FF)", c["info_text"], c["info_bg"], 4.5),
        ("Gráfico: série azul (#0B4F9F sobre #FFFFFF)", c["chart_blue"], c["bg_surface"], 3.0),
        ("Gráfico: série teal (#0F766E sobre #FFFFFF)", c["chart_teal"], c["bg_surface"], 3.0),
        ("Gráfico: série âmbar (#B45309 sobre #FFFFFF)", c["chart_amber"], c["bg_surface"], 3.0),
        ("Gráfico: série vermelha (#B91C1C sobre #FFFFFF)", c["chart_red"], c["bg_surface"], 3.0),
        ("Indicador de foco (#1565C0 sobre #FFFFFF)", c["focus_ring"], c["bg_surface"], 3.0),
    ]
    results = []
    for label, fg, bg, min_req in pairs:
        ratio = contrast_ratio(fg, bg)
        results.append(
            {
                "pair": label,
                "foreground": fg,
                "background": bg,
                "ratio": ratio,
                "min_required": min_req,
                "passed": ratio >= min_req,
            }
        )
    return results


def render_status_badge(
    text: str,
    tone: str = "neutral",
    icon: str | None = None,
) -> str:
    """Gera HTML de um badge semântico acessível (com ícone + texto e contraste >= 7:1)."""
    tone_map = {
        "success": ("vt-badge-success", icon or "check_circle", DESIGN_TOKENS["colors"]["success_text"]),
        "warning": ("vt-badge-warning", icon or "warning", DESIGN_TOKENS["colors"]["warning_text"]),
        "danger": ("vt-badge-danger", icon or "cancel", DESIGN_TOKENS["colors"]["danger_text"]),
        "info": ("vt-badge-info", icon or "sensors", DESIGN_TOKENS["colors"]["info_text"]),
        "neutral": ("vt-badge-neutral", icon or "indeterminate", DESIGN_TOKENS["colors"]["neutral_text"]),
    }
    cls_name, resolved_icon, icon_color = tone_map.get(tone, tone_map["neutral"])
    icon_html = svg_icon(resolved_icon, icon_color, 14)
    return f'<span class="vt-badge {cls_name}">{icon_html}<span>{escape(text)}</span></span>'


def inject_css() -> str:
    """Retorna a string CSS institucional (padrão AeroMotion + VulcanTech MES)."""
    c = DESIGN_TOKENS["colors"]
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

    :root {{
        --vt-bg-app: {c["bg_app"]};
        --vt-bg-surface: {c["bg_surface"]};
        --vt-bg-surface-alt: {c["bg_surface_alt"]};
        --vt-bg-sidebar: {c["bg_sidebar"]};
        --vt-sidebar-text: {c["sidebar_text"]};
        --vt-sidebar-muted: {c["sidebar_muted"]};
        --vt-sidebar-section: {c["sidebar_section"]};
        --vt-sidebar-border: {c["sidebar_border"]};
        --vt-sidebar-hover: {c["bg_sidebar_hover"]};
        --vt-sidebar-active: {c["bg_sidebar_active"]};
        --vt-text-primary: {c["text_primary"]};
        --vt-text-secondary: {c["text_secondary"]};
        --vt-text-muted: {c["text_muted"]};
        --vt-primary: {c["primary"]};
        --vt-primary-hover: {c["primary_hover"]};
        --vt-border: {c["border"]};
        --vt-border-strong: {c["border_strong"]};
        --vt-focus: {c["focus_ring"]};
        --vt-success-text: {c["success_text"]};
        --vt-success-bg: {c["success_bg"]};
        --vt-success-border: {c["success_border"]};
        --vt-warning-text: {c["warning_text"]};
        --vt-warning-bg: {c["warning_bg"]};
        --vt-warning-border: {c["warning_border"]};
        --vt-danger-text: {c["danger_text"]};
        --vt-danger-bg: {c["danger_bg"]};
        --vt-danger-border: {c["danger_border"]};
        --vt-neutral-text: {c["neutral_text"]};
        --vt-neutral-bg: {c["neutral_bg"]};
        --vt-neutral-border: {c["neutral_border"]};
        --vt-info-text: {c["info_text"]};
        --vt-info-bg: {c["info_bg"]};
        --vt-info-border: {c["info_border"]};
    }}

    /* Aplicação geral estilo AeroMotion / MES / SCADA */
    html, body, [class*="css"], .stApp {{
        background-color: var(--vt-bg-app) !important;
        color: var(--vt-text-primary);
        font-family: {DESIGN_TOKENS["typography"]["font_sans"]} !important;
    }}
    [data-testid="stHeader"] {{
        background: transparent !important;
    }}
    #MainMenu, footer {{
        visibility: hidden;
    }}
    /* Oculta completamente a lista automática de arquivos pages/ do Streamlit */
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavSeparator"],
    ul[data-testid="stSidebarNavItems"] {{
        display: none !important;
        height: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    .block-container {{
        max-width: 100%;
        padding: 0.85rem 1.4rem 1.8rem 1.4rem;
    }}

    /* Tipografia compacta e objetiva */
    h1, h2, h3, h4 {{
        color: var(--vt-text-primary);
        letter-spacing: -0.015em;
        margin-bottom: 0.35rem;
    }}
    h1 {{ font-size: 1.35rem; font-weight: 700; }}
    h2 {{ font-size: 1.05rem; font-weight: 600; }}
    h3 {{ font-size: 0.92rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--vt-text-secondary); }}
    p, .stCaption, [data-testid="stCaptionContainer"] {{
        color: var(--vt-text-muted);
        font-size: 0.80rem;
    }}

    /* ── Barra Lateral (Sidebar) Padrão AeroMotion (Fundo #FFFFFF, Texto #102A43) ── */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebarHeader"] {{
        background-color: #FFFFFF !important;
        color: #102A43 !important;
    }}
    section[data-testid="stSidebar"] {{
        border-right: 1px solid #DCE4EE !important;
    }}
    section[data-testid="stSidebar"][aria-expanded="true"] {{
        min-width: 280px !important;
        max-width: 315px !important;
    }}
    [data-testid="stSidebarContent"] {{
        padding: 0.75rem 0.95rem 1.25rem 0.95rem !important;
    }}

    /* Botões de recolher/expandir a sidebar sempre visíveis e com alto contraste */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stExpandSidebarButton"] {{
        color: #102A43 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #D9E2EC !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover,
    [data-testid="stExpandSidebarButton"]:hover {{
        color: #1565C0 !important;
        background-color: #E3F0FF !important;
        border-color: #B9D7FB !important;
    }}
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stExpandSidebarButton"] svg {{
        fill: currentColor !important;
        stroke: currentColor !important;
    }}

    /* Rótulos e textos da Sidebar */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stNumberInput label {{
        font-size: 0.80rem !important;
        font-weight: 600 !important;
        color: #183B56 !important;
        margin-bottom: 0.2rem !important;
    }}

    /* Controles de Navegação Nativa (stRadio na sidebar — Padrão AeroMotion) */
    section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {{
        gap: 0.28rem !important;
        width: 100% !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
        background: #FFFFFF !important;
        border: 1px solid #D9E2EC !important;
        border-radius: 6px !important;
        padding: 0.48rem 0.75rem !important;
        margin-bottom: 0.15rem !important;
        transition: all 0.15s ease-in-out !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        background: #F0F4F8 !important;
        border-color: #B9D7FB !important;
    }}
    /* Item ativo da navegação: fundo azul-claro (#E3F0FF), texto azul-escuro (#102A43), borda esquerda azul (#1565C0) */
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background: #E3F0FF !important;
        border-color: #B9D7FB !important;
        border-left: 4px solid #1565C0 !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {{
        color: #102A43 !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label p {{
        font-size: 0.83rem !important;
        color: #334E68 !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }}

    /* Marca e seções da Sidebar (AeroMotion + VulcanTech) */
    .sidebar-brand, .vt-logo {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 2px 4px 10px 4px;
        border-bottom: 1px solid #DCE4EE;
        margin-bottom: 8px;
    }}
    .vt-logo-mark {{ width: 34px; height: 34px; flex: none; }}
    .sidebar-brand-title, .vt-logo-name {{
        color: #102A43 !important;
        font-weight: 700;
        font-size: 1.0rem;
        line-height: 1.1;
        letter-spacing: -0.01em;
    }}
    .vt-logo-sub {{
        color: #475569 !important;
        font-size: 0.64rem;
        font-weight: 600;
        letter-spacing: 0.10em;
        margin-top: 2px;
    }}
    .sidebar-section-title, .vt-sidebar-section {{
        display: flex;
        align-items: center;
        gap: 0.4rem;
        color: #183B56 !important;
        font-size: 0.70rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 12px 2px 6px 2px;
        padding-bottom: 4px;
        border-bottom: 1px solid #EDF2F7;
    }}
    .vt-sidebar-foot {{
        border-top: 1px solid #DCE4EE;
        margin-top: 12px;
        padding: 10px 6px 4px 6px;
        background: #F8FAFC;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
        color: #334E68 !important;
        font-size: 0.74rem;
        line-height: 1.7;
    }}
    .vt-sidebar-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 2px 4px;
    }}
    .vt-sidebar-key {{
        color: #334E68 !important;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .vt-sidebar-val {{
        color: #102A43 !important;
        font-family: {DESIGN_TOKENS["typography"]["font_mono"]};
        font-size: 0.71rem;
        font-weight: 700;
    }}

    /* Botões de Regime e Status na Sidebar (Padrão AeroMotion) */
    .regime-icon-row {{
        display: flex;
        justify-content: center;
        margin: 0.1rem 0 0.25rem 0;
    }}
    .regime-icon-box {{
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: #F7F9FC;
        border: 1px solid #D9E2EC;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .regime-icon-box.active {{
        background: #E3F0FF;
        border-color: #B9D7FB;
    }}
    .regime-active-note {{
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-top: 0.4rem;
        padding: 0.42rem 0.65rem;
        border-radius: 6px;
        background: #E3F0FF;
        border: 1px solid #B9D7FB;
        font-size: 0.75rem;
        font-weight: 600;
        color: #102A43 !important;
    }}
    .sim-status-box {{
        background: #FFFFFF;
        border: 1px solid #D9E2EC;
        border-radius: 6px;
        padding: 0.45rem 0.7rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        margin-top: 0.45rem;
    }}
    .sim-status-box.active {{
        background: #ECFDF5;
        border-color: #A7F3D0;
        color: #065F46 !important;
    }}
    .sim-status-box.idle {{
        background: #F8FAFC;
        border-color: #D9E2EC;
        color: #475569 !important;
    }}

    /* Cabeçalho Operacional Compacto (Topbar do Módulo) */
    .vt-header-bar {{
        background: var(--vt-bg-surface);
        border: 1px solid var(--vt-border);
        border-left: 4px solid var(--vt-primary);
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }}
    .vt-header-main {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .vt-page-title {{
        color: var(--vt-text-primary);
        font-size: 1.15rem;
        font-weight: 700;
        line-height: 1.2;
        margin: 0;
    }}
    .vt-page-subtitle {{
        color: var(--vt-text-secondary);
        font-size: 0.80rem;
        margin-top: 2px;
    }}
    .vt-header-meta {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        font-size: 0.75rem;
        color: var(--vt-text-muted);
    }}

    /* KPIs Industriais de Alta Densidade */
    .vt-kpi {{
        background: var(--vt-bg-surface);
        border: 1px solid var(--vt-border);
        border-top: 3px solid var(--vt-primary);
        border-radius: 6px;
        padding: 10px 12px;
        min-height: 86px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .vt-kpi.vt-kpi-success {{ border-top-color: var(--vt-success-border); }}
    .vt-kpi.vt-kpi-warning {{ border-top-color: var(--vt-warning-border); }}
    .vt-kpi.vt-kpi-danger {{ border-top-color: var(--vt-danger-border); }}
    .vt-kpi.vt-kpi-neutral {{ border-top-color: var(--vt-neutral-border); }}
    .vt-kpi-label {{
        color: var(--vt-text-secondary);
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
    }}
    .vt-kpi-value {{
        color: var(--vt-text-primary);
        font-family: {DESIGN_TOKENS["typography"]["font_mono"]};
        font-size: 1.32rem;
        font-weight: 700;
        line-height: 1.15;
        margin: 6px 0 4px 0;
    }}
    .vt-kpi-note {{
        color: var(--vt-text-muted);
        font-size: 0.71rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    /* Painéis, Tabelas e Badges Semânticos */
    .vt-panel {{
        background: var(--vt-bg-surface);
        border: 1px solid var(--vt-border);
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }}
    .vt-panel-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--vt-border);
        padding-bottom: 8px;
        margin-bottom: 10px;
        font-size: 0.84rem;
        font-weight: 600;
        color: var(--vt-text-primary);
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .vt-badge {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 0.73rem;
        font-weight: 600;
        line-height: 1.2;
        border: 1px solid transparent;
    }}
    .vt-badge-success {{
        background-color: var(--vt-success-bg);
        color: var(--vt-success-text);
        border-color: var(--vt-success-border);
    }}
    .vt-badge-warning {{
        background-color: var(--vt-warning-bg);
        color: var(--vt-warning-text);
        border-color: var(--vt-warning-border);
    }}
    .vt-badge-danger {{
        background-color: var(--vt-danger-bg);
        color: var(--vt-danger-text);
        border-color: var(--vt-danger-border);
    }}
    .vt-badge-neutral {{
        background-color: var(--vt-neutral-bg);
        color: var(--vt-neutral-text);
        border-color: var(--vt-neutral-border);
    }}
    .vt-badge-info {{
        background-color: var(--vt-info-bg);
        color: var(--vt-info-text);
        border-color: var(--vt-info-border);
    }}
    .vt-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        flex: none;
    }}

    /* Botões com Contraste Garantido em Todos os Estados */
    div[data-testid="stButton"] > button {{
        border-radius: 6px;
        border: 1px solid {c["secondary_border"]};
        background-color: {c["secondary_bg"]};
        color: {c["secondary_text"]} !important;
        font-weight: 600;
        font-size: 0.80rem;
        padding: 0.36rem 0.65rem;
        min-height: 2.1rem;
        transition: background-color 0.12s ease, border-color 0.12s ease;
    }}
    div[data-testid="stButton"] > button:hover:not(:disabled) {{
        background-color: {c["secondary_hover_bg"]};
        border-color: var(--vt-primary);
        color: {c["secondary_text"]} !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"],
    button[data-testid="baseButton-primary"] {{
        background-color: var(--vt-primary) !important;
        border-color: var(--vt-primary) !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"] *,
    button[data-testid="baseButton-primary"] * {{
        color: #FFFFFF !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled),
    button[data-testid="baseButton-primary"]:hover:not(:disabled) {{
        background-color: var(--vt-primary-hover) !important;
        border-color: var(--vt-primary-hover) !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stButton"] > button:focus-visible {{
        outline: 2px solid var(--vt-focus) !important;
        outline-offset: 2px !important;
    }}
    div[data-testid="stButton"] > button:disabled {{
        background-color: {c["disabled_bg"]} !important;
        border-color: var(--vt-border) !important;
        color: {c["disabled_text"]} !important;
        opacity: 1 !important;
    }}

    /* Campos de formulário e filtros compactos */
    div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border-color: #D9E2EC !important;
        border-radius: 6px !important;
        color: #102A43 !important;
        font-size: 0.82rem !important;
    }}
    [data-testid="stDataFrame"] {{
        border: 1px solid var(--vt-border);
        border-radius: 5px;
        background: var(--vt-bg-surface);
    }}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 1px solid var(--vt-border);
    }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--vt-text-secondary);
        padding: 6px 14px;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        color: var(--vt-primary) !important;
    }}
    [data-testid="stExpander"] {{
        background: var(--vt-bg-surface);
        border: 1px solid var(--vt-border);
        border-radius: 5px;
    }}

    /* Grade de Estado de Equipamentos (MES Matrix) */
    .vt-equip-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 10px;
    }}
    .vt-equip-card {{
        background: var(--vt-bg-surface);
        border: 1px solid var(--vt-border);
        border-radius: 6px;
        padding: 10px 12px;
    }}
    .vt-equip-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }}
    .vt-equip-id {{
        font-family: {DESIGN_TOKENS["typography"]["font_mono"]};
        font-weight: 700;
        font-size: 0.90rem;
        color: var(--vt-text-primary);
    }}
    .vt-equip-meta {{
        font-size: 0.74rem;
        color: var(--vt-text-secondary);
        line-height: 1.45;
    }}

    @media (max-width: 980px) {{
        .vt-equip-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .block-container {{ padding: 0.6rem 0.8rem 1.5rem 0.8rem; }}
    }}
    </style>
    """


def apply_styles() -> None:
    """Injeta a folha de estilos industrial (AeroMotion / MES / SCADA) baseada em DESIGN_TOKENS."""
    st.markdown(inject_css(), unsafe_allow_html=True)
