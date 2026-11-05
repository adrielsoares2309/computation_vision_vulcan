"""VulcanTech industrial analytics dashboard — Cockpit MES / SCADA com 9 módulos industriais."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.components.sidebar import MENU_OPTIONS, render_sidebar
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

st.set_page_config(
    page_title="VulcanTech Smart Metals S.A. — MES & SCADA Industrial",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_styles()
selected = render_sidebar()

pages = {
    "Dashboard Geral": render_dashboard,
    "Monitoramento em Tempo Real": render_realtime,
    "Manutenção Preditiva": render_maintenance,
    "OEE e Eficiência Industrial": render_oee,
    "Visão Computacional": render_vision,
    "Análise de Dados (EDA)": render_eda,
    "Modelos de IA": render_models,
    "Simulador Industrial": render_simulator,
    "Parecer Técnico": render_report,
    "OEE": render_oee,
}

try:
    page_fn = pages.get(selected, render_dashboard)
    page_fn()
except Exception as error:
    st.error(f"Não foi possível carregar este módulo: {error}")
    st.caption("Confira a disponibilidade das dependências, dados e modelos deste projeto.")
