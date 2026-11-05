"""Módulo de Monitoramento Operacional de OEE (Overall Equipment Effectiveness) estilo MES/SCADA."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import APIConnectionError, APIResponseError
from frontend.services.oee_service import (
    get_oee_by_equipment,
    get_oee_downtime,
    get_oee_events,
    get_oee_history,
    get_oee_snapshot,
    get_simulation_status,
    set_simulation_mode,
    start_simulation,
    step_simulation,
    stop_simulation,
)

SOURCE_LABELS = {
    "simulated": "Simulados (MES Demo)",
    "api": "API Operacional",
    "all": "Consolidado (API + Simulados)",
    "historical": "Histórico (Somente Sensores · N/D)",
}

SIM_MODES = [
    "MISTO",
    "NORMAL",
    "DESGASTE_FERRAMENTA",
    "FALHA_REFRIGERACAO",
    "DESALINHAMENTO_TRINCA",
]


def _fmt_pct(value: float | None) -> str:
    return f"{value:.1f}%" if value is not None else "N/D"


def _fmt_min(value: float | None) -> str:
    return f"{value:.1f} min" if value is not None else "N/D"


def _fmt_int(value: int | None) -> str:
    return f"{int(value):,}" if value is not None else "N/D"


def _kpi_tone(pct: float | None, target: float = 80.0) -> str:
    if pct is None:
        return "neutral"
    if pct >= target:
        return "success"
    if pct >= target - 15.0:
        return "warning"
    return "danger"


def render() -> None:
    try:
        sim_status = get_simulation_status()
    except APIConnectionError as exc:
        render_header(
            "OEE · Gestão de Eficiência Operacional",
            "Monitoramento de disponibilidade, performance, qualidade, produção e paradas.",
            "speed",
            refresh_callback=st.cache_data.clear,
            context_badge=("API OFFLINE", "danger"),
        )
        st.error(f"Conexão indisponível com o backend FastAPI: {exc}")
        return
    except APIResponseError as exc:
        render_header(
            "OEE · Gestão de Eficiência Operacional",
            "Monitoramento de disponibilidade, performance, qualidade, produção e paradas.",
            "speed",
            context_badge=("ERRO HTTP", "danger"),
        )
        st.error(f"Falha ao consultar estado operacional: {exc.message}")
        return

    # Barra integrada de Filtros Operacionais + Controle Rápido de Lotes
    f1, f2, f3, f4, f5 = st.columns([1.35, 0.95, 0.95, 1.25, 1.0], vertical_alignment="bottom")
    with f1:
        default_src_idx = 0 if sim_status.get("cycles_completed", 0) > 0 else 2
        data_source = st.selectbox(
            "Origem dos dados",
            options=list(SOURCE_LABELS.keys()),
            index=default_src_idx,
            format_func=lambda k: SOURCE_LABELS[k],
        )
    with f2:
        selected_cell = st.selectbox("Equipamento", ["Todas", "CEL-201", "CEL-202", "CEL-203", "CEL-204"])
    with f3:
        selected_shift = st.selectbox("Turno", ["Todos", "MANHA", "TARDE", "NOITE"])
    with f4:
        date_filter = st.date_input("Período", value=())
    with f5:
        if st.button("Gerar +4 lotes (Simulador)", type="primary", width="stretch"):
            try:
                step_simulation(mode=sim_status.get("mode", "MISTO"), count=4)
                st.rerun()
            except Exception as exc:
                st.error(f"Falha na geração de lotes: {exc}")

    start_date = end_date = None
    if isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_date = date_filter[0].isoformat()
        end_date = date_filter[1].isoformat()
    elif isinstance(date_filter, tuple) and len(date_filter) == 1:
        start_date = end_date = date_filter[0].isoformat()

    try:
        snapshot = get_oee_snapshot(
            equipment_id=selected_cell,
            shift=selected_shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
        )
    except (APIConnectionError, APIResponseError) as exc:
        st.error(f"Falha ao consultar resumo de OEE: {exc}")
        return

    available = bool(snapshot.get("available"))
    badge_Map = {
        "simulated": ("FONTE: SIMULADOS", "info"),
        "api": ("FONTE: API OPERACIONAL", "success"),
        "all": ("FONTE: CONSOLIDADO", "info"),
        "historical": ("FONTE: HISTÓRICO (N/D)", "neutral"),
    }
    render_header(
        "OEE · Gestão de Eficiência Operacional",
        f"Escopo: {selected_cell} · Turno: {selected_shift} · Lotes avaliados: {snapshot.get('records_count', 0)}",
        "speed",
        last_update=snapshot.get("last_timestamp"),
        refresh_callback=st.cache_data.clear,
        context_badge=badge_Map.get(data_source, ("OPERACIONAL", "neutral")),
    )

    # Linha única com os 6 KPIs principais exigidos
    metrics = snapshot.get("metrics", {})
    oee_val = metrics.get("oee")
    avail_val = metrics.get("availability")
    perf_val = metrics.get("performance")
    qual_val = metrics.get("quality")
    total_cnt = metrics.get("total_count")
    good_cnt = metrics.get("good_count")
    rej_cnt = metrics.get("rejected_count")
    down_min = metrics.get("downtime_min")
    op_min = metrics.get("operating_time_min")
    plan_min = metrics.get("planned_time_min")

    k_cols = st.columns(6)
    with k_cols[0]:
        render_kpi(
            "OEE Global",
            _fmt_pct(oee_val),
            "Disp. × Perf. × Qual." if available else "Sem lotes válidos",
            "speed",
            tone=_kpi_tone(oee_val, 75.0),
        )
    with k_cols[1]:
        render_kpi(
            "Disponibilidade",
            _fmt_pct(avail_val),
            f"Op.: {_fmt_min(op_min)} / Plan.: {_fmt_min(plan_min)}" if available else "N/D",
            "factory",
            tone=_kpi_tone(avail_val, 85.0),
        )
    with k_cols[2]:
        render_kpi(
            "Performance",
            _fmt_pct(perf_val),
            "Tempo ideal × Prod. / Op." if available else "N/D",
            "speed",
            tone=_kpi_tone(perf_val, 85.0),
        )
    with k_cols[3]:
        render_kpi(
            "Qualidade",
            _fmt_pct(qual_val),
            f"Aprovadas: {_fmt_int(good_cnt)} un" if available else "N/D",
            "verified",
            tone=_kpi_tone(qual_val, 95.0),
        )
    with k_cols[4]:
        render_kpi(
            "Produção Total",
            f"{_fmt_int(total_cnt)} un" if total_cnt is not None else "N/D",
            f"Boas: {_fmt_int(good_cnt)} · Refugo: {_fmt_int(rej_cnt)}" if available else "N/D",
            "box",
            tone="primary" if available else "neutral",
        )
    with k_cols[5]:
        render_kpi(
            "Tempo de Parada",
            _fmt_min(down_min),
            f"{snapshot.get('records_count', 0)} lotes no filtro" if available else "N/D",
            "clock",
            tone="warning" if (down_min and down_min > 0) else "neutral",
        )

    with st.expander("Parâmetros do Simulador Industrial em Background", expanded=False):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.3], vertical_alignment="bottom")
        current_mode = sim_status.get("mode", "MISTO")
        with c1:
            chosen_mode = st.selectbox(
                "Modo operacional",
                SIM_MODES,
                index=SIM_MODES.index(current_mode) if current_mode in SIM_MODES else 0,
                key="oee_sim_mode",
            )
            if chosen_mode != current_mode:
                sim_status = set_simulation_mode(chosen_mode)
        with c2:
            if st.button("Iniciar contínuo", type="primary", disabled=bool(sim_status.get("running")), width="stretch"):
                start_simulation(mode=chosen_mode, interval_seconds=5.0, generate_initial_batch=4)
                st.rerun()
        with c3:
            if st.button("Parar contínuo", disabled=not bool(sim_status.get("running")), width="stretch"):
                stop_simulation()
                st.rerun()
        with c4:
            st.caption(
                f"Status: {'ATIVO' if sim_status.get('running') else 'PARADO'} · "
                f"Ciclos: {sim_status.get('cycles_completed', 0)}"
            )

    if not available:
        st.warning(
            snapshot.get("reason")
            or "Sem registros operacionais de produção para os filtros selecionados. Utilize o botão 'Gerar +4 lotes (Simulador)' ou selecione outra origem."
        )
        return

    try:
        history_resp = get_oee_history(
            equipment_id=selected_cell,
            shift=selected_shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
        )
        equip_resp = get_oee_by_equipment(
            shift=selected_shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
        )
        down_resp = get_oee_downtime(
            equipment_id=selected_cell,
            shift=selected_shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
        )
        events_resp = get_oee_events(
            equipment_id=selected_cell,
            shift=selected_shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=100,
        )
    except (APIConnectionError, APIResponseError) as exc:
        st.error(f"Erro ao carregar séries analíticas de OEE: {exc}")
        return

    tab_evol, tab_comp, tab_stops, tab_impact = st.tabs(
        [
            "Evolução Temporal & Produção por Período",
            "Comparativo por Equipamento (Disp. × Perf. × Qual.)",
            "Histórico de Paradas & Eventos Operacionais",
            "Impacto Preditivo no OEE & Financeiro",
        ]
    )

    with tab_evol:
        series_list = history_resp.get("series", [])
        if series_list:
            hist_df = pd.DataFrame(series_list)
            g1, g2 = st.columns(2, gap="medium")
            with g1:
                fig_line = px.line(
                    hist_df,
                    x="timestamp",
                    y=["oee", "availability", "performance", "quality"],
                    markers=True,
                    title="Evolução Temporal do OEE e Fatores (%)",
                    labels={"value": "Índice (%)", "timestamp": "Horário do lote", "variable": "Indicador"},
                )
                apply_chart_theme(fig_line, height=320)
                st.plotly_chart(fig_line, width="stretch", key="oee-history-chart")
            with g2:
                fig_prod = px.bar(
                    hist_df,
                    x="timestamp",
                    y=["good_count", "rejected_count"],
                    barmode="stack",
                    title="Produção por Período (Unidades Boas vs. Refugo)",
                    labels={"value": "Unidades", "timestamp": "Horário do lote", "variable": "Classificação"},
                )
                apply_chart_theme(fig_prod, height=320)
                st.plotly_chart(fig_prod, width="stretch", key="oee-prod-period-chart")
        else:
            st.info("Sem série histórica para o recorte selecionado.")

    with tab_comp:
        equip_list = [e for e in equip_resp.get("equipment", []) if e.get("available")]
        if equip_list:
            eq_df = pd.DataFrame(equip_list)
            c_chart, c_table = st.columns([1.25, 1.0], gap="medium")
            with c_chart:
                fig_bar = px.bar(
                    eq_df,
                    x="id_celula",
                    y=["availability", "performance", "quality", "oee"],
                    barmode="group",
                    title="Disponibilidade, Performance, Qualidade e OEE por Célula (%)",
                    labels={"value": "Percentual (%)", "id_celula": "Equipamento", "variable": "Indicador"},
                )
                apply_chart_theme(fig_bar, height=320)
                st.plotly_chart(fig_bar, width="stretch", key="oee-equipment-chart")
            with c_table:
                summary_table = eq_df[
                    [
                        "id_celula",
                        "records_count",
                        "oee",
                        "availability",
                        "performance",
                        "quality",
                        "total_count",
                        "downtime_min",
                    ]
                ].rename(
                    columns={
                        "id_celula": "Célula",
                        "records_count": "Lotes",
                        "oee": "OEE (%)",
                        "availability": "Disp. (%)",
                        "performance": "Perf. (%)",
                        "quality": "Qual. (%)",
                        "total_count": "Produção",
                        "downtime_min": "Paradas (min)",
                    }
                )
                st.dataframe(summary_table, hide_index=True, width="stretch", height=310)
        else:
            st.info("Sem dados comparativos entre células para o filtro atual.")

    with tab_stops:
        d1, d2 = st.columns([1.0, 1.45], gap="medium")
        with d1:
            reasons = down_resp.get("by_reason", [])
            if reasons:
                r_df = pd.DataFrame(reasons)
                fig_down = px.bar(
                    r_df,
                    x="downtime_min",
                    y="reason",
                    orientation="h",
                    title="Pareto de Paradas por Motivo (min)",
                    labels={"downtime_min": "Minutos acumulados", "reason": "Motivo"},
                )
                apply_chart_theme(fig_down, height=320)
                st.plotly_chart(fig_down, width="stretch", key="oee-downtime-chart")
            else:
                st.info("Nenhuma parada registrada nos lotes consultados.")
        with d2:
            events = events_resp.get("items", [])
            if events:
                ev_df = pd.DataFrame(events)[
                    [
                        "timestamp",
                        "id_celula",
                        "liga_metalica",
                        "shift",
                        "planned_time_min",
                        "downtime_min",
                        "total_count",
                        "good_count",
                        "rejected_count",
                        "data_source",
                    ]
                ].rename(
                    columns={
                        "timestamp": "Data/Hora",
                        "id_celula": "Célula",
                        "liga_metalica": "Liga",
                        "shift": "Turno",
                        "planned_time_min": "Plan. (min)",
                        "downtime_min": "Parada (min)",
                        "total_count": "Prod. Total",
                        "good_count": "Boas",
                        "rejected_count": "Refugo",
                        "data_source": "Origem",
                    }
                )
                st.dataframe(ev_df, hide_index=True, width="stretch", height=320)
            else:
                st.info("Nenhum evento operacional listado.")

    with tab_impact:
        st.markdown("<h4 style='font-size:1.05rem; font-weight:700; color:#0F172A;'>Projeção de Impacto de Falhas no OEE e Perdas Financeiras</h4>", unsafe_allow_html=True)
        st.markdown(
            "Quantifica como falhas previstas não tratadas penalizam a Disponibilidade (tempo de parada corretiva) "
            "e a Qualidade (peças rejeitadas), calculando o custo total do downtime e o ROI da ação preditiva."
        )

        pcol1, pcol2 = st.columns([1, 1.4])
        with pcol1:
            tipo_falha_sim = st.selectbox(
                "Tipo de Falha Prevista:",
                options=[1, 2, 3],
                format_func=lambda x: {
                    1: "1 - Desgaste de Ferramenta (MTTR ~45m)",
                    2: "2 - Falha de Refrigeração (MTTR ~90m)",
                    3: "3 - Desalinhamento / Trinca Estrutural (MTTR ~180m)",
                }[x],
            )
            prob_falha_sim = st.slider("Probabilidade da Falha:", 0.20, 0.99, 0.85, 0.05)
            anom_score_sim = st.slider("Score de Anomalia (Isolation Forest):", 0.10, 0.99, 0.75, 0.05)
            custo_hora = st.number_input("Custo Hora Parada (R$/h):", value=4500.0, step=500.0)
            custo_peca = st.number_input("Custo Peça Rejeitada (R$/un):", value=850.0, step=50.0)

        with pcol2:
            from src.oee.calculator import calculate_oee_from_counts
            from src.oee.predictive_impact import calcular_impacto_preditivo_oee

            oee_base_impact = calculate_oee_from_counts(480.0, 30.0, 1.5, 280, good_count=268)
            res_impact = calcular_impacto_preditivo_oee(
                oee_atual=oee_base_impact,
                tipo_falha_previsto=tipo_falha_sim,
                probabilidade_falha=prob_falha_sim,
                score_anomalia=anom_score_sim,
                custo_hora_parada=custo_hora,
                custo_peca_rejeito=custo_peca,
            )

            oee_antes = res_impact["oee_atual"]["oee"]
            oee_depois = res_impact["oee_projetado_sem_intervencao"]["oee"]
            queda = res_impact["impacto"]["queda_oee_pontos_percentuais"]
            perda_rs = res_impact["financeiro"]["perda_total_estimada_brl"]
            economia_rs = res_impact["financeiro"]["economia_acao_preventiva_brl"]

            st.markdown(
                f"""
                <div class="vt-card" style="border-left: 6px solid #DC2626; padding: 16px; margin-bottom: 12px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">
                        DEGRADAÇÃO PROJETADA CASO NÃO HAJA INTERVENÇÃO
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline; margin: 6px 0;">
                        <span style="font-size:1.8rem; font-weight:800; color:#DC2626;">
                            {oee_antes:.1f}% &rarr; {oee_depois:.1f}% (-{queda:.1f} p.p.)
                        </span>
                        <span class="vt-badge vt-badge-danger" style="font-size:0.85rem; padding:4px 10px;">
                            GRAVIDADE: {res_impact['gravidade']}
                        </span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155;">
                        <b>Parada Não Planejada Estimada:</b> +{res_impact['impacto']['downtime_adicional_previsto_min']} min |
                        <b>Refugo Adicional:</b> +{res_impact['impacto']['pecas_refugo_adicionais']} un
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            fcol1, fcol2 = st.columns(2)
            with fcol1:
                st.markdown(
                    f"""
                    <div class="vt-card" style="border:1px solid #CBD5E1; padding: 12px;">
                        <div style="font-size:0.75rem; color:#64748B; font-weight:700;">PERDA FINANCEIRA TOTAL</div>
                        <div style="font-size:1.4rem; font-weight:800; color:#DC2626;">R$ {perda_rs:,.2f}</div>
                        <div style="font-size:0.72rem; color:#64748B;">Downtime + Refugo de Lote</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with fcol2:
                st.markdown(
                    f"""
                    <div class="vt-card" style="border:1px solid #10B981; padding: 12px; background:#ECFDF5;">
                        <div style="font-size:0.75rem; color:#065F46; font-weight:700;">ECONOMIA PREVENTIVA (ROI)</div>
                        <div style="font-size:1.4rem; font-weight:800; color:#059669;">R$ {economia_rs:,.2f}</div>
                        <div style="font-size:0.72rem; color:#065F46;">Evitada com Ação Antecipada</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.info(f"Recomendação Prescritiva: {res_impact['recomendacao_operacional']}")


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('OEE e Eficiência Industrial')
