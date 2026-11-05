"""Barra lateral industrial (padrão AeroMotion Dynamics + VulcanTech MES) com navegação nativa st.radio, filtros globais, controle de regimes e telemetria real da API."""

from __future__ import annotations

from html import escape
import importlib.util
from pathlib import Path
import sys
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from frontend.components.icons import svg_icon
from frontend.services.api_client import fetch_system_status, get_api_client
from frontend.styles import COLORS, DESIGN_TOKENS

_ROOT_SIM_PATH = Path(__file__).resolve().parents[2] / "simulator.py"
if "root_simulator" in sys.modules:
    sim = sys.modules["root_simulator"]
else:
    _sim_spec = importlib.util.spec_from_file_location("root_simulator", _ROOT_SIM_PATH)
    sim = importlib.util.module_from_spec(_sim_spec)  # type: ignore[arg-type]
    sys.modules["root_simulator"] = sim
    if _sim_spec and _sim_spec.loader:
        _sim_spec.loader.exec_module(sim)

MENU_OPTIONS = [
    "Dashboard Geral",
    "Monitoramento em Tempo Real",
    "Manutenção Preditiva",
    "OEE e Eficiência Industrial",
    "Visão Computacional",
    "Análise de Dados (EDA)",
    "Modelos de IA",
    "Simulador Industrial",
    "Parecer Técnico",
]

MENU_ICONS = [
    "grid-1x2",
    "activity",
    "tools",
    "speedometer2",
    "camera",
    "bar-chart-line",
    "cpu",
    "play-circle",
    "shield-check",
]

CELL_OPTIONS = ["Todas as Células", "CEL-201", "CEL-202", "CEL-203", "CEL-204"]
ALLOY_OPTIONS = [
    "Todas as Ligas",
    "Aco_Carbono_316L",
    "Aluminio_7075",
    "Liga_Titanio_Ti6Al4V",
]

REGIME_BUTTONS = [
    ("Producao_Normal", "Normal", "Normal", "check_circle"),
    ("Usinagem_Pesada", "Pesada", "Misto", "activity"),
    ("Alta_Velocidade", "Crítica", "Degradado", "bolt"),
]


def _apply_regime_change(regime_key: str, api_mode: str, api_online: bool) -> None:
    """Atualiza o regime operacional no controle local do simulador e na API FastAPI."""
    try:
        sim.write_control(regime_key, action="run", requested_by="sidebar")
    except Exception:
        pass
    st.session_state["regime_selecionado"] = regime_key
    if api_online:
        try:
            client = get_api_client()
            client.post("/simulation/step", json={"mode": api_mode.upper(), "count": 4})
        except Exception:
            pass


def _trigger_simulator_action(action: str, regime_key: str, api_online: bool) -> None:
    """Aciona início, parada ou passo de simulação na API e no controle local."""
    mode_map = {
        "Producao_Normal": "NORMAL",
        "Usinagem_Pesada": "MISTO",
        "Alta_Velocidade": "DEGRADADO",
    }
    api_mode = mode_map.get(regime_key, "MISTO")
    try:
        sim.write_control(
            regime_key,
            action="stop" if action == "stop" else "run",
            requested_by="sidebar",
        )
    except Exception:
        pass

    if api_online:
        client = get_api_client()
        try:
            if action == "start":
                client.post(
                    "/simulation/start",
                    json={"mode": api_mode, "interval_seconds": 5.0, "batch_size": 4},
                )
                client.post("/simulation/step", json={"mode": api_mode, "count": 4})
            elif action == "stop":
                client.post("/simulation/stop", json={})
            elif action == "step":
                client.post("/simulation/step", json={"mode": api_mode, "count": 4})
        except Exception:
            pass


def render_sidebar(default_page: str | None = None) -> str:
    """Renderiza a barra lateral industrial completa (Navegação nativa, Filtros, Regimes, Simulador e Status)."""
    status: dict[str, Any] = fetch_system_status()
    api_online = bool(status.get("api_online"))
    db_info = status.get("database", {}) if api_online else {}
    db_online = bool(db_info.get("available"))
    sim_info = status.get("simulation", {}) if api_online else {}
    local_sim = sim.simulator_status()
    sim_running = bool(sim_info.get("running")) or bool(local_sim.get("simulador_online"))
    models_info = status.get("models", {}) if api_online else {}
    tab_ok = bool(models_info.get("tabular", {}).get("available"))
    vis_ok = bool(models_info.get("vision", {}).get("available"))
    version = str(status.get("version") or "1.0.0") if api_online else "OFFLINE"

    api_dot = "#059669" if api_online else "#DC2626"
    api_txt = "ONLINE" if api_online else "OFFLINE"
    db_dot = "#059669" if db_online else "#DC2626"
    db_txt = "SQLITE ATIVO" if db_online else "INDISPONÍVEL"
    sim_dot = "#059669" if sim_running else "#64748B"
    sim_txt = f"ATIVO ({sim_info.get('mode', 'MISTO')})" if sim_running else "PARADO"
    ia_dot = "#059669" if (tab_ok and vis_ok) else ("#D97706" if (tab_ok or vis_ok) else "#DC2626")
    ia_txt = "TABULAR + VISÃO" if (tab_ok and vis_ok) else ("PARCIAL" if (tab_ok or vis_ok) else "OFFLINE")

    # Sincronização de estado de navegação
    if default_page and default_page in MENU_OPTIONS and "vt_nav_menu" not in st.session_state:
        st.session_state["vt_nav_menu"] = default_page

    saved_selection = st.session_state.get("vt_nav_menu")
    default_idx = MENU_OPTIONS.index(saved_selection) if saved_selection in MENU_OPTIONS else 0

    with st.sidebar:
        # 1. Cabeçalho Institucional da Marca (AeroMotion + VulcanTech)
        st.markdown(
            '<div class="vt-logo">'
            '<svg class="vt-logo-mark" viewBox="0 0 48 48" role="img" aria-label="VulcanTech MES">'
            '<rect width="48" height="48" rx="8" fill="#1565C0"/>'
            '<path d="M10 13h7.5L24 27.5 30.5 13H38L26.5 36h-5L10 13Z" fill="#FFFFFF"/>'
            '</svg>'
            '<div><div class="vt-logo-name">VulcanTech MES</div>'
            '<div class="vt-logo-sub">SMART METALS S.A.</div></div></div>',
            unsafe_allow_html=True,
        )

        # 2. Seção de Navegação Nativa (100% responsiva e sem falhas de iframe)
        nav_icon = svg_icon("dashboard", COLORS["text_heading"], 14)
        st.markdown(
            f'<div class="sidebar-section-title">{nav_icon}<span>Módulos Operacionais</span></div>',
            unsafe_allow_html=True,
        )
        selected = st.radio(
            "Navegação do Sistema",
            options=MENU_OPTIONS,
            index=default_idx,
            key="vt_nav_radio",
            label_visibility="collapsed",
        )
        st.session_state["vt_nav_menu"] = selected

        # 3. Seção de Filtros Operacionais Globais (Célula e Liga Metálica)
        filter_icon = svg_icon("Precision_manufacturing", COLORS["text_heading"], 14)
        st.markdown(
            f'<div class="sidebar-section-title">{filter_icon}<span>Escopo Operacional</span></div>',
            unsafe_allow_html=True,
        )
        selected_cell = st.selectbox(
            "Célula Industrial",
            options=CELL_OPTIONS,
            index=0,
            key="sidebar_cell_select",
            help="Filtra ou destaca a célula de manufatura monitorada.",
        )
        st.session_state["selected_cell"] = None if selected_cell == "Todas as Células" else selected_cell

        selected_alloy = st.selectbox(
            "Liga Metálica",
            options=ALLOY_OPTIONS,
            index=0,
            key="sidebar_alloy_select",
            help="Filtra a liga metálica processada nas células CNC.",
        )
        st.session_state["selected_alloy"] = None if selected_alloy == "Todas as Ligas" else selected_alloy

        # 4. Seção de Regime de Operação (Padrão AeroMotion Dynamics)
        regime_icon = svg_icon("activity", COLORS["text_heading"], 14)
        st.markdown(
            f'<div class="sidebar-section-title">{regime_icon}<span>Regime de Operação</span></div>',
            unsafe_allow_html=True,
        )
        current_regime = st.session_state.get(
            "regime_selecionado",
            local_sim.get("regime_selecionado", sim.DEFAULT_REGIME),
        )
        if current_regime not in sim.REGIMES:
            current_regime = sim.DEFAULT_REGIME

        rcols = st.columns(3)
        clicked_regime: tuple[str, str] | None = None
        for col, (reg_key, short_label, api_mode, icon_name) in zip(rcols, REGIME_BUTTONS):
            is_active = reg_key == current_regime
            with col:
                icon_svg = svg_icon(
                    icon_name,
                    COLORS["blue_primary"] if is_active else COLORS["text_secondary"],
                    15,
                )
                st.markdown(
                    f'<div class="regime-icon-row"><div class="regime-icon-box{" active" if is_active else ""}">'
                    f"{icon_svg}</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    short_label,
                    key=f"btn_regime_{reg_key.lower()}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                    help=f"Seleciona o regime {sim.REGIME_LABELS.get(reg_key, reg_key)}",
                ):
                    clicked_regime = (reg_key, api_mode)

        if clicked_regime is not None:
            _apply_regime_change(clicked_regime[0], clicked_regime[1], api_online)
            st.rerun()

        active_regime_label = sim.REGIME_LABELS.get(current_regime, current_regime)
        check_svg = svg_icon("check_circle", COLORS["blue_primary"], 14)
        st.markdown(
            f'<div class="regime-active-note">{check_svg}<span>{escape(active_regime_label)}</span></div>',
            unsafe_allow_html=True,
        )

        # 5. Controle Rápido de Simulação e Sincronização
        sim_icon = svg_icon("sensors", COLORS["text_heading"], 14)
        st.markdown(
            f'<div class="sidebar-section-title">{sim_icon}<span>Simulação & Sincronia</span></div>',
            unsafe_allow_html=True,
        )
        scol1, scol2, scol3 = st.columns(3)
        if scol1.button(
            "Iniciar",
            key="sidebar_sim_start",
            type="primary",
            use_container_width=True,
            disabled=sim_running,
            help="Inicia a geração contínua de telemetria.",
        ):
            _trigger_simulator_action("start", current_regime, api_online)
            st.rerun()

        if scol2.button(
            "Parar",
            key="sidebar_sim_stop",
            type="secondary",
            use_container_width=True,
            disabled=not sim_running,
            help="Interrompe a simulação contínua.",
        ):
            _trigger_simulator_action("stop", current_regime, api_online)
            st.rerun()

        if scol3.button(
            "+Ciclo",
            key="sidebar_sim_step",
            type="secondary",
            use_container_width=True,
            help="Injeta 4 novas leituras simuladas imediatamente.",
        ):
            _trigger_simulator_action("step", current_regime, api_online)
            st.rerun()

        auto_refresh = st.toggle(
            "Auto-atualizar (10s)",
            value=False,
            key="sidebar_auto_refresh",
            help="Atualiza os indicadores operacionais a cada 10 segundos quando a API está ativa.",
        )
        if auto_refresh and api_online:
            st_autorefresh(interval=10_000, key="vt_periodic_refresh")

        # 6. Rodapé de Telemetria de Infraestrutura
        st.markdown(
            f'<div class="vt-sidebar-foot">'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{api_dot}"></span>API REST</span><span class="vt-sidebar-val">{escape(api_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{db_dot}"></span>Persistência</span><span class="vt-sidebar-val">{escape(db_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{ia_dot}"></span>Modelos IA</span><span class="vt-sidebar-val">{escape(ia_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{sim_dot}"></span>Simulador</span><span class="vt-sidebar-val">{escape(sim_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key">Versão API</span><span class="vt-sidebar-val">v{escape(version)}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    return selected or MENU_OPTIONS[0]


def run_standalone_page(default_page: str) -> None:
    """Garante renderização completa da aplicação caso um arquivo em frontend/pages/ seja acessado diretamente."""
    from frontend.pages.dashboard import render as render_dashboard
    from frontend.pages.eda import render as render_eda
    from frontend.pages.models_ai import render as render_models
    from frontend.pages.oee import render as render_oee
    from frontend.pages.predictive_maintenance import render as render_maintenance
    from frontend.pages.realtime_monitoring import render as render_realtime
    from frontend.pages.simulator import render as render_simulator
    from frontend.pages.technical_report import render as render_report
    from frontend.pages.vision import render as render_vision
    from frontend.styles import apply_styles

    apply_styles()
    selected = render_sidebar(default_page=default_page)
    page_map = {
        "Dashboard Geral": render_dashboard,
        "Monitoramento em Tempo Real": render_realtime,
        "Manutenção Preditiva": render_maintenance,
        "OEE e Eficiência Industrial": render_oee,
        "Visão Computacional": render_vision,
        "Análise de Dados (EDA)": render_eda,
        "Modelos de IA": render_models,
        "Simulador Industrial": render_simulator,
        "Parecer Técnico": render_report,
    }
    page_map.get(selected, render_dashboard)()

