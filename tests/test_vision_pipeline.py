"""Testes determinísticos do pipeline visual unificado adaptado do AeroMotion para VulcanTech."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import vision
from vision.geometry import (
    GeometryConfig,
    analyze_geometry,
    contour_features,
    load_image,
)
from vision.pipeline import (
    diagnose_image_dataset,
    discover_images,
    predict_image,
    process_batch,
    process_image,
)
from vision.thermal import (
    ThermalConfig,
    analyze_thermal,
    classify_thermal_against_references,
)


class VisionGeometryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.image = np.zeros((120, 120, 3), dtype=np.uint8)
        # Desenha cordão de solda e poro circular
        cv2.rectangle(self.image, (20, 45), (100, 75), (200, 200, 200), -1)
        cv2.circle(self.image, (60, 60), 6, (0, 0, 0), -1)
        self.path = self.root / "solda_teste.png"
        cv2.imwrite(str(self.path), self.image)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_valid_and_missing_image(self) -> None:
        self.assertEqual(load_image(self.path).shape, self.image.shape)
        with self.assertRaises(ValueError):
            load_image(self.root / "inexistente.png")

    def test_gray_edges_contours_and_features(self) -> None:
        result = analyze_geometry(self.path)
        self.assertEqual((result["width"], result["height"], result["channels"]), (120, 120, 3))
        self.assertGreater(result["contour_count"], 0)
        feature = result["contours"][0]
        self.assertGreater(feature["area"], 0)
        self.assertGreater(feature["perimeter"], 0)
        self.assertIsNotNone(feature["circularity"])
        self.assertIsNotNone(feature["centroid"])
        self.assertGreaterEqual(feature["aspect_ratio"], 0)

    def test_array_input_returns_artifacts_without_persisting(self) -> None:
        result = analyze_geometry(self.image, include_artifacts=True)
        self.assertEqual(result["path"], "<imagem em memória>")
        self.assertTrue({"gray", "edges", "contours", "annotated"}.issubset(result["artifacts"]))
        self.assertFalse(result["outputs"])

    def test_blank_image_returns_zero_contours(self) -> None:
        blank = np.zeros((50, 50, 3), dtype=np.uint8)
        res = analyze_geometry(blank)
        self.assertEqual(res["contour_count"], 0)


class VisionThermalContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Cria imagem com hotspot vermelho no espaço BGR
        self.thermal_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.thermal_img[30:70, 30:70] = (0, 0, 240)  # BGR vermelho intenso
        self.path = self.root / "termica_teste.png"
        cv2.imwrite(str(self.path), self.thermal_img)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_thermal_segmentation_and_mask_fraction(self) -> None:
        res = analyze_thermal(self.path, include_artifacts=True)
        self.assertGreater(res["mask_fraction"], 0.10)
        self.assertGreater(res["zac_area_pct"], 10.0)
        self.assertGreater(res["estimated_peak_c"], 100.0)
        self.assertIn("mask", res["artifacts"])
        self.assertIn("annotated", res["artifacts"])

    def test_thermal_classification_against_references(self) -> None:
        res = classify_thermal_against_references(self.thermal_img)
        self.assertIn(res["status"], ["APROVADA", "REPROVADA"])
        self.assertGreater(res["confidence"], 0.5)


class VisionPipelineBatchTests(unittest.TestCase):
    def test_discover_images_and_process_batch(self) -> None:
        supported, unsupported = discover_images()
        self.assertGreaterEqual(len(supported), 4)
        summary = process_batch()
        self.assertEqual(summary["processed"], len(supported))
        self.assertGreater(summary["geometric_images"], 0)
        self.assertGreater(summary["thermal_images"], 0)

    def test_predict_image_in_memory(self) -> None:
        test_img = np.zeros((80, 80, 3), dtype=np.uint8)
        pred_geo = predict_image(test_img, image_type="geometrica")
        self.assertTrue(pred_geo["available"])
        self.assertEqual(pred_geo["type"], "geometrica")

        pred_therm = predict_image(test_img, image_type="termica")
        self.assertTrue(pred_therm["available"])
        self.assertEqual(pred_therm["type"], "termica")

