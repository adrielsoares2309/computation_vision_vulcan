"""Testes unitários e de integração do simulador industrial adaptado do AeroMotion."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import simulator as sim


class SimulatorUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime_dir = Path(self.tmp.name)
        self.control_file = self.runtime_dir / "simulator_control.json"
        self.state_file = self.runtime_dir / "simulator_state.json"
        self.lock_file = self.runtime_dir / "simulator.lock"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_regime_and_cells(self) -> None:
        self.assertEqual(sim.DEFAULT_REGIME, "Producao_Normal")
        self.assertEqual(len(sim.CELLS), 4)
        self.assertEqual(len(sim.ALLOYS), 3)
        self.assertEqual(sim.CELL_ALLOY_MAP["CEL-201"], "Aco_Carbono_316L")

    def test_simulator_lock_acquire_and_release(self) -> None:
        lock1 = sim.SimulatorLock(self.lock_file)
        self.assertTrue(lock1.acquire())
        self.assertTrue(lock1.acquired)

        # Segunda tentativa no mesmo lock file deve falhar
        lock2 = sim.SimulatorLock(self.lock_file)
        self.assertFalse(lock2.acquire())

        lock1.release()
        self.assertFalse(lock1.acquired)

        # Após liberar, segundo lock consegue adquirir
        self.assertTrue(lock2.acquire())
        lock2.release()

    def test_control_and_state_atomic_rw(self) -> None:
        sim.write_control("Usinagem_Pesada", action="run", path=self.control_file)
        ctrl = sim.read_control(self.control_file)
        self.assertIsNotNone(ctrl)
        self.assertEqual(ctrl["regime"], "Usinagem_Pesada")
        self.assertEqual(ctrl["action"], "run")

        sim.write_state({"status": "running", "pid": 1234}, path=self.state_file)
        st = sim.read_state(self.state_file)
        self.assertIsNotNone(st)
        self.assertEqual(st["status"], "running")
        self.assertEqual(st["pid"], 1234)

    def test_simulator_step_physics_and_iem(self) -> None:
        telemetry_sim = sim.IndustrialTelemetrySimulator(seed=123, regime="Producao_Normal")
        readings = telemetry_sim.step(dt_s=5.0)

        self.assertEqual(len(readings), 4)
        cell_ids = [r["id_celula"] for r in readings]
        self.assertEqual(cell_ids, list(sim.CELLS))

        for r in readings:
            # Validação física de sensores
            self.assertGreater(r["temperatura_fuso_c"], 20.0)
            self.assertGreater(r["vibracao_triaxial_rms_mms"], 0.0)
            self.assertGreater(r["torque_fuso_nm"], 10.0)
            self.assertGreater(r["vazao_refrigerante_lmin"], 0.0)
            self.assertIn(r["liga_metalica"], sim.ALLOYS)

            # Validação da fórmula industrial do IEM: (Torque * Vibracao) / (Vazao + 1)
            expected_iem = (r["torque_fuso_nm"] * r["vibracao_triaxial_rms_mms"]) / (
                r["vazao_refrigerante_lmin"] + 1.0
            )
            self.assertAlmostEqual(r["indice_esforco_mecanico"], expected_iem, places=2)

    def test_anomaly_injection_profiles(self) -> None:
        telemetry_sim = sim.IndustrialTelemetrySimulator(seed=999, regime="Producao_Normal")

        # Teste Perfil A (Falha de Refrigeração)
        readings_a = telemetry_sim.step(dt_s=5.0, forced_anomaly="A")
        self.assertTrue(any(r["tipo_falha_simulado"] == 2 for r in readings_a))

        # Teste Perfil B (Desgaste de Ferramenta)
        readings_b = telemetry_sim.step(dt_s=5.0, forced_anomaly="B")
        self.assertTrue(any(r["tipo_falha_simulado"] == 1 for r in readings_b))

        # Teste Perfil C (Desalinhamento/Trinca)
        readings_c = telemetry_sim.step(dt_s=5.0, forced_anomaly="C")
        self.assertTrue(any(r["tipo_falha_simulado"] == 3 for r in readings_c))

