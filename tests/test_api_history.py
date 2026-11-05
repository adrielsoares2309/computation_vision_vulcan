"""Testes unitários da camada de persistência histórica SQLite (PredictionHistory)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from api.history import PredictionHistory


class PredictionHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_history.sqlite3"
        self.history = PredictionHistory(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_database_creation_and_add_reading(self) -> None:
        self.assertTrue(self.db_path.exists())

        reading = {
            "id_celula": "CEL-201",
            "liga_metalica": "Aco_Carbono_316L",
            "temperatura_fuso_c": 55.4,
            "vibracao_triaxial_rms_mms": 1.82,
            "torque_fuso_nm": 62.0,
            "vazao_refrigerante_lmin": 18.0,
        }
        result = {
            "id_celula": "CEL-201",
            "classe_prevista": 0,
            "anomalia": 0,
            "tempo_inferencia_ms": 1.45,
            "probabilidades": [0.98, 0.01, 0.005, 0.005],
        }

        self.history.add(reading, result)
        items = self.history.list(limit=10)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["classe_prevista"], 0)
        self.assertEqual(items[0]["id_celula"], "CEL-201")

    def test_filter_by_equipment_and_stats(self) -> None:
        for cid in ["CEL-201", "CEL-202", "CEL-203"]:
            self.history.add(
                {"id_celula": cid, "temperatura_fuso_c": 50.0},
                {"id_celula": cid, "classe_prevista": 0, "anomalia": 0, "tempo_inferencia_ms": 2.0},
            )

        cel201 = self.history.list(limit=10, equipment_id="CEL-201")
        self.assertEqual(len(cel201), 1)

        stats = self.history.stats()
        self.assertEqual(stats["total_predicoes"], 3)
        self.assertEqual(stats["celulas_ativas"], 3)

