"""Módulo de Manutenção Preditiva e Monitoramento de Condição de Equipamentos via FastAPI."""

from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import APIConnectionError, APIResponseError
from frontend.services.ml_service import (
    get_equipment_overview,
    get_latest_predictions,
    get_latest_sensor_readings,
    get_maintenance_alerts,
    get_maintenance_sensors_view,
    get_prediction_history,
    get_sensor_metadata,
    predict_sensor_reading,
)
from frontend.styles import render_status_badge

SENSOR_INFO = {
    "temperatura_fuso_c": ("Temperatura do Fuso", "°C", 30.0, 75.0),
    "vibracao_triaxial_rms_mms": ("Vibração Triaxial RMS", "mm/s", 0.8, 3.8),
    "torque_fuso_nm": ("Torque do Fuso", "Nm", 45.0, 210.0),
    "vazao_refrigerante_lmin": ("Vazão de Refrigerante", "L/min", 15.0, 40.0),
    "corrente_estator_amp": ("Corrente do Estator", "A", 12.0, 55.0),
    "pressao_hidraulica_bar": ("Pressão Hidráulica", "bar", 110.0, 220.0),
    "nivel_ruido_db": ("Nível de Ruído", "dB", 45.0, 85.0),
}

SOURCE_OPTIONS = {
    "historical": "Histórico (Parquet Tratado)",
    "simulated": "Simulados (SQLite)",
    "api": "API Operacional (SQLite)",
    "all": "Consolidado (Todas as Fontes)",
}


def _state_badge(class_code: int | None, class_name: str | None) -> str:
    if class_code is None:
        return render_status_badge("SEM LEITURA", "neutral", "indeterminate")
    if class_code == 0:
        return render_status_badge(class_name or "Normal", "success", "check_circle")
    if class_code == 1:
        return render_status_badge(class_name or "Desgaste de ferramenta", "warning", "warning")
    return render_status_badge(class_name or "Falha Crítica", "danger", "cancel")


def render() -> None:
    try:
        metadata = get_sensor_metadata()
        initial_view = get_maintenance_sensors_view(limit=200)
    except APIConnectionError as error:
        render_header(
            "Manutenção Preditiva · Monitoramento de Condição",
            "Telemetria de sensores, estado das células e classificação contemporânea de falhas.",
            "sensors",
            refresh_callback=st.cache_data.clear,
            context_badge=("API OFFLINE", "danger"),
        )
        st.error(f"Conexão indisponível com o backend FastAPI: {error}")
        return
    except APIResponseError as error:
        render_header(
            "Manutenção Preditiva · Monitoramento de Condição",
            "Telemetria de sensores, estado das células e classificação contemporânea de falhas.",
            "sensors",
            context_badge=("INDISPONÍVEL", "danger"),
        )
        st.error(f"Dados ou modelo tabular indisponíveis na API: {error.message}")
        return

    cells = initial_view.get("available_cells", ["CEL-201", "CEL-202", "CEL-203", "CEL-204"])
    date_bounds = initial_view.get("date_range", {})
    min_d = date.fromisoformat(date_bounds["min"]) if date_bounds.get("min") else date(2026, 10, 1)
    max_d = date.fromisoformat(date_bounds["max"]) if date_bounds.get("max") else date(2026, 11, 4)

    # Barra de filtros operacionais compacta
    f1, f2, f3, f4 = st.columns([1.2, 0.9, 1.35, 1.25], vertical_alignment="bottom")
    with f1:
        data_source = st.selectbox(
            "Origem dos dados",
            options=list(SOURCE_OPTIONS.keys()),
            index=0,
            format_func=lambda k: SOURCE_OPTIONS[k],
        )
    with f2:
        selected_cell = st.selectbox("Equipamento", ["Todas", *cells])
    with f3:
        selected_sensor = st.selectbox(
            "Sensor monitorado",
            list(SENSOR_INFO.keys()),
            format_func=lambda col: f"{SENSOR_INFO[col][0]} ({SENSOR_INFO[col][1]})",
        )
    with f4:
        selected_dates = st.date_input("Intervalo", value=(min_d, max_d))

    start_iso = end_iso = None
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_iso, end_iso = selected_dates[0].isoformat(), selected_dates[1].isoformat()
    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
        start_iso = end_iso = selected_dates[0].isoformat()
    elif hasattr(selected_dates, "isoformat"):
        start_iso = end_iso = selected_dates.isoformat()

    try:
        view = get_maintenance_sensors_view(
            equipment_id=selected_cell,
            start_date=start_iso if data_source == "historical" else None,
            end_date=end_iso if data_source == "historical" else None,
            sensor=selected_sensor,
            data_source=data_source,
            limit=500,
        )
        equip_overview = get_equipment_overview(data_source=data_source)
        latest_sensors_resp = get_latest_sensor_readings(data_source=data_source)
        alerts_resp = get_maintenance_alerts(equipment_id=selected_cell, data_source=data_source, limit=50)
        history_resp = get_prediction_history(equipment_id=selected_cell, data_source=data_source, limit=50)
        latest_preds_resp = get_latest_predictions(equipment_id=selected_cell, data_source=data_source)
    except (APIConnectionError, APIResponseError) as exc:
        st.error(f"Erro ao consultar telemetria na API: {exc}")
        return

    last_ts = view.get("last_timestamp")
    src_badge_map = {
        "historical": ("FONTE: HISTÓRICO", "neutral"),
        "simulated": ("FONTE: SIMULADOS", "info"),
        "api": ("FONTE: API REAL", "success"),
        "all": ("FONTE: CONSOLIDADO", "info"),
    }
    render_header(
        "Manutenção Preditiva · Monitoramento de Condição",
        f"Modelo ativo: {metadata.get('model_name', 'LogisticRegression')} (Classificação contemporânea de condição · Sem RUL)",
        "sensors",
        last_update=last_ts,
        refresh_callback=st.cache_data.clear,
        context_badge=src_badge_map.get(data_source, ("HISTÓRICO", "neutral")),
    )

    # KPIs em linha única (5 indicadores objetivos)
    kpis = view.get("kpis", {})
    alerts_items = alerts_resp.get("items", [])
    k_cols = st.columns(5)
    with k_cols[0]:
        render_kpi(
            "Equipamentos Monitorados",
            f"{kpis.get('cells_count', 0)} / {len(cells)}",
            f"Filtro: {selected_cell}",
            "factory",
            tone="primary",
        )
    with k_cols[1]:
        render_kpi(
            "Alertas Operacionais",
            str(len(alerts_items)),
            "Falhas registradas no SQLite",
            "warning",
            tone="danger" if len(alerts_items) > 0 else "success",
        )
    with k_cols[2]:
        render_kpi(
            "Leituras no Período",
            f"{kpis.get('readings_in_period', 0):,}",
            f"Fonte: {data_source.upper()}",
            "sensors",
            tone="primary",
        )
    with k_cols[3]:
        render_kpi(
            "Leituras Classificadas",
            f"{kpis.get('labeled_readings', 0):,}",
            "Com classe de condição associada",
            "verified",
            tone="success",
        )
    with k_cols[4]:
        render_kpi(
            "Previsão Temporal (RUL)",
            "N/D",
            "Escopo: condição presente",
            "clock",
            tone="neutral",
        )

    # Painel de Estado dos Equipamentos Monitorados (CEL-201 a CEL-204)
    latest_by_cell = {
        (item.get("id_celula") or item.get("equipment_id")): item
        for item in latest_preds_resp.get("items", [])
    }
    equip_cards_html = ['<div class="vt-equip-grid">']
    for eq in equip_overview.get("equipment", []):
        cid = eq.get("equipment_id", "CEL")
        pred = eq.get("latest_persisted_prediction") or latest_by_cell.get(cid) or {}
        cls_code = pred.get("predicted_class_code")
        cls_name = pred.get("predicted_class_name", "Sem previsão")
        action = pred.get("recommended_action", "N/D")
        src_tag = str(pred.get("data_source") or "historical").upper()
        ts_short = str(pred.get("timestamp") or eq.get("historical_last_timestamp") or "N/D")[:16].replace("T", " ")
        badge_html = _state_badge(cls_code, cls_name)
        equip_cards_html.append(
            f'<div class="vt-equip-card">'
            f'<div class="vt-equip-top"><span class="vt-equip-id">{escape(cid)}</span>{badge_html}</div>'
            f'<div class="vt-equip-meta">'
            f'<div><strong>Ação:</strong> {escape(action)}</div>'
            f'<div><strong>Origem:</strong> {escape(src_tag)} · <strong>Leitura:</strong> {escape(ts_short)}</div>'
            f'</div></div>'
        )
    equip_cards_html.append("</div>")
    st.markdown("".join(equip_cards_html), unsafe_allow_html=True)

    # Abas operacionais para alta densidade sem poluição visual
    tab_telemetry, tab_alerts, tab_diag = st.tabs(
        [
            "Séries Temporais & Últimas Leituras dos Sensores",
            f"Alertas Ativos & Histórico de Previsões ({len(alerts_items)})",
            "Diagnóstico de Leitura sob Demanda (API)",
        ]
    )

    with tab_telemetry:
        series_rows = view.get("series", [])
        if series_rows:
            series_df = pd.DataFrame(series_rows)
            name, unit, low, high = SENSOR_INFO[selected_sensor]
            chart = px.line(
                series_df,
                x="timestamp",
                y="value",
                color="id_celula" if selected_cell == "Todas" else "data_source",
                title=f"Monitoramento Temporal · {name} ({unit}) — Faixa nominal: [{low} a {high} {unit}]",
                labels={
                    "value": f"{name} ({unit})",
                    "timestamp": "Horário",
                    "id_celula": "Equipamento",
                    "data_source": "Origem",
                },
            )
            chart.add_hrect(
                y0=low,
                y1=high,
                fillcolor="#0B4F9F",
                opacity=0.07,
                line_width=0,
                annotation_text="Faixa operacional nominal",
                annotation_position="top left",
            )
            apply_chart_theme(chart, height=310)
            st.plotly_chart(chart, width="stretch", key="sensor-history")
        else:
            st.info(f"Nenhuma leitura encontrada para a origem '{SOURCE_OPTIONS.get(data_source)}' no filtro atual.")

        st.markdown('<div class="vt-panel-header"><span>Últimas Leituras dos Sensores por Equipamento</span></div>', unsafe_allow_html=True)
        latest_readings = latest_sensors_resp.get("items", [])
        if latest_readings:
            lr_df = pd.DataFrame(latest_readings)
            cols_order = [
                c
                for c in [
                    "id_celula",
                    "timestamp",
                    "liga_metalica",
                    "temperatura_fuso_c",
                    "vibracao_triaxial_rms_mms",
                    "torque_fuso_nm",
                    "vazao_refrigerante_lmin",
                    "corrente_estator_amp",
                    "pressao_hidraulica_bar",
                    "nivel_ruido_db",
                    "data_source",
                ]
                if c in lr_df.columns
            ]
            st.dataframe(
                lr_df[cols_order].rename(
                    columns={
                        "id_celula": "Célula",
                        "timestamp": "Horário",
                        "liga_metalica": "Liga Metálica",
                        "temperatura_fuso_c": "Temp. (°C)",
                        "vibracao_triaxial_rms_mms": "Vibração (mm/s)",
                        "torque_fuso_nm": "Torque (Nm)",
                        "vazao_refrigerante_lmin": "Vazão (L/min)",
                        "corrente_estator_amp": "Corrente (A)",
                        "pressao_hidraulica_bar": "Pressão (bar)",
                        "nivel_ruido_db": "Ruído (dB)",
                        "data_source": "Origem",
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Sem leituras recentes para a origem selecionada.")

    with tab_alerts:
        c_al, c_pr = st.columns([1.15, 1.0], gap="medium")
        with c_al:
            st.markdown('<div class="vt-panel-header"><span>Alertas Operacionais Ordenados por Relevância</span></div>', unsafe_allow_html=True)
            if alerts_items:
                sev_order = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAIXA": 3}
                sorted_alerts = sorted(
                    alerts_items,
                    key=lambda x: (sev_order.get(str(x.get("severity", "")).upper(), 9), str(x.get("timestamp", ""))),
                )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Severidade": a.get("severity"),
                                "Equipamento": a.get("id_celula"),
                                "Condição Detectada": a.get("fault_name"),
                                "Ação Recomendada": a.get("recommended_action"),
                                "Horário": str(a.get("timestamp", ""))[:19].replace("T", " "),
                                "Origem": str(a.get("data_source", "")).upper(),
                            }
                            for a in sorted_alerts
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                    height=300,
                )
            else:
                st.info("Nenhum alerta de falha ativo no banco operacional para o filtro selecionado.")

        with c_pr:
            st.markdown('<div class="vt-panel-header"><span>Histórico de Previsões Persistidas (SQLite)</span></div>', unsafe_allow_html=True)
            hist_items = history_resp.get("items", [])
            if hist_items:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Horário": str(h.get("timestamp", ""))[:19].replace("T", " "),
                                "Célula": h.get("id_celula"),
                                "Liga": h.get("liga_metalica"),
                                "Condição Prevista": h.get("predicted_class_name"),
                                "Ação": h.get("recommended_action"),
                                "Origem": str(h.get("data_source", "")).upper(),
                            }
                            for h in hist_items
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                    height=300,
                )
            else:
                st.info("Nenhuma previsão persistida no SQLite para o filtro selecionado.")

    with tab_diag:
        c_left, c_right = st.columns([1.0, 1.25], gap="medium")
        with c_left:
            dist_rows = view.get("class_distribution", [])
            if dist_rows:
                dist_df = pd.DataFrame(dist_rows).rename(columns={"class_name": "Classe", "count": "Leituras"})
                fig_dist = px.bar(
                    dist_df,
                    x="Classe",
                    y="Leituras",
                    text="Leituras",
                    title="Distribuição das Classes Observadas no Recorte",
                )
                apply_chart_theme(fig_dist, height=290)
                st.plotly_chart(fig_dist, width="stretch", key="fault-distribution")
            else:
                st.info("Sem classes rotuladas para o recorte atual.")

        with c_right:
            st.markdown('<div class="vt-panel-header"><span>Executar Inferência Tabular (POST /api/v1/maintenance/predict)</span></div>', unsafe_allow_html=True)
            selectable = view.get("selectable_records", [])
            if selectable:
                sel_col, btn_col = st.columns([3.0, 1.2], vertical_alignment="bottom")
                with sel_col:
                    idx_choice = st.selectbox(
                        "Selecionar leitura de sensores",
                        range(len(selectable)),
                        format_func=lambda i: (
                            f"{str(selectable[i]['timestamp'])[:19].replace('T', ' ')} · "
                            f"{selectable[i]['id_celula']} · {selectable[i]['liga_metalica']} "
                            f"[{str(selectable[i].get('data_source', 'historical')).upper()}]"
                        ),
                    )
                with btn_col:
                    run_diag = st.button("Classificar", type="primary", width="stretch")

                chosen_row = selectable[idx_choice]
                if run_diag:
                    try:
                        result = predict_sensor_reading(chosen_row, persist=True)
                        st.session_state["last_maint_pred"] = result
                        st.rerun()
                    except (APIConnectionError, APIResponseError) as error:
                        st.error(f"Falha ao classificar registro: {error}")

            pred_result = st.session_state.get("last_maint_pred")
            if pred_result:
                cls_code = pred_result.get("predicted_class_code", 0)
                cls_name = pred_result.get("predicted_class_name", "Normal")
                action = pred_result.get("recommended_action", "MANTER_OPERACAO")
                badge_html = _state_badge(cls_code, cls_name)
                st.markdown(
                    f'<div class="vt-panel">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                    f'<div>{badge_html}</div>'
                    f'<div style="font-size:0.78rem;color:var(--vt-text-secondary);"><strong>Ação recomendada:</strong> {escape(action)}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                scores_map = pred_result.get("scores", {})
                if scores_map:
                    score_frame = pd.DataFrame(
                        {"Classe": list(scores_map.keys()), "Escore": [round(float(v), 4) for v in scores_map.values()]}
                    )
                    fig_sc = px.bar(
                        score_frame,
                        x="Escore",
                        y="Classe",
                        orientation="h",
                        text="Escore",
                        title="Escores Contemporâneos por Classe (Modelo LogisticRegression)",
                    )
                    apply_chart_theme(fig_sc, height=210)
                    st.plotly_chart(fig_sc, width="stretch", key="model-scores")


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Manutenção Preditiva')
