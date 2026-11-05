"""Simulador industrial contínuo com física de primeira ordem, inércia térmica e CLP fechado.

Desenvolvido para o ecossistema VulcanTech Smart Metals S.A. com base na arquitetura
de referência do AeroMotion Dynamics:
- Process Lock exclusivo de instância (msvcrt / fcntl)
- Arquivo de controle atômico: data/runtime/simulator_control.json
- Heartbeat e telemetria: data/runtime/simulator_state.json
- Inércia física de primeira ordem com ruído estocástico AR(1)
- Três regimes operacionais industriais: Producao_Normal, Usinagem_Pesada, Alta_Velocidade
- Quatro células industriais: CEL-201, CEL-202, CEL-203, CEL-204
- Três ligas metálicas nobres: Aco_Carbono_316L, Aluminio_7075, Liga_Titanio_Ti6Al4V
- Injeção determinística de perfis de anomalia A (Térmica), B (Desgaste IEM), C (Trinca/Desalinhamento)
- Integração bidirecional com a API FastAPI e persistência no banco SQLite.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests

try:  # Windows
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]
    import fcntl

ROOT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.getenv("VULCANTECH_RUNTIME_DIR", str(ROOT_DIR / "data" / "runtime")))
CONTROL_FILE = RUNTIME_DIR / "simulator_control.json"
STATE_FILE = RUNTIME_DIR / "simulator_state.json"
LOCK_FILE = RUNTIME_DIR / "simulator.lock"

REGIMES = ("Producao_Normal", "Usinagem_Pesada", "Alta_Velocidade")
REGIME_LABELS = {
    "Producao_Normal": "Produção Normal (Nominal)",
    "Usinagem_Pesada": "Usinagem Pesada (Alto Torque)",
    "Alta_Velocidade": "Alta Velocidade (Crítico)",
}
DEFAULT_REGIME = "Producao_Normal"

CELLS = ("CEL-201", "CEL-202", "CEL-203", "CEL-204")
ALLOYS = ("Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V")

CELL_ALLOY_MAP = {
    "CEL-201": "Aco_Carbono_316L",
    "CEL-202": "Aluminio_7075",
    "CEL-203": "Liga_Titanio_Ti6Al4V",
    "CEL-204": "Liga_Titanio_Ti6Al4V",
}

SENSOR_FIELDS = (
    "temperatura_fuso_c",
    "vibracao_triaxial_rms_mms",
    "torque_fuso_nm",
    "vazao_refrigerante_lmin",
    "corrente_estator_amp",
    "pressao_hidraulica_bar",
    "nivel_ruido_db",
)

SENSOR_LIMITS = {
    "temperatura_fuso_c": (35.0, 85.0),
    "vibracao_triaxial_rms_mms": (0.8, 6.0),
    "torque_fuso_nm": (30.0, 135.0),
    "vazao_refrigerante_lmin": (5.0, 30.0),
    "corrente_estator_amp": (12.0, 50.0),
    "pressao_hidraulica_bar": (40.0, 85.0),
    "nivel_ruido_db": (55.0, 88.0),
}

REGIME_PROFILES: dict[str, dict[str, float]] = {
    "Producao_Normal": {
        "load_index": 0.40,
        "temperatura_fuso_c": 52.4,
        "vibracao_triaxial_rms_mms": 1.75,
        "torque_fuso_nm": 58.2,
        "vazao_refrigerante_lmin": 19.5,
        "corrente_estator_amp": 22.1,
        "pressao_hidraulica_bar": 56.0,
        "nivel_ruido_db": 68.5,
        "noise_scale": 1.0,
    },
    "Usinagem_Pesada": {
        "load_index": 0.75,
        "temperatura_fuso_c": 64.8,
        "vibracao_triaxial_rms_mms": 2.85,
        "torque_fuso_nm": 86.4,
        "vazao_refrigerante_lmin": 16.0,
        "corrente_estator_amp": 32.5,
        "pressao_hidraulica_bar": 65.0,
        "nivel_ruido_db": 76.2,
        "noise_scale": 1.25,
    },
    "Alta_Velocidade": {
        "load_index": 0.95,
        "temperatura_fuso_c": 74.5,
        "vibracao_triaxial_rms_mms": 3.90,
        "torque_fuso_nm": 98.0,
        "vazao_refrigerante_lmin": 14.5,
        "corrente_estator_amp": 41.2,
        "pressao_hidraulica_bar": 72.0,
        "nivel_ruido_db": 82.0,
        "noise_scale": 1.50,
    },
}

REGIME_CONFIG: dict[str, dict[str, Any]] = {
    "Producao_Normal": {
        "nominal_ratio": 0.95,
        "anomaly_ratio": 0.05,
        "block_size": 20,
        "anomaly_intensity": 0.35,
        "anomaly_weights": {"A": 0.35, "B": 0.45, "C": 0.20},
    },
    "Usinagem_Pesada": {
        "nominal_ratio": 0.70,
        "anomaly_ratio": 0.30,
        "block_size": 10,
        "anomaly_intensity": 0.70,
        "anomaly_weights": {"A": 0.30, "B": 0.45, "C": 0.25},
    },
    "Alta_Velocidade": {
        "nominal_ratio": 0.40,
        "anomaly_ratio": 0.60,
        "block_size": 5,
        "anomaly_intensity": 1.00,
        "anomaly_weights": {"A": 0.35, "B": 0.35, "C": 0.30},
    },
}

ANOMALY_PROFILE_LABELS = {
    "A": "Falha de Refrigeração (Sobreaquecimento)",
    "B": "Desgaste Acelerado da Ferramenta (IEM Crítico)",
    "C": "Desalinhamento Mecânico / Trinca Estrutural",
}

ANOMALY_PROFILE_DELTAS: dict[str, dict[str, dict[str, float]]] = {
    "Producao_Normal": {
        "A": {"temperatura_fuso_c": 31.0, "vazao_refrigerante_lmin": -13.5},
        "B": {"torque_fuso_nm": 42.0, "vibracao_triaxial_rms_mms": 3.2},
        "C": {
            "vibracao_triaxial_rms_mms": 4.1,
            "nivel_ruido_db": 14.5,
            "corrente_estator_amp": 12.0,
        },
    },
    "Usinagem_Pesada": {
        "A": {"temperatura_fuso_c": 34.5, "vazao_refrigerante_lmin": -14.0},
        "B": {"torque_fuso_nm": 48.0, "vibracao_triaxial_rms_mms": 3.6},
        "C": {
            "vibracao_triaxial_rms_mms": 4.5,
            "nivel_ruido_db": 15.0,
            "corrente_estator_amp": 14.0,
        },
    },
    "Alta_Velocidade": {
        "A": {"temperatura_fuso_c": 36.0, "vazao_refrigerante_lmin": -14.5},
        "B": {"torque_fuso_nm": 52.0, "vibracao_triaxial_rms_mms": 4.0},
        "C": {
            "vibracao_triaxial_rms_mms": 4.8,
            "nivel_ruido_db": 16.2,
            "corrente_estator_amp": 15.5,
        },
    },
}

TAU_LOAD_S = 20.0
TAU_TEMP_S = 28.0
TAU_VIB_S = 14.0
AR1_PHI = 0.65


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


class SimulatorLock:
    """Lock exclusivo de processo para impedir instâncias simultâneas do simulador."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or LOCK_FILE
        self._handle: Any = None
        self.acquired = False

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        try:
            if msvcrt is not None:
                self._handle.seek(0)
                if self.path.stat().st_size == 0:
                    self._handle.write("1")
                    self._handle.flush()
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.acquired = True
        except OSError:
            self.acquired = False
        return self.acquired

    def release(self) -> None:
        if not self._handle:
            return
        try:
            if self.acquired:
                if msvcrt is not None:
                    self._handle.seek(0)
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
            self.acquired = False


def read_control(path: Path | None = None) -> dict[str, Any] | None:
    return _read_json(path or CONTROL_FILE)


def write_control(
    regime: str,
    action: str = "run",
    path: Path | None = None,
    requested_by: str = "dashboard",
) -> dict[str, Any]:
    current = read_control(path) or {}
    payload = {
        "regime": regime if regime in REGIMES else DEFAULT_REGIME,
        "action": action,
        "requested_by": requested_by,
        "updated_at": _now_iso(),
        "previous_regime": current.get("regime"),
    }
    _atomic_write_json(path or CONTROL_FILE, payload)
    return payload


def write_state(state: dict[str, Any], path: Path | None = None) -> None:
    _atomic_write_json(path or STATE_FILE, state)


def read_state(path: Path | None = None) -> dict[str, Any] | None:
    return _read_json(path or STATE_FILE)


def simulator_status(
    *,
    control_path: Path | None = None,
    state_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Une comando e heartbeat em um status consumível pela API/dashboard."""
    control = read_control(control_path) or {}
    state = read_state(state_path) or {}
    reference = now or datetime.now()

    selected = control.get("regime")
    if selected not in REGIMES:
        selected = state.get("regime") if state.get("regime") in REGIMES else DEFAULT_REGIME

    interval = float(state.get("interval_seconds") or 5.0)
    last_cycle_str = state.get("last_cycle_at")
    last_cycle = datetime.fromisoformat(last_cycle_str) if last_cycle_str else None
    age = None
    online = False
    if state.get("status") == "running" and last_cycle is not None:
        age = max(0.0, (reference - last_cycle).total_seconds())
        online = age <= max(15.0, interval * 2.0 + 5.0)

    return {
        "regimes_disponiveis": list(REGIMES),
        "rotulos": dict(REGIME_LABELS),
        "regime_selecionado": selected,
        "regime_ativo": state.get("regime") if online else None,
        "simulador_online": online,
        "status_simulador": state.get("status", "parado"),
        "ultimo_ciclo": state.get("last_cycle_at"),
        "idade_ultimo_ciclo_s": round(age, 1) if age is not None else None,
        "intervalo_segundos": interval,
        "pid": state.get("pid"),
        "origem": "simulada",
        "atualizado_em": _now_iso(),
    }


def request_regime(regime: str) -> dict[str, Any]:
    if regime not in REGIMES:
        raise ValueError(f"Regime inválido: {regime}. Aceitos: {', '.join(REGIMES)}")
    write_control(regime, action="run", requested_by="api")
    return simulator_status()


@dataclass
class CellPhysicalState:
    cell_id: str
    alloy: str
    load_actual: float = 0.40
    temp_actual: float = 52.0
    vib_actual: float = 1.7
    torque_actual: float = 58.0
    flow_actual: float = 19.5
    current_actual: float = 22.0
    press_actual: float = 56.0
    noise_actual: float = 68.0
    ar1_noise: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ar1_noise:
            self.ar1_noise = {field: 0.0 for field in SENSOR_FIELDS}


class IndustrialTelemetrySimulator:
    """Simulador de telemetria multicélula com inércia, ruído AR(1) e injeção de falhas."""

    def __init__(self, seed: int = 42, regime: str = DEFAULT_REGIME) -> None:
        self.rng = np.random.default_rng(seed)
        self.regime = regime if regime in REGIMES else DEFAULT_REGIME
        self.cells = {
            cid: CellPhysicalState(cell_id=cid, alloy=CELL_ALLOY_MAP[cid])
            for cid in CELLS
        }
        self.cycle_count = 0

    def step(
        self,
        dt_s: float = 5.0,
        forced_anomaly: str | None = None,
    ) -> list[dict[str, Any]]:
        self.cycle_count += 1
        readings = []
        reg_prof = REGIME_PROFILES[self.regime]
        target_load = reg_prof["load_index"]
        alpha_load = 1.0 - math.exp(-dt_s / TAU_LOAD_S)
        alpha_temp = 1.0 - math.exp(-dt_s / TAU_TEMP_S)
        alpha_vib = 1.0 - math.exp(-dt_s / TAU_VIB_S)

        # Determina perfil de anomalia se houver
        cfg = REGIME_CONFIG[self.regime]
        is_anomaly = (
            (self.rng.random() < cfg["anomaly_ratio"])
            if forced_anomaly is None
            else bool(forced_anomaly)
        )
        anomaly_type = forced_anomaly
        if is_anomaly and anomaly_type is None:
            weights = cfg["anomaly_weights"]
            anomaly_type = self.rng.choice(
                list(weights.keys()), p=list(weights.values())
            )

        deltas = (
            ANOMALY_PROFILE_DELTAS[self.regime].get(anomaly_type, {})
            if is_anomaly and anomaly_type
            else {}
        )

        for cell_id, state in self.cells.items():
            # Inércia de carga
            state.load_actual += (target_load - state.load_actual) * alpha_load

            # Metas nominais
            target_temp = reg_prof["temperatura_fuso_c"] + deltas.get("temperatura_fuso_c", 0.0)
            target_vib = reg_prof["vibracao_triaxial_rms_mms"] + deltas.get("vibracao_triaxial_rms_mms", 0.0)
            target_torque = reg_prof["torque_fuso_nm"] + deltas.get("torque_fuso_nm", 0.0)
            target_flow = max(
                3.0,
                reg_prof["vazao_refrigerante_lmin"] + deltas.get("vazao_refrigerante_lmin", 0.0),
            )
            target_current = reg_prof["corrente_estator_amp"] + deltas.get("corrente_estator_amp", 0.0)
            target_press = reg_prof["pressao_hidraulica_bar"] + deltas.get("pressao_hidraulica_bar", 0.0)
            target_noise = reg_prof["nivel_ruido_db"] + deltas.get("nivel_ruido_db", 0.0)

            # Inércia física
            state.temp_actual += (target_temp - state.temp_actual) * alpha_temp
            state.vib_actual += (target_vib - state.vib_actual) * alpha_vib
            state.torque_actual += (target_torque - state.torque_actual) * alpha_vib
            state.flow_actual += (target_flow - state.flow_actual) * 0.35
            state.current_actual += (target_current - state.current_actual) * 0.40
            state.press_actual += (target_press - state.press_actual) * 0.25
            state.noise_actual += (target_noise - state.noise_actual) * 0.35

            # Ruído estocástico AR(1)
            noise_scale = reg_prof["noise_scale"]
            for field in SENSOR_FIELDS:
                white = float(self.rng.normal(0, 0.4 * noise_scale))
                state.ar1_noise[field] = AR1_PHI * state.ar1_noise[field] + white

            # Valores finais dos sensores
            temp = float(np.clip(state.temp_actual + state.ar1_noise["temperatura_fuso_c"] * 0.4, 25.0, 115.0))
            vib = float(np.clip(state.vib_actual + state.ar1_noise["vibracao_triaxial_rms_mms"] * 0.15, 0.4, 12.0))
            torque = float(np.clip(state.torque_actual + state.ar1_noise["torque_fuso_nm"] * 0.6, 15.0, 160.0))
            flow = float(np.clip(state.flow_actual + state.ar1_noise["vazao_refrigerante_lmin"] * 0.2, 1.0, 35.0))
            current = float(np.clip(state.current_actual + state.ar1_noise["corrente_estator_amp"] * 0.3, 8.0, 65.0))
            press = float(np.clip(state.press_actual + state.ar1_noise["pressao_hidraulica_bar"] * 0.3, 30.0, 95.0))
            noise = float(np.clip(state.noise_actual + state.ar1_noise["nivel_ruido_db"] * 0.4, 45.0, 98.0))

            iem = (torque * vib) / (flow + 1.0)
            tipo_falha_real = 0
            if is_anomaly:
                if anomaly_type == "B":
                    tipo_falha_real = 1  # Desgaste de Ferramenta
                elif anomaly_type == "A":
                    tipo_falha_real = 2  # Falha de Refrigeração
                elif anomaly_type == "C":
                    tipo_falha_real = 3  # Desalinhamento / Trinca

            reading = {
                "timestamp": _now_iso(),
                "id_celula": cell_id,
                "liga_metalica": state.alloy,
                "modo_operacao": self.regime,
                "regime_operacional": self.regime,
                "temperatura_fuso_c": round(temp, 2),
                "vibracao_triaxial_rms_mms": round(vib, 3),
                "torque_fuso_nm": round(torque, 2),
                "vazao_refrigerante_lmin": round(flow, 2),
                "corrente_estator_amp": round(current, 2),
                "pressao_hidraulica_bar": round(press, 2),
                "nivel_ruido_db": round(noise, 2),
                "indice_esforco_mecanico": round(iem, 3),
                "origem_leitura": "simulada",
                "tipo_falha_simulado": tipo_falha_real,
                "perfil_anomalia": anomaly_type if is_anomaly else "nominal",
            }
            readings.append(reading)

        return readings


def run_simulator_loop(
    api_url: str = "http://127.0.0.1:8000",
    interval_s: float = 5.0,
    max_cycles: int = 0,
    regime: str = DEFAULT_REGIME,
) -> None:
    """Loop contínuo de execução do simulador com controle de concorrência."""
    lock = SimulatorLock()
    if not lock.acquire():
        print(f"Erro: Instância do simulador já está em execução (lock ativo em {LOCK_FILE}).")
        sys.exit(1)

    print(f"[{_now_iso()}] Simulador VulcanTech iniciado (PID: {os.getpid()}).")
    print(f"  -> Conectado a: {api_url}")
    print(f"  -> Intervalo: {interval_s}s | Regime: {regime}")

    sim = IndustrialTelemetrySimulator(regime=regime)
    cycles = 0

    try:
        write_control(regime, action="run", requested_by="startup")
        while True:
            # Checa se houve solicitação externa de parada ou troca de regime
            ctrl = read_control()
            if ctrl:
                if ctrl.get("action") == "stop":
                    print(f"[{_now_iso()}] Parada solicitada via simulator_control.json.")
                    break
                new_regime = ctrl.get("regime")
                if new_regime in REGIMES and new_regime != sim.regime:
                    print(f"[{_now_iso()}] Transição de regime: {sim.regime} -> {new_regime}")
                    sim.regime = new_regime

            # Gera leitura das 4 células
            readings = sim.step(dt_s=interval_s)
            cycles += 1

            # Publica telemetria na API se disponível
            try:
                for r in readings:
                    requests.post(
                        f"{api_url}/api/v1/telemetry",
                        json=r,
                        timeout=1.5,
                    )
            except Exception:
                pass  # Permite que o simulador continue gerando estado mesmo se API estiver offline

            # Atualiza heartbeat no simulator_state.json
            write_state(
                {
                    "status": "running",
                    "pid": os.getpid(),
                    "regime": sim.regime,
                    "interval_seconds": interval_s,
                    "last_cycle_at": _now_iso(),
                    "cycle_count": cycles,
                    "api_url": api_url,
                    "last_readings": readings,
                }
            )

            if max_cycles > 0 and cycles >= max_cycles:
                print(f"[{_now_iso()}] Limite de {max_cycles} ciclos atingido. Encerrando.")
                break

            time.sleep(interval_s)

    finally:
        write_state(
            {
                "status": "stopped",
                "pid": os.getpid(),
                "regime": sim.regime,
                "interval_seconds": interval_s,
                "last_cycle_at": _now_iso(),
                "cycle_count": cycles,
            }
        )
        lock.release()
        print(f"[{_now_iso()}] Simulador VulcanTech encerrado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador Industrial VulcanTech Smart Metals S.A.")
    parser.add_argument("--api-url", default=os.getenv("VULCANTECH_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--quantidade", type=int, default=0, help="0 para contínuo")
    parser.add_argument("--regime", choices=list(REGIMES), default=DEFAULT_REGIME)
    args = parser.parse_args()

    run_simulator_loop(
        api_url=args.api_url,
        interval_s=args.intervalo,
        max_cycles=args.quantidade,
        regime=args.regime,
    )

