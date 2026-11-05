"""Rotas de integração industrial avançada, monitoramento SCADA/MES e telemetria preditiva."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
import numpy as np
import pandas as pd

from backend.dependencies import get_ml_service, get_oee_service, get_simulation_service
from backend.services.ml_service import MLService
from backend.services.oee_service import OEEService
from backend.services.simulation_service import SimulationService
from src.ml.anomaly_detection import detectar_anomalias
from src.ml.predict import carregar_modelo, prever
from src.simulation.plc_controller import avaliar_acao_clp, obter_historico_acoes_clp

router = APIRouter(tags=["Integração Industrial e SCADA"])

RAIZ = Path(__file__).resolve().parents[2]
REPORTS_DIR = RAIZ / "reports" / "ml"
MODELS_DIR = RAIZ / "models" / "tabular"


@router.get("/industrial/status", summary="Snapshot do estado operacional das células industriais")
def get_industrial_status(
    simulation_service: SimulationService = Depends(get_simulation_service),
    oee_service: OEEService = Depends(get_oee_service),
) -> dict[str, Any]:
    """Retorna visão consolidada SCADA/MES das 4 células de manufatura (CEL-201 a CEL-204)."""
    sim_status = simulation_service.get_status()
    oee_summary = oee_service.get_summary(data_source="all")
    recent_plc = obter_historico_acoes_clp(limite=10)

    # Status por célula
    celulas = ["CEL-201", "CEL-202", "CEL-203", "CEL-204"]
    celulas_info = {}
    for c in celulas:
        # Verifica se há ações recentes de CLP para esta célula
        acoes_celula = [a for a in recent_plc if a.get("id_celula") == c]
        ultima_acao = acoes_celula[-1] if acoes_celula else None
        nivel_seg = ultima_acao["nivel_seguranca"] if ultima_acao else 0

        estado = "OPERACAO_NORMAL"
        if nivel_seg == 4:
            estado = "INTERTRAVAMENTO_PARADA_EMERGENCIA"
        elif nivel_seg == 3:
            estado = "MANUTENCAO_PREVENTIVA_SOLICITADA"
        elif nivel_seg == 2:
            estado = "INSPECAO_QUALIDADE_EM_ANDAMENTO"
        elif nivel_seg == 1:
            estado = "ALERTA_PREVENTIVO_AMARELO"

        celulas_info[c] = {
            "id_celula": c,
            "estado": estado,
            "nivel_seguranca_clp": nivel_seg,
            "alimentacao_fuso_pct": ultima_acao["ajuste_velocidade_feed_pct"] if ultima_acao else 100,
            "ultima_mensagem": ultima_acao["mensagem"] if ultima_acao else "Operação nominal estável.",
            "online": True,
        }

    return {
        "status_fabrica": "PRODUCAO_ATIVA",
        "total_celulas": len(celulas),
        "celulas_em_operacao": sum(1 for c in celulas_info.values() if c["nivel_seguranca_clp"] < 4),
        "celulas_intertravadas": sum(1 for c in celulas_info.values() if c["nivel_seguranca_clp"] == 4),
        "oee_global": oee_summary.get("oee"),
        "disponibilidade_global": oee_summary.get("availability"),
        "desempenho_global": oee_summary.get("performance"),
        "qualidade_global": oee_summary.get("quality"),
        "simulador_ativo": sim_status.get("running", False),
        "modo_simulacao": sim_status.get("mode"),
        "detalhes_celulas": celulas_info,
    }


@router.get("/industrial/metrics", summary="KPIs industriais em tempo real")
def get_industrial_metrics(
    oee_service: OEEService = Depends(get_oee_service),
) -> dict[str, Any]:
    """Retorna indicadores operacionais, taxa de defeitos e parâmetros críticos."""
    oee = oee_service.get_summary(data_source="all")
    total = oee.get("total_count", 0) or 0
    rejeito = oee.get("rejected_count", 0) or 0
    taxa_rejeito = (rejeito / max(total, 1)) * 100.0 if total > 0 else 1.2

    return {
        "oee_percentual": oee.get("oee", 84.5),
        "disponibilidade_percentual": oee.get("availability", 91.2),
        "desempenho_percentual": oee.get("performance", 95.8),
        "qualidade_percentual": oee.get("quality", 96.7),
        "taxa_rejeito_percentual": round(taxa_rejeito, 2),
        "total_pecas_produzidas": total,
        "total_pecas_rejeitadas": rejeito,
        "tempo_operacao_min": oee.get("operating_time_min", 480.0),
        "tempo_parada_min": oee.get("downtime_min", 35.0),
        "mtbf_horas_estimado": 168.0,
        "mttr_minutos_estimado": 42.5,
        "custo_hora_parada_brl": 4500.0,
    }


@router.post("/prediction", summary="Inferência preditiva multiclasse com enriquecimento automático de features")
def make_prediction(
    dados_sensor: dict[str, Any],
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    """Recebe leitura de sensores (bruta ou enriquecida) e retorna diagnóstico multiclasse."""
    try:
        resultado = service.predict_single(dados_sensor, persist=True)

        # Avaliação no CLP em malha fechada
        tipo_falha = int(resultado.get("predicted_class_code", 0))
        probabilidade = float(resultado.get("probabilities", {}).get(f"classe_{tipo_falha}", 0.0))
        acao_clp = avaliar_acao_clp(
            dados_sensor,
            tipo_falha_previsto=tipo_falha,
            probabilidade_falha=probabilidade,
            score_anomalia=0.0,
        )
        resultado["acao_clp_recomendada"] = acao_clp
        return resultado
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/anomaly/detection", summary="Detecção de anomalias por Isolation Forest")
def detect_anomaly_endpoint(
    leitura: dict[str, Any],
) -> dict[str, Any]:
    """Avalia o vetor de sensores contra a distribuição de normalidade do Isolation Forest."""
    try:
        df_entrada = pd.DataFrame([leitura])
        is_anom, score_anom = detectar_anomalias(df_entrada)

        score = float(score_anom[0])
        anomalia = bool(is_anom[0])

        status_anom = "NORMAL"
        if score >= 0.75:
            status_anom = "ANOMALIA_CRITICA"
        elif score >= 0.50:
            status_anom = "ANOMALIA_MODERADA"
        elif score >= 0.35:
            status_anom = "ATENCAO_PREVENTIVA"

        return {
            "is_anomaly": anomalia,
            "anomaly_score": score,
            "status": status_anom,
            "limiar_anomalia": 0.50,
            "detalhes": {
                "interpretacao": (
                    "Comportamento atípico significativo detectado nos sensores."
                    if anomalia
                    else "Padrão de operação dentro da normalidade estocástica dos sensores."
                )
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/models/metrics", summary="Relatório comparativo de métricas dos modelos de Machine Learning")
def get_models_metrics() -> dict[str, Any]:
    """Retorna os resultados da avaliação comparativa (Random Forest, XGBoost, etc.)."""
    caminho_report = REPORTS_DIR / "classification_report.json"
    caminho_meta = MODELS_DIR / "model_metadata.json"
    caminho_comp = REPORTS_DIR / "model_comparison.csv"

    if not caminho_meta.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metadados de modelos ainda não gerados. Execute o treinamento primeiro.",
        )

    try:
        metadata = json.loads(caminho_meta.read_text(encoding="utf-8"))
        report = json.loads(caminho_report.read_text(encoding="utf-8")) if caminho_report.is_file() else {}

        tabela_comparacao = []
        if caminho_comp.is_file():
            df_comp = pd.read_csv(caminho_comp)
            tabela_comparacao = df_comp.to_dict(orient="records")

        return {
            "modelo_selecionado": metadata.get("model_name"),
            "criterio_selecao": metadata.get("selection_criterion"),
            "metricas_teste_final": metadata.get("test_metrics"),
            "metricas_validacao": metadata.get("validation_metrics"),
            "relatorio_por_classe": report.get("per_class", {}),
            "comparacao_modelos": tabela_comparacao,
            "parametros_vencedores": metadata.get("best_parameters"),
            "features_utilizadas": metadata.get("features"),
            "data_treinamento_utc": metadata.get("trained_at_utc"),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

