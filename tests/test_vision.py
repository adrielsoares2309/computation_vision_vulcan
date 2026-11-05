"""Functional checks for image inspection; these do not assess generalization."""

import json
from pathlib import Path

import numpy as np
import pytest

from src.vision.dataset import CLASS_TO_INDEX, MODALITIES, ROOT, collect_samples
from src.vision.predict import predict_image
from src.vision.preprocessing import IMAGE_SIZE, augment_image, extract_features, load_rgb_image
from src.vision.train import MIN_GROUPS_PER_CLASS_MODALITY, MODEL_DIR, is_tiny_dataset


def test_dataset_diagnostic_reads_four_labeled_images():
    records, report = collect_samples()
    assert report["valid_count"] == 4
    assert report["invalid_count"] == 0
    assert report["duplicate_count"] == 0
    assert report["counts_by_modality_and_class"] == {
        "termica/APROVADA": 1,
        "termica/REPROVADA": 1,
        "visual/APROVADA": 1,
        "visual/REPROVADA": 1,
    }
    assert len(records) == 4


def test_label_map_is_explicit_and_stable():
    assert CLASS_TO_INDEX == {"APROVADA": 0, "REPROVADA": 1}
    mapping = json.loads((MODEL_DIR / "class_mapping.json").read_text(encoding="utf-8"))
    assert mapping["class_to_index"] == CLASS_TO_INDEX


@pytest.mark.parametrize("filename", [
    "solda_aprovada.png", "solda_reprovada.png",
    "termica_solda_aprovada.png", "termica_solda_reprovada.png",
])
def test_preprocessing_shape_dtype_and_features(filename):
    path = ROOT / "data/raw/imagens" / filename
    image = load_rgb_image(path)
    assert image.shape == (IMAGE_SIZE[1], IMAGE_SIZE[0], 3)
    assert image.dtype == np.uint8
    feature = extract_features(path)
    assert feature.ndim == 1
    assert np.isfinite(feature).all()


def test_training_artifacts_are_separate_and_experimental():
    metadata = json.loads((MODEL_DIR / "model_metadata.json").read_text(encoding="utf-8"))
    assert metadata["experimental"] is True
    assert metadata["validated_for_industrial_use"] is False
    assert set(metadata["modalities"]) == MODALITIES
    assert (MODEL_DIR / "visual_model.joblib").is_file()
    assert (MODEL_DIR / "termica_model.joblib").is_file()
    assert metadata["metrics"]["status"] == "insufficient_independent_data"
    assert metadata["metrics"]["metrics"] is None
    assert metadata["split"]["test_count"] == 0
    assert all(count == 1 for count in metadata["unique_groups_by_modality_and_class"].values())


@pytest.mark.parametrize("filename,modality", [
    ("solda_aprovada.png", "visual"),
    ("termica_solda_reprovada.png", "termica"),
])
def test_inference_runs_and_returns_experimental_warning(filename, modality):
    result = predict_image(ROOT / "data/raw/imagens" / filename, modality=modality)
    assert result["predicted_class"] in CLASS_TO_INDEX
    assert set(result["class_scores"]) == set(CLASS_TO_INDEX)
    assert abs(sum(result["class_scores"].values()) - 1) < 1e-8
    assert result["score_type"] == "relative_nearest_prototype_similarity_not_probability"
    assert result["validated_for_industrial_use"] is False
    assert any("experimental" in warning.lower() for warning in result["warnings"])
    if modality == "termica":
        assert any("calibração" in warning for warning in result["warnings"])


def test_invalid_path_modality_and_corrupt_file_are_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        predict_image(tmp_path / "missing.png", modality="visual")
    sample = ROOT / "data/raw/imagens/solda_aprovada.png"
    with pytest.raises(ValueError, match="modalidade"):
        predict_image(sample, modality="multimodal")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not a png")
    with pytest.raises(ValueError, match="inválida"):
        extract_features(corrupt)


def test_future_data_minimum_is_not_met_by_initial_dataset():
    _, report = collect_samples()
    assert MIN_GROUPS_PER_CLASS_MODALITY == 20
    assert all(value < MIN_GROUPS_PER_CLASS_MODALITY
               for value in report["unique_groups_by_modality_and_class"].values())
    assert is_tiny_dataset(report["unique_groups_by_modality_and_class"]) is True
    adequate = {f"{modality}/{label}": 20 for modality in MODALITIES for label in CLASS_TO_INDEX}
    assert is_tiny_dataset(adequate) is False


def test_augmentation_is_optional_and_bounded():
    image = load_rgb_image(ROOT / "data/raw/imagens/solda_aprovada.png")
    augmented = augment_image(image, angle_degrees=2, brightness_delta=0.02)
    assert augmented.shape == image.shape
    assert augmented.dtype == np.uint8
    with pytest.raises(ValueError):
        augment_image(image, angle_degrees=25)
