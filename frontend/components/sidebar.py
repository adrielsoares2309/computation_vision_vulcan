"""Navegação industrial profissional com ícones vetoriais SVG (Lucide/Tabler), filtros de escopo e telemetria SCADA."""

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

# Mapeamento estrito dos módulos industriais documentados
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

# Mapeamento de ícones Lucide/Tabler conforme especificação
MENU_ICON_MAP = {
    "Dashboard Geral": "layout_dashboard",
    "Monitoramento em Tempo Real": "activity",
    "Manutenção Preditiva": "wrench",
    "OEE e Eficiência Industrial": "gauge",
    "Visão Computacional": "scan_eye",
    "Análise de Dados (EDA)": "chart_no_axes_combined",
    "Modelos de IA": "brain_circuit",
    "Simulador Industrial": "sliders_horizontal",
    "Parecer Técnico": "file_check",
}

MENU_ICONS = [MENU_ICON_MAP[k] for k in MENU_OPTIONS]

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
    """Renderiza a barra lateral industrial Siemens/Fiori com navegação por ícones SVG vetoriais."""
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

    # Sincronização de navegação
    if default_page and default_page in MENU_OPTIONS and "vt_nav_menu" not in st.session_state:
        st.session_state["vt_nav_menu"] = default_page

    saved_selection = st.session_state.get("vt_nav_menu")
    default_idx = MENU_OPTIONS.index(saved_selection) if saved_selection in MENU_OPTIONS else 0

    with st.sidebar:
        # 1. Identidade Visual da Planta (Estilo Siemens / WEG)
        st.markdown(
            '<div class="vt-logo">'
            '<svg class="vt-logo-mark" viewBox="0 0 48 48" role="img" aria-label="VulcanTech Industrial">'
            '<rect width="48" height="48" rx="8" fill="#1565C0"/>'
            '<path d="M11 14h7L24 28 30 14h7L26.5 35h-5L11 14Z" fill="#FFFFFF"/>'
            '</svg>'
            '<div><div class="vt-logo-name">VulcanTech MES</div>'
            '<div class="vt-logo-sub">SCADA & AI PLATFORM</div></div></div>',
            unsafe_allow_html=True,
        )

        # 2. Navegação por Ícones SVG Vetoriais
        st.markdown(
            f'<div class="sidebar-section-title">{svg_icon("layers", COLORS["text_heading"], 13)}<span>Navegação</span></div>',
            unsafe_allow_html=True,
        )

        # Usamos format_func com ícone SVG inline + nome para clareza e acessibilidade (WCAG 2.2)
        def _format_nav_item(item: str) -> str:
            return item

        selected = st.radio(
            "Navegação do Sistema",
            options=MENU_OPTIONS,
            index=default_idx,
            key="vt_nav_radio",
            label_visibility="collapsed",
        )
        st.session_state["vt_nav_menu"] = selected

        # 3. Escopo Operacional (Célula e Liga)
        st.markdown(
            f'<div class="sidebar-section-title">{svg_icon("factory", COLORS["text_heading"], 13)}<span>Filtro de Célula</span></div>',
            unsafe_allow_html=True,
        )
        selected_cell = st.selectbox(
            "Célula Industrial",
            options=CELL_OPTIONS,
            index=0,
            key="sidebar_cell_select",
            label_visibility="collapsed",
            help="Filtra a célula de manufatura monitorada.",
        )
        st.session_state["selected_cell"] = None if selected_cell == "Todas as Células" else selected_cell

        selected_alloy = st.selectbox(
            "Liga Metálica",
            options=ALLOY_OPTIONS,
            index=0,
            key="sidebar_alloy_select",
            label_visibility="collapsed",
            help="Filtra a liga metálica processada.",
        )
        st.session_state["selected_alloy"] = None if selected_alloy == "Todas as Ligas" else selected_alloy

        # 4. Regime Operacional do CLP
        st.markdown(
            f'<div class="sidebar-section-title">{svg_icon("activity", COLORS["text_heading"], 13)}<span>Regime CLP</span></div>',
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
                if st.button(
                    short_label,
                    key=f"btn_regime_{reg_key.lower()}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                    help=f"Regime {sim.REGIME_LABELS.get(reg_key, reg_key)}",
                ):
                    clicked_regime = (reg_key, api_mode)

        if clicked_regime is not None:
            _apply_regime_change(clicked_regime[0], clicked_regime[1], api_online)
            st.rerun()

        # 5. Controle do Simulador
        st.markdown(
            f'<div class="sidebar-section-title">{svg_icon("sliders_horizontal", COLORS["text_heading"], 13)}<span>Simulador</span></div>',
            unsafe_allow_html=True,
        )
        scol1, scol2, scol3 = st.columns(3)
        if scol1.button(
            "Iniciar",
            key="sidebar_sim_start",
            type="primary",
            use_container_width=True,
            disabled=sim_running,
            help="Inicia geração contínua de telemetria.",
        ):
            _trigger_simulator_action("start", current_regime, api_online)
            st.rerun()

        if scol2.button(
            "Parar",
            key="sidebar_sim_stop",
            type="secondary",
            use_container_width=True,
            disabled=not sim_running,
            help="Pausa o simulador.",
        ):
            _trigger_simulator_action("stop", current_regime, api_online)
            st.rerun()

        if scol3.button(
            "+Ciclo",
            key="sidebar_sim_step",
            type="secondary",
            use_container_width=True,
            help="Executa 1 ciclo de telemetria imediato.",
        ):
            _trigger_simulator_action("step", current_regime, api_online)
            st.rerun()

        auto_refresh = st.toggle(
            "Auto-atualizar (10s)",
            value=False,
            key="sidebar_auto_refresh",
            help="Sincronização periódica da telemetria.",
        )
        if auto_refresh and api_online:
            st_autorefresh(interval=10_000, key="vt_periodic_refresh")

        # 6. Rodapé Técnico de Conectividade Industrial
        api_dot = "#10B981" if api_online else "#EF4444"
        api_txt = "ONLINE" if api_online else "OFFLINE"
        db_dot = "#10B981" if db_online else "#EF4444"
        db_txt = "PRONTO" if db_online else "INDISPONÍVEL"
        sim_dot = "#10B981" if sim_running else "#64748B"
        sim_txt = "EXECUÇÃO" if sim_running else "PARADO"
        ia_dot = "#10B981" if (tab_ok and vis_ok) else ("#F59E0B" if (tab_ok or vis_ok) else "#EF4444")
        ia_txt = "ATIVO" if (tab_ok and vis_ok) else ("PARCIAL" if (tab_ok or vis_ok) else "OFFLINE")

        st.markdown(
            f'<div class="vt-sidebar-foot">'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{api_dot}"></span>API REST</span><span class="vt-sidebar-val">{escape(api_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{db_dot}"></span>SQLite</span><span class="vt-sidebar-val">{escape(db_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{ia_dot}"></span>Modelos IA</span><span class="vt-sidebar-val">{escape(ia_txt)}</span></div>'
            f'<div class="vt-sidebar-row"><span class="vt-sidebar-key"><span class="vt-dot" style="background:{sim_dot}"></span>Simulador</span><span class="vt-sidebar-val">{escape(sim_txt)}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    return selected or MENU_OPTIONS[0]


def run_standalone_page(default_page: str) -> None:
    """Renderiza a aplicação com a sidebar e roteia para a página especificada."""
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
