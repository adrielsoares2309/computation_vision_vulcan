"""Cliente HTTP centralizado para comunicação entre o frontend Streamlit e a API FastAPI."""

from __future__ import annotations

import os
from typing import Any

import httpx


class APIConnectionError(RuntimeError):
    """Indica que o servidor FastAPI está inacessível ou excedeu o tempo limite."""


class APIResponseError(RuntimeError):
    """Indica que a API respondeu com um código HTTP de erro (4xx/5xx)."""

    def __init__(self, status_code: int, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details


class VulcanTechAPIClient:
    """Cliente HTTP compartilhado com configuração por variável de ambiente e tratamento padronizado."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        resolved = (base_url or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.base_url = resolved
        self.api_v1_url = f"{self.base_url}/api/v1"
        self.timeout = timeout

    def _extract_error_message(self, response: httpx.Response) -> tuple[str, Any]:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                if "message" in payload:
                    return str(payload["message"]), payload.get("details")
                if "detail" in payload:
                    return str(payload["detail"]), payload
        except Exception:
            pass
        return f"Erro HTTP {response.status_code} ao comunicar com a API.", None

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | list[Any]:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        url = f"{self.base_url}{path}" if path.startswith("/api/") else f"{self.api_v1_url}{path}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}

        try:
            with httpx.Client(timeout=timeout or self.timeout) as client:
                response = client.request(
                    method=method.upper(),
                    url=url,
                    params=clean_params,
                    json=json_body,
                    data=data,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise APIConnectionError(
                f"Tempo limite excedido ao conectar à API ({self.base_url}). Verifique se o backend está em execução."
            ) from exc
        except httpx.RequestError as exc:
            raise APIConnectionError(
                f"API indisponível em {self.base_url}. Inicie o backend FastAPI para carregar os serviços."
            ) from exc

        if response.status_code >= 400:
            msg, details = self._extract_error_message(response)
            raise APIResponseError(status_code=response.status_code, message=msg, details=details)

        try:
            return response.json()
        except ValueError as exc:
            raise APIResponseError(
                status_code=response.status_code,
                message="A API retornou uma resposta que não pôde ser decodificada como JSON.",
            ) from exc

    def get(self, endpoint: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        return self.request("GET", endpoint, params=params, timeout=timeout)

    def post(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        return self.request("POST", endpoint, json_body=json_body, data=data, files=files, timeout=timeout)


def get_api_client() -> VulcanTechAPIClient:
    """Retorna uma instância configurada do cliente HTTP da API."""
    return VulcanTechAPIClient()


def fetch_system_status() -> dict[str, Any]:
    """Consulta o estado completo da API, banco de dados, modelos e simulador."""
    client = get_api_client()
    try:
        data = client.get("/system/status", timeout=4.0)
        return {"api_online": True, **data}
    except APIConnectionError as exc:
        return {"api_online": False, "error": str(exc)}
    except APIResponseError as exc:
        return {"api_online": True, "error": str(exc), "status_code": exc.status_code}

