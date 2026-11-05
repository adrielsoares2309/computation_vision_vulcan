"""Testes para o cliente HTTP centralizado, serviços do frontend e conformidade de contraste WCAG 2.2."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest

from backend.config import Settings
from backend.dependencies import reset_container
from backend.main import create_app
from database.db import init_db
from frontend.services.api_client import (
    APIConnectionError,
    APIResponseError,
    VulcanTechAPIClient,
    fetch_system_status,
)
from frontend.services.ml_service import (
    get_equipment_overview,
    get_latest_sensor_readings,
    get_maintenance_sensors_view,
    get_sensor_metadata,
    predict_sensor_reading,
)
from frontend.services.oee_service import get_oee_snapshot, step_simulation
from frontend.services.vision_service import get_vision_metadata, inspect_sample_image, list_sample_images
from frontend.styles import render_status_badge, verify_all_token_contrasts


def test_wcag_22_design_tokens_contrast_compliance():
    """Garante que todas as combinações de cores dos Design Tokens cumprem os mínimos da WCAG 2.2."""
    results = verify_all_token_contrasts()
    assert len(results) >= 25
    failures = [r for r in results if not r["passed"]]
    assert not failures, f"Combinações com contraste insuficiente WCAG 2.2: {failures}"

    badge_html = render_status_badge("APROVADA", tone="success", icon="check_circle")
    assert "vt-badge-success" in badge_html
    assert "<svg" in badge_html
    assert "APROVADA" in badge_html


def test_client_raises_connection_error_when_api_is_offline(monkeypatch: pytest.MonkeyPatch):
    def mock_connect_fail(self, method: str, url: str, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "request", mock_connect_fail)
    client = VulcanTechAPIClient(base_url="http://127.0.0.1:59999", timeout=0.5)
    with pytest.raises(APIConnectionError, match="API indisponível"):
        client.get("/health")

    status = fetch_system_status()
    assert status["api_online"] is False
    assert "indisponível" in status["error"]


def test_client_parses_structured_http_error(monkeypatch: pytest.MonkeyPatch):
    def mock_request(self, method: str, url: str, **kwargs):
        return httpx.Response(
            status_code=400,
            json={"code": "bad_request", "message": "Intervalo inválido."},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(httpx.Client, "request", mock_request)
    client = VulcanTechAPIClient(base_url="http://127.0.0.1:8000")
    with pytest.raises(APIResponseError) as exc_info:
        client.get("/oee/summary")
    assert exc_info.value.status_code == 400
    assert "Intervalo inválido" in exc_info.value.message


def test_frontend_services_integrate_with_backend_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "fe_integration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    init_db(f"sqlite:///{db_file.as_posix()}")
    reset_container(Settings())
    app = create_app()

    with TestClient(app) as tc:
        class _TestClientAdapter:
            def __init__(self, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def request(self, method: str, url: str, **kwargs):
                path = str(url).replace("http://127.0.0.1:8000", "")
                return tc.request(method, path, **kwargs)

        monkeypatch.setattr("frontend.services.api_client.httpx.Client", _TestClientAdapter)

        sys_st = fetch_system_status()
        assert sys_st["api_online"] is True

        v_meta = get_vision_metadata()
        assert v_meta["experimental"] is True

        samples = list_sample_images()
        assert len(samples) >= 4
        insp = inspect_sample_image(samples[0], modality="visual", piece_id="TEST-01")
        assert insp["predicted_class"] in {"APROVADA", "REPROVADA"}

        m_meta = get_sensor_metadata()
        assert m_meta["model_name"] in {"LogisticRegression", "RandomForestClassifier", "XGBClassifier"}

        view = get_maintenance_sensors_view(equipment_id="CEL-201", data_source="historical", limit=50)
        assert view["kpis"]["readings_in_period"] > 0
        sample = view["selectable_records"][0]
        pred = predict_sensor_reading(sample, persist=True)
        assert "predicted_class_name" in pred

        eq_ov = get_equipment_overview(data_source="all")
        assert len(eq_ov["equipment"]) == 4

        latest_sens = get_latest_sensor_readings(data_source="all")
        assert latest_sens["count"] == 4

        step_simulation(mode="NORMAL", count=2)
        oee_sim = get_oee_snapshot(data_source="simulated")
        assert oee_sim["available"] is True
        assert oee_sim["metrics"]["oee"] is not None

        sim_view = get_maintenance_sensors_view(data_source="simulated", limit=50)
        assert sim_view["kpis"]["readings_in_period"] >= 2
