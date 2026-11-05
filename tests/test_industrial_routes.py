"""Testes de integração para as rotas industriais da API FastAPI."""

from fastapi.testclient import TestClient
import pytest

from backend.main import create_app

client = TestClient(create_app())


def test_root_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_v1_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_industrial_status():
    resp = client.get("/api/v1/industrial/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_celulas" in data
    assert data["total_celulas"] == 4
    assert "detalhes_celulas" in data


def test_industrial_metrics():
    resp = client.get("/api/v1/industrial/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "oee_percentual" in data
    assert "mtbf_horas_estimado" in data


def test_prediction_endpoint():
    payload = {
        "id_celula": "CEL-201",
        "liga_metalica": "Aco_Carbono_316L",
        "temperatura_fuso_c": 52.0,
        "vibracao_triaxial_rms_mms": 1.5,
        "torque_fuso_nm": 105.0,
        "vazao_refrigerante_lmin": 28.0,
        "corrente_estator_amp": 28.5,
        "pressao_hidraulica_bar": 160.0,
        "nivel_ruido_db": 54.0,
    }
    resp = client.post("/api/v1/prediction", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_class_code" in data
    assert "predicted_class_name" in data
    assert "acao_clp_recomendada" in data


def test_anomaly_detection_endpoint():
    payload = {
        "temperatura_fuso_c": 52.0,
        "vibracao_triaxial_rms_mms": 1.5,
        "torque_fuso_nm": 105.0,
        "vazao_refrigerante_lmin": 28.0,
        "corrente_estator_amp": 28.5,
        "pressao_hidraulica_bar": 160.0,
        "nivel_ruido_db": 54.0,
    }
    resp = client.post("/api/v1/anomaly/detection", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "is_anomaly" in data
    assert "anomaly_score" in data
    assert "status" in data


def test_models_metrics_endpoint():
    resp = client.get("/api/v1/models/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "modelo_selecionado" in data
    assert "metricas_teste_final" in data


def test_oee_endpoints():
    # /oee/current
    resp_cur = client.get("/api/v1/oee/current")
    assert resp_cur.status_code == 200

    # /oee/calculate
    resp_calc = client.post("/api/v1/oee/calculate", json={
        "planned_time_min": 480.0,
        "downtime_min": 30.0,
        "ideal_cycle_time_min": 1.0,
        "total_count": 400,
        "good_count": 390,
    })
    assert resp_calc.status_code == 200
    assert resp_calc.json()["available"] is True

    # /oee/impact
    resp_imp = client.post("/api/v1/oee/impact", json={
        "tipo_falha_previsto": 1,
        "probabilidade_falha": 0.85,
        "score_anomalia": 0.70,
    })
    assert resp_imp.status_code == 200
    assert "impacto" in resp_imp.json()
    assert "financeiro" in resp_imp.json()

