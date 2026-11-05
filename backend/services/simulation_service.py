"""Gerenciador seguro do Simulador Industrial em background."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import threading
from typing import Any

from backend.config import Settings, get_settings
from backend.services.oee_service import OEEService
from backend.services.sensor_service import SensorService
from src.simulation.event_generator import generate_simulated_production_event
from src.simulation.sensor_simulator import SIMULATION_MODES, generate_simulated_sensor_reading

logger = logging.getLogger("vulcantech.simulation")


class SimulationService:
    """Controla o ciclo de vida do simulador sem criar processos duplicados nem bloquear o event loop."""

    def __init__(
        self,
        settings: Settings | None = None,
        sensor_service: SensorService | None = None,
        oee_service: OEEService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.sensor_service = sensor_service or SensorService(self.settings)
        self.oee_service = oee_service or OEEService(self.settings)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self._running = False
        self._mode = "MISTO"
        self._interval_seconds = float(self.settings.simulation_interval_seconds)
        self._cycles_completed = 0
        self._started_at_utc: str | None = None
        self._last_cycle_at_utc: str | None = None
        self._last_event: dict[str, Any] | None = None

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            alive = bool(self._worker_thread and self._worker_thread.is_alive() and self._running)
            self._running = alive
            return {
                "running": alive,
                "mode": self._mode,
                "interval_seconds": self._interval_seconds,
                "cycles_completed": self._cycles_completed,
                "started_at_utc": self._started_at_utc,
                "last_cycle_at_utc": self._last_cycle_at_utc,
                "last_event": self._last_event,
                "data_source_tag": "simulated",
            }

    def execute_cycle(
        self,
        mode: str | None = None,
        equipment_id: str | None = None,
    ) -> dict[str, Any]:
        """Executa um único ciclo simulado: gera leitura, classifica via modelo tabular e gera lote OEE."""
        effective_mode = (mode or self._mode).upper().strip()
        if effective_mode not in SIMULATION_MODES:
            raise ValueError(f"Modo inválido: {effective_mode}. Modos válidos: {sorted(SIMULATION_MODES)}.")

        reading = generate_simulated_sensor_reading(mode=effective_mode, equipment_id=equipment_id)
        ingested = self.sensor_service.ingest_reading(reading, run_prediction=True)
        pred = ingested.get("prediction") or {}
        predicted_fault = int(pred.get("predicted_class_code", reading.get("expected_fault_code", 0)))

        prod_event = generate_simulated_production_event(
            equipment_id=reading["id_celula"],
            alloy=reading["liga_metalica"],
            fault_class=predicted_fault,
            planned_time_min=15.0,
        )
        prod_recorded = self.oee_service.record_production_event(prod_event)

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        summary = {
            "cycle_timestamp_utc": now_iso,
            "equipment_id": reading["id_celula"],
            "liga_metalica": reading["liga_metalica"],
            "scenario_mode": reading["scenario_mode"],
            "reading_id": ingested["reading_id"],
            "predicted_class_code": pred.get("predicted_class_code"),
            "predicted_class_name": pred.get("predicted_class_name"),
            "recommended_action": pred.get("recommended_action"),
            "production_event_id": prod_recorded["event_id"],
            "batch_oee": prod_recorded["event_oee"].get("oee"),
            "data_source": "simulated",
        }

        with self._lock:
            self._cycles_completed += 1
            self._last_cycle_at_utc = now_iso
            self._last_event = summary

        return summary

    def _worker_loop(self) -> None:
        logger.info("Worker de simulação iniciado (modo=%s, intervalo=%.1fs).", self._mode, self._interval_seconds)
        while not self._stop_event.is_set():
            try:
                self.execute_cycle()
            except Exception as exc:
                logger.error("Erro no ciclo do simulador: %s", exc)
            if self._stop_event.wait(timeout=self._interval_seconds):
                break
        with self._lock:
            self._running = False
        logger.info("Worker de simulação finalizado.")

    def start(
        self,
        mode: str = "MISTO",
        interval_seconds: float = 5.0,
        generate_initial_batch: int = 4,
    ) -> dict[str, Any]:
        """Inicia o worker de simulação se ainda não estiver ativo e gera lote inicial opcional."""
        clean_mode = mode.upper().strip()
        if clean_mode not in SIMULATION_MODES:
            raise ValueError(f"Modo inválido: {mode}")

        with self._lock:
            self._mode = clean_mode
            self._interval_seconds = max(1.0, min(60.0, float(interval_seconds)))
            already_running = bool(self._worker_thread and self._worker_thread.is_alive() and self._running)

        cells = ["CEL-201", "CEL-202", "CEL-203", "CEL-204"]
        for i in range(max(0, min(20, int(generate_initial_batch)))):
            self.execute_cycle(mode=clean_mode, equipment_id=cells[i % len(cells)])

        with self._lock:
            if not already_running:
                self._stop_event.clear()
                self._running = True
                self._started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="vulcantech-simulator",
                    daemon=True,
                )
                self._worker_thread.start()

        return self.get_status()

    def stop(self) -> dict[str, Any]:
        """Interrompe a thread de simulação com segurança."""
        with self._lock:
            self._stop_event.set()
            thread = self._worker_thread
            self._running = False
        if thread and thread.is_alive():
            thread.join(timeout=3.0)
        return self.get_status()

    def set_mode(self, mode: str) -> dict[str, Any]:
        """Altera o modo operacional do simulador."""
        clean_mode = mode.upper().strip()
        if clean_mode not in SIMULATION_MODES:
            raise ValueError(f"Modo inválido: {mode}. Modos válidos: {sorted(SIMULATION_MODES)}.")
        with self._lock:
            self._mode = clean_mode
        return self.get_status()

