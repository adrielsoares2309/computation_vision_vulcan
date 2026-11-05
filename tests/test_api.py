"""Testes de contrato, integração real e segurança para o backend FastAPI VulcanTech."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.config import Settings
from backend.dependencies import reset_container
from backend.main import create_app
from database.db import init_db

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cria um TestClient isolado com banco SQLite temporário e modelos reais do projeto."""
    db_file = tmp_path / "test_vulcantech.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://localhost:8501")
    init_db(db_url)
    reset_container(Settings())
    app = create_app()
    with TestClient(app) as client:
        yield client
    reset_container()


def test_health_readiness_and_openapi_docs(api_client: TestClient):
    r_health = api_client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_ready = api_client.get("/api/v1/ready")
    assert r_ready.status_code == 200
    body = r_ready.json()
    assert body["ready"] is True
    assert body["database_ready"] is True
    assert body["tabular_model_ready"] is True
    assert body["vision_models_ready"] is True

    r_status = api_client.get("/api/v1/system/status")
    assert r_status.status_code == 200
    assert r_status.json()["api_status"] == "online"

    assert api_client.get("/openapi.json").status_code == 200
    assert api_client.get("/docs").status_code == 200


def test_cors_allows_configured_origin_and_blocks_unlisted(api_client: TestClient):
    allowed = api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:8501"

    blocked = api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://malicious.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert blocked.headers.get("access-control-allow-origin") is None


def test_oee_historical_is_unavailable_and_operational_events_calculate_consistently(api_client: TestClient):
    # Fonte histórica não possui dados de produção -> available=False explícito
    hist = api_client.get("/api/v1/oee/summary", params={"data_source": "historical"})
    assert hist.status_code == 200
    assert hist.json()["available"] is False
    assert hist.json()["metrics"]["oee"] is None

    # Intervalo inválido deve retornar 400
    bad_dates = api_client.get(
        "/api/v1/oee/summary",
        params={"data_source": "simulated", "start_date": "2026-11-10", "end_date": "2026-10-01"},
    )
    assert bad_dates.status_code == 400

    # Inserir lote operacional e validar consistência entre summary, history, equipment e downtime
    create_resp = api_client.post(
        "/api/v1/oee/events",
        json={
            "id_celula": "CEL-201",
            "liga_metalica": "Aco_Carbono_316L",
            "shift": "MANHA",
            "planned_time_min": 60.0,
            "downtime_min": 12.0,
            "ideal_cycle_time_min": 0.25,
            "total_count": 160,
            "good_count": 152,
            "downtime_reason": "Ajuste de ferramenta",
            "data_source": "api",
        },
    )
    assert create_resp.status_code == 201

    summary = api_client.get("/api/v1/oee/summary", params={"data_source": "api", "equipment_id": "CEL-201"}).json()
    assert summary["available"] is True
    assert summary["metrics"]["availability"] == 80.0
    assert summary["metrics"]["performance"] == 83.33
    assert summary["metrics"]["quality"] == 95.0
    assert summary["metrics"]["oee"] == 63.33

    history = api_client.get("/api/v1/oee/history", params={"data_source": "api", "equipment_id": "CEL-201"}).json()
    assert history["available"] is True
    assert len(history["series"]) == 1
    assert history["series"][0]["oee"] == 63.33

    downtime = api_client.get("/api/v1/oee/downtime", params={"data_source": "api"}).json()
    assert downtime["available"] is True
    assert downtime["total_downtime_min"] == 12.0


def test_vision_endpoints_real_inference_and_validations(api_client: TestClient):
    meta = api_client.get("/api/v1/vision/metadata")
    assert meta.status_code == 200
    assert meta.json()["experimental"] is True

    img_path = ROOT / "data" / "raw" / "imagens" / "solda_aprovada.png"
    with img_path.open("rb") as f:
        resp = api_client.post(
            "/api/v1/vision/predict",
            data={"modality": "visual", "piece_id": "PECA-TESTE-01"},
            files={"file": ("solda_aprovada.png", f.read(), "image/png")},
        )
    assert resp.status_code == 200
    pred = resp.json()
    assert pred["predicted_class"] in {"APROVADA", "REPROVADA"}
    assert pred["experimental"] is True
    assert pred["validated_for_industrial_use"] is False
    assert pred["piece_id"] == "PECA-TESTE-01"

    hist = api_client.get("/api/v1/vision/history").json()
    assert hist["count"] == 1
    assert hist["items"][0]["piece_id"] == "PECA-TESTE-01"

    # Arquivo corrompido -> 400
    corrupt_resp = api_client.post(
        "/api/v1/vision/predict",
        data={"modality": "visual"},
        files={"file": ("corrupt.png", b"invalid-image-bytes", "image/png")},
    )
    assert corrupt_resp.status_code == 400

    # Extensão não permitida -> 400
    ext_resp = api_client.post(
        "/api/v1/vision/predict",
        data={"modality": "visual"},
        files={"file": ("script.exe", b"1234", "application/octet-stream")},
    )
    assert ext_resp.status_code == 400


def test_vision_oversized_upload_returns_413(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "size_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "128")
    init_db(f"sqlite:///{db_file.as_posix()}")
    reset_container(Settings())
    app = create_app()
    with TestClient(app) as client:
        img_bytes = (ROOT / "data" / "raw" / "imagens" / "solda_aprovada.png").read_bytes()
        resp = client.post(
            "/api/v1/vision/predict",
            data={"modality": "visual"},
            files={"file": ("solda_aprovada.png", img_bytes, "image/png")},
        )
        assert resp.status_code == 413


def test_maintenance_and_sensors_endpoints_with_sentinel_cleaning(api_client: TestClient):
    # Envio de leitura com sentinela documentado (-99.0 em vibração) e falha de refrigeração
    resp = api_client.post(
        "/api/v1/maintenance/predict",
        json={
            "id_celula": "CEL-202",
            "liga_metalica": "Liga_Titanio_Ti6Al4V",
            "temperatura_fuso_c": 96.5,
            "vibracao_triaxial_rms_mms": -99.0,
            "torque_fuso_nm": 150.0,
            "vazao_refrigerante_lmin": 6.2,
            "corrente_estator_amp": 38.0,
            "pressao_hidraulica_bar": 152.0,
            "nivel_ruido_db": 72.0,
            "data_source": "api",
            "persist": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_class_code"] in {0, 1, 2, 3}
    assert data["calibrated_probabilities"] is False
    assert any("Sentinela" in w for w in data["warnings"])

    # Verificar ingestão direta em /sensors/readings
    sens_resp = api_client.post(
        "/api/v1/sensors/readings",
        json={
            "id_celula": "CEL-203",
            "liga_metalica": "Aco_Carbono_316L",
            "temperatura_fuso_c": 52.0,
            "vibracao_triaxial_rms_mms": 1.9,
            "torque_fuso_nm": 110.0,
            "vazao_refrigerante_lmin": 28.0,
            "corrente_estator_amp": 28.0,
            "pressao_hidraulica_bar": 160.0,
            "nivel_ruido_db": 54.0,
            "data_source": "api",
            "run_prediction": True,
        },
    )
    assert sens_resp.status_code == 201
    assert sens_resp.json()["prediction"]["predicted_class_code"] == 0

    # Consultar telemetria da célula
    eq_resp = api_client.get("/api/v1/sensors/equipment/CEL-203", params={"data_source": "api"})
    assert eq_resp.status_code == 200
    assert eq_resp.json()["count"] == 1

    # Validar erro 422 para célula inexistente
    invalid_cell = api_client.post(
        "/api/v1/maintenance/predict",
        json={
            "id_celula": "CEL-999",
            "liga_metalica": "Aco_Carbono_316L",
        },
    )
    assert invalid_cell.status_code == 422


def test_simulation_lifecycle_and_simulated_data_tagging(api_client: TestClient):
    st0 = api_client.get("/api/v1/simulation/status").json()
    assert st0["running"] is False

    step = api_client.post("/api/v1/simulation/step", json={"mode": "DESGASTE_FERRAMENTA", "count": 2})
    assert step.status_code == 200
    step_data = step.json()
    assert step_data["executed_cycles"] == 2
    assert all(ev["data_source"] == "simulated" for ev in step_data["events"])

    # Verificar que os eventos simulados alimentaram o OEE simulado, mas não o histórico
    oee_sim = api_client.get("/api/v1/oee/summary", params={"data_source": "simulated"}).json()
    assert oee_sim["available"] is True
    assert oee_sim["records_count"] == 2

    oee_hist = api_client.get("/api/v1/oee/summary", params={"data_source": "historical"}).json()
    assert oee_hist["available"] is False


def test_unavailable_models_return_503_explicitly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "empty_models.db"
    empty_models = tmp_path / "no_models_here"
    empty_models.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("MODEL_DIR", str(empty_models))
    init_db(f"sqlite:///{db_file.as_posix()}")
    reset_container(Settings())
    app = create_app()
    with TestClient(app) as client:
        ready = client.get("/api/v1/ready")
        assert ready.status_code == 503
        assert ready.json()["ready"] is False

        pred = client.post(
            "/api/v1/maintenance/predict",
            json={
                "id_celula": "CEL-201",
                "liga_metalica": "Aco_Carbono_316L",
                "temperatura_fuso_c": 50.0,
                "vibracao_triaxial_rms_mms": 1.8,
                "torque_fuso_nm": 100.0,
                "vazao_refrigerante_lmin": 28.0,
                "corrente_estator_amp": 25.0,
                "pressao_hidraulica_bar": 160.0,
                "nivel_ruido_db": 55.0,
            },
        )
        assert pred.status_code == 503

