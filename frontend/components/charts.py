"""Tema Plotly industrial padronizado com alto contraste (WCAG 2.2)."""

from __future__ import annotations

import plotly.graph_objects as go

from frontend.styles import DESIGN_TOKENS

c = DESIGN_TOKENS["colors"]
PALETTE = [
    c["chart_blue"],
    c["chart_teal"],
    c["chart_amber"],
    c["chart_red"],
    c["chart_slate"],
    c["chart_purple"],
]


def style_figure(fig: go.Figure, height: int = 310) -> go.Figure:
    """Aplica tema corporativo claro, bordas discretas e tipografia de alto contraste."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=38, b=14),
        paper_bgcolor=c["bg_surface"],
        plot_bgcolor=c["bg_surface"],
        font=dict(
            family="Inter, Segoe UI, Arial, sans-serif",
            color=c["text_primary"],
            size=11,
        ),
        title=dict(
            font=dict(size=13, color=c["text_primary"], family="Inter, Segoe UI, sans-serif"),
            x=0.0,
            xanchor="left",
        ),
        colorway=PALETTE,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color=c["text_secondary"]),
            title=dict(text=""),
        ),
        hoverlabel=dict(
            bgcolor=c["bg_surface"],
            bordercolor=c["border_strong"],
            font=dict(color=c["text_primary"], size=11),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=c["border"],
        tickfont=dict(color=c["text_secondary"], size=10),
        title_font=dict(color=c["text_secondary"], size=11),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor="#E2E8F0",
        linecolor=c["border"],
        tickfont=dict(color=c["text_secondary"], size=10),
        title_font=dict(color=c["text_secondary"], size=11),
        zeroline=False,
    )
    return fig


apply_chart_theme = style_figure
