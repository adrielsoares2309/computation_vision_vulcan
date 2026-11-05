"""Manifesto, rótulos, modalidades e diagnóstico das imagens de solda."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "imagens"
PROCESSED_DIR = ROOT / "data" / "processed" / "vision"
REPORT_DIR = ROOT / "reports" / "vision"
CLASS_TO_INDEX = {"APROVADA": 0, "REPROVADA": 1}
INDEX_TO_CLASS = {value: key for key, value in CLASS_TO_INDEX.items()}
MODALITIES = {"visual", "termica"}
SEED_FILES = {
    "solda_aprovada.png": ("APROVADA", "visual", "solda_aprovada"),
    "solda_reprovada.png": ("REPROVADA", "visual", "solda_reprovada"),
    "termica_solda_aprovada.png": ("APROVADA", "termica", "solda_aprovada"),
    "termica_solda_reprovada.png": ("REPROVADA", "termica", "solda_reprovada"),
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MANIFEST = PROCESSED_DIR / "labels.csv"


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _describe(path: Path, label: str, modality: str, group_id: str, source: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path.resolve()), "relative_path": _relative_path(path),
        "label": label, "label_index": CLASS_TO_INDEX[label], "modality": modality,
        "group_id": group_id, "source": source, "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            record.update({"valid": True, "format": image.format, "width": image.width,
                           "height": image.height, "mode": image.mode, "channels": len(image.getbands())})
    except Exception as error:
        record.update({"valid": False, "error": str(error)})
    return record


def collect_samples() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Lê os quatro exemplos iniciais e futuras imagens em pastas/manifesto."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        MANIFEST.write_text("path,label,modality,group_id\n", encoding="utf-8")
    readme = PROCESSED_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Vision dataset\n\n"
            "Add images under `visual/aprovada`, `visual/reprovada`, `termica/aprovada`, or `termica/reprovada`, "
            "or list them in `labels.csv` with columns `path,label,modality,group_id`.\n\n"
            "Use the same group_id for all views of one physical specimen, including across modalities. "
            "Do not move or change files under data/raw/imagens. Augmented copies are not independent specimens.\n",
            encoding="utf-8",
        )
    for modality in sorted(MODALITIES):
        for label in ("aprovada", "reprovada"):
            (PROCESSED_DIR / modality / label).mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    invalid: list[dict[str, str]] = []
    for filename, (label, modality, group_id) in SEED_FILES.items():
        path = RAW_DIR / filename
        if not path.is_file():
            missing.append(str(path.relative_to(ROOT)))
            continue
        record = _describe(path, label, modality, group_id, "nome_do_arquivo_inicial")
        records.append(record)
        if not record["valid"]:
            invalid.append({"path": record["relative_path"], "error": record["error"]})

    manifest_rows = 0
    if MANIFEST.is_file():
        with MANIFEST.open(encoding="utf-8-sig", newline="") as stream:
            for linha, row in enumerate(csv.DictReader(stream), start=2):
                if not any((v or "").strip() for v in row.values()):
                    continue
                manifest_rows += 1
                relativo = (row.get("path") or "").strip()
                label = (row.get("label") or "").strip().upper()
                modality = (row.get("modality") or "").strip().lower()
                group_id = (row.get("group_id") or "").strip()
                if label not in CLASS_TO_INDEX or modality not in MODALITIES or not group_id or not relativo:
                    invalid.append({"path": relativo, "error": f"Manifesto inválido na linha {linha}; campos: path,label,modality,group_id."})
                    continue
                path = Path(relativo)
                if not path.is_absolute():
                    path = ROOT / path
                if not path.is_file():
                    missing.append(str(path))
                    continue
                record = _describe(path, label, modality, group_id, "manifesto")
                records.append(record)
                if not record["valid"]:
                    invalid.append({"path": record["relative_path"], "error": record["error"]})

    # Pastas futuras: data/processed/vision/{visual,termica}/{aprovada,reprovada}/.
    for modality in sorted(MODALITIES):
        for label_folder, label in [("aprovada", "APROVADA"), ("reprovada", "REPROVADA")]:
            folder = PROCESSED_DIR / modality / label_folder
            for path in sorted(folder.iterdir()):
                if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                stem = path.stem.casefold().replace("termica_", "").replace("thermal_", "")
                records.append(_describe(path, label, modality, stem, "pasta_rotulada"))

    valid_records = [r for r in records if r["valid"]]
    hashes: dict[str, list[str]] = {}
    for record in valid_records:
        hashes.setdefault(record["sha256"], []).append(record["relative_path"])
    duplicates = [{"sha256": digest, "files": paths} for digest, paths in hashes.items() if len(paths) > 1]
    valid_by_pair = Counter((r["modality"], r["label"]) for r in valid_records)
    groups_by_pair = {f"{modality}/{label}": len({r["group_id"] for r in valid_records if r["modality"] == modality and r["label"] == label})
                      for modality in sorted(MODALITIES) for label in CLASS_TO_INDEX}
    report = {
        "class_mapping": CLASS_TO_INDEX,
        "expected_seed_files": list(SEED_FILES),
        "records": records,
        "missing_files": missing,
        "invalid_files": invalid,
        "valid_count": len(valid_records),
        "invalid_count": len(invalid),
        "missing_count": len(missing),
        "exact_duplicates": duplicates,
        "duplicate_count": len(duplicates),
        "counts_by_class": {label: sum(1 for r in valid_records if r["label"] == label) for label in CLASS_TO_INDEX},
        "counts_by_modality": {modality: sum(1 for r in valid_records if r["modality"] == modality) for modality in sorted(MODALITIES)},
        "counts_by_modality_and_class": {f"{modality}/{label}": int(valid_by_pair[(modality, label)])
                                          for modality in sorted(MODALITIES) for label in CLASS_TO_INDEX},
        "unique_groups_by_modality_and_class": groups_by_pair,
        "manifest_path": str(MANIFEST.relative_to(ROOT)),
        "manifest_rows": manifest_rows,
    }
    return records, report


def write_dataset_report(report: dict[str, Any]) -> Path:
    """Salva diagnóstico JSON em reports/vision."""
    import json

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORT_DIR / "dataset_report.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination

