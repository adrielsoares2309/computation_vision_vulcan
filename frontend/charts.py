"""Gráficos Plotly industriais de alto contraste para o cockpit VulcanTech Smart Metals S.A.

Paleta de Cores Industrial de Alto Contraste (WCAG 2.2 AA):
- Área de plotagem (canvas): `#FFFFFF` (fundo branco com grade e moldura contrastantes)
- Fundo externo (card): `#FFFFFF`
- Borda e eixos: `#475569` com mirror=True (quadro fechado e nítido)
- Linhas de grade: `#CBD5E1` (perfeitamente visíveis sobre o canvas)
- Séries principais: Azul industrial `#1565C0`, Âmbar `#B45309`, Laranja `#E65100`, Vermelho `#C62828`, Teal `#0F766E`
- Zero emojis em qualquer visualização ou anotação.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

CHART_PALETTE = {
    "blue": "#1565C0",          # Série principal (Torque / Rotação)
    "orange": "#E65100",        # Vibração triaxial RMS
    "purple": "#6A1B9A",        # Pressão hidráulica
    "green": "#16803C",         # Vazão de refrigerante / Estado Normal
    "amber": "#B45309",         # Temperatura do fuso / Alerta
    "red": "#C62828",           # Falhas críticas e fora dos limites
    "teal": "#0F766E",          # Corrente do estator
    "slate": "#475569",         # Eixos e bordas dos gráficos
    "grid": "#CBD5E1",          # Linhas de grade nítidas
    "plot_bg": "#FFFFFF",       # Fundo branco da área de plotagem
    "paper_bg": "#FFFFFF",      # Fundo do cartão externo
    "font_heading": "#0F172A",  # Títulos e labels principais
    "font_body": "#1E293B",     # Rótulos de eixos e valores
    "safe_fill": "rgba(22, 128, 60, 0.08)",  # Faixa operacional segura
}

SENSOR_LIMITS = {
    "temperatura_fuso_c": (45.0, 85.0),
    "vibracao_triaxial_rms_mms": (1.0, 4.5),
    "torque_fuso_nm": (40.0, 120.0),
    "vazao_refrigerante_lmin": (10.0, 25.0),
}

REGIME_LABELS = {
    "Producao_Normal": "Produção Normal",
    "Usinagem_Pesada": "Usinagem Pesada",
    "Alta_Velocidade": "Alta Velocidade",
}

REGIME_COLORS = {
    "Producao_Normal": CHART_PALETTE["blue"],
    "Usinagem_Pesada": CHART_PALETTE["amber"],
    "Alta_Velocidade": CHART_PALETTE["orange"],
}


def _add_regime_transitions(fig: go.Figure, df: pd.DataFrame) -> None:
    """Marca transições operacionais com linhas verticais discretas e rotuladas."""
    col = "modo_operacao" if "modo_operacao" in df.columns else ("regime_operacional" if "regime_operacional" in df.columns else None)
    if col is None or "timestamp" not in df.columns:
        return

    ordered = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if len(ordered) < 2:
        return

    labels = ordered[col].tolist()
    moments = ordered["timestamp"].tolist()
    transitions = [
        (moments[i], labels[i])
        for i in range(1, len(labels))
        if pd.notna(labels[i]) and labels[i] != labels[i - 1]
    ]

    for ts, reg in transitions[-6:]:
        color = REGIME_COLORS.get(str(reg), CHART_PALETTE["slate"])
        fig.add_vline(
            x=ts,
            line_dash="dot",
            line_color=color,
            line_width=1.4,
            annotation_text=REGIME_LABELS.get(str(reg), str(reg)),
            annotation_position="top left",
            annotation_font_size=9,
            annotation_font_color=color,
            annotation_bgcolor="rgba(255,255,255,0.88)",
        )


def _apply_industrial_layout(
    fig: go.Figure,
    title: str,
    x_title: str | None = None,
    y_title: str | None = None,
    height: int = 280,
) -> go.Figure:
    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 13, "color": CHART_PALETTE["font_heading"], "family": "Inter, sans-serif"},
            "x": 0.01,
            "y": 0.95,
        },
        height=height,
        margin={"l": 48, "r": 20, "t": 38, "b": 38},
        plot_bgcolor=CHART_PALETTE["plot_bg"],
        paper_bgcolor=CHART_PALETTE["paper_bg"],
        font={"color": CHART_PALETTE["font_body"], "size": 11, "family": "Inter, sans-serif"},
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "font": {"size": 10},
        },
        xaxis={
            "title": x_title,
            "showgrid": True,
            "gridcolor": CHART_PALETTE["grid"],
            "linecolor": CHART_PALETTE["slate"],
            "mirror": True,
            "zeroline": False,
        },
        yaxis={
            "title": y_title,
            "showgrid": True,
            "gridcolor": CHART_PALETTE["grid"],
            "linecolor": CHART_PALETTE["slate"],
            "mirror": True,
            "zeroline": False,
        },
    )
    return fig


def plot_telemetry_timeseries(
    df: pd.DataFrame,
    sensor_col: str,
    sensor_label: str,
    unit: str,
    color_hex: str | None = None,
    height: int = 280,
) -> go.Figure:
    """Plota série temporal de telemetria com limites operacionais e detecção de transições."""
    fig = go.Figure()
    if df.empty or sensor_col not in df.columns:
        fig.add_annotation(text="Sem dados de telemetria disponíveis", showarrow=False)
        return _apply_industrial_layout(fig, f"{sensor_label} — Histórico", height=height)

    color = color_hex or CHART_PALETTE["blue"]
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df[sensor_col],
            mode="lines+markers",
            name=f"{sensor_label} ({unit})",
            line={"color": color, "width": 2.2},
            marker={"size": 4, "color": color},
        )
    )

    # Limites operacionais seguros
    if sensor_col in SENSOR_LIMITS:
        low, high = SENSOR_LIMITS[sensor_col]
        fig.add_hline(
            y=high,
            line_dash="dash",
            line_color=CHART_PALETTE["red"],
            line_width=1.5,
            annotation_text=f"Limite Máx ({high} {unit})",
            annotation_position="bottom right",
            annotation_font_size=9,
            annotation_font_color=CHART_PALETTE["red"],
        )
        fig.add_hline(
            y=low,
            line_dash="dash",
            line_color=CHART_PALETTE["amber"],
            line_width=1.5,
            annotation_text=f"Limite Mín ({low} {unit})",
            annotation_position="top right",
            annotation_font_size=9,
            annotation_font_color=CHART_PALETTE["amber"],
        )

    _add_regime_transitions(fig, df)
    return _apply_industrial_layout(
        fig,
        title=f"Telemetria: {sensor_label}",
        x_title="Horário",
        y_title=f"{sensor_label} [{unit}]",
        height=height,
    )


def plot_iem_gauge(iem_value: float, cell_id: str = "CEL-201") -> go.Figure:
    """Indicador Gauge para o Índice de Esforço Mecânico (IEM)."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=iem_value,
            number={"suffix": " IEM", "font": {"size": 22, "color": CHART_PALETTE["font_heading"]}},
            gauge={
                "axis": {"range": [0, 50], "tickwidth": 1, "tickcolor": CHART_PALETTE["slate"]},
                "bar": {"color": CHART_PALETTE["blue"], "thickness": 0.25},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": CHART_PALETTE["slate"],
                "steps": [
                    {"range": [0, 18], "color": "#ECFDF5"},
                    {"range": [18, 30], "color": "#FFFBEB"},
                    {"range": [30, 50], "color": "#FEF2F2"},
                ],
                "threshold": {
                    "line": {"color": CHART_PALETTE["red"], "width": 3},
                    "thickness": 0.75,
                    "value": 30.0,
                },
            },
        )
    )
    fig.update_layout(
        title={"text": f"IEM — {cell_id}", "font": {"size": 12, "color": CHART_PALETTE["font_heading"]}},
        height=190,
        margin={"l": 20, "r": 20, "t": 30, "b": 10},
        paper_bgcolor=CHART_PALETTE["paper_bg"],
    )
    return fig


def plot_oee_breakdown(
    availability: float,
    performance: float,
    quality: float,
    oee: float,
) -> go.Figure:
    """Gráfico de barras dos fatores do OEE industrial (Meta Mundial: 85%)."""
    labels = ["Disponibilidade", "Performance", "Qualidade", "OEE Geral"]
    values = [availability * 100.0, performance * 100.0, quality * 100.0, oee * 100.0]
    colors = [CHART_PALETTE["blue"], CHART_PALETTE["teal"], CHART_PALETTE["purple"], CHART_PALETTE["amber"]]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v:.1f}%" for v in values],
            textposition="auto",
            marker_color=colors,
            marker_line={"color": CHART_PALETTE["slate"], "width": 1},
        )
    )
    fig.add_hline(
        y=85.0,
        line_dash="dot",
        line_color=CHART_PALETTE["green"],
        line_width=2,
        annotation_text="Classe Mundial (85%)",
        annotation_position="top right",
    )
    fig.update_layout(
        title={"text": "Composição dos Indicadores de Eficiência Global (OEE)", "font": {"size": 13}},
        yaxis={"range": [0, 105], "title": "Percentual (%)", "gridcolor": CHART_PALETTE["grid"]},
        xaxis={"gridcolor": CHART_PALETTE["grid"]},
        height=280,
        plot_bgcolor=CHART_PALETTE["plot_bg"],
        paper_bgcolor=CHART_PALETTE["paper_bg"],
        margin={"l": 40, "r": 20, "t": 40, "b": 35},
    )
    return fig

