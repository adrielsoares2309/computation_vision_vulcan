"""Diagnóstico e treinamento experimental de modelos por modalidade."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
import sklearn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .dataset import (CLASS_TO_INDEX, INDEX_TO_CLASS, MODALITIES, PROCESSED_DIR, RAW_DIR,
                     REPORT_DIR, ROOT, collect_samples, write_dataset_report)
from .evaluate import evaluate_predictions, insufficient_evaluation
from .preprocessing import FEATURE_VERSION, IMAGE_SIZE, extract_features


MODEL_DIR = ROOT / "models" / "vision"
MIN_GROUPS_PER_CLASS_MODALITY = 20
SEED = 42


def write_class_mapping() -> Path:
    """Persiste mapeamento explícito e imutável das classes."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / "class_mapping.json"
    path.write_text(json.dumps({"class_to_index": CLASS_TO_INDEX, "index_to_class": INDEX_TO_CLASS}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _usable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove somente cópias exatas após a primeira e registros inválidos."""
    seen: set[str] = set()
    usable = []
    for row in records:
        if not row.get("valid") or row["sha256"] in seen:
            continue
        seen.add(row["sha256"])
        usable.append(row)
    return usable


def _pair_group_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {f"{modality}/{label}": len({r["group_id"] for r in records if r["modality"] == modality and r["label"] == label})
            for modality in sorted(MODALITIES) for label in CLASS_TO_INDEX}


def is_tiny_dataset(counts: dict[str, int]) -> bool:
    """Indica se ao menos uma combinação classe/modalidade não alcança o piso configurado."""
    return any(int(counts.get(f"{modality}/{label}", 0)) < MIN_GROUPS_PER_CLASS_MODALITY
               for modality in MODALITIES for label in CLASS_TO_INDEX)


def _group_split(records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Encontra divisão 70/15/15 por grupo sem misturar réplicas do mesmo corpo de prova."""
    groups = np.asarray([r["group_id"] for r in records])
    y = np.asarray([r["label_index"] for r in records])
    pair = np.asarray([f"{r['modality']}/{r['label']}" for r in records])
    wanted = set(pair)
    outer = GroupShuffleSplit(n_splits=1000, test_size=.15, random_state=SEED)
    for dev_idx, test_idx in outer.split(np.zeros(len(records)), y, groups):
        if set(pair[test_idx]) != wanted:
            continue
        inner = GroupShuffleSplit(n_splits=1000, test_size=.1765, random_state=SEED)
        dev_groups = groups[dev_idx]
        for train_pos, val_pos in inner.split(np.zeros(len(dev_idx)), y[dev_idx], dev_groups):
            train_idx, val_idx = dev_idx[train_pos], dev_idx[val_pos]
            if set(pair[train_idx]) == wanted and set(pair[val_idx]) == wanted:
                return train_idx, val_idx, test_idx
    raise ValueError("Não foi encontrada divisão por grupo com as duas classes em cada modalidade nos três blocos. Revise grupos/rótulos ou adicione corpos de prova independentes.")


def _make_pipeline() -> Any:
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=1, metric="euclidean", weights="distance"))


def _save_reports(dataset_report: dict[str, Any], evaluation: dict[str, Any], metadata: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "evaluation_metrics.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for record in dataset_report["records"]:
        rows.append(f"| {record['relative_path']} | {record['label']} | {record['modality']} | {'válida' if record['valid'] else 'inválida'} |")
    resumo = f"""# Treinamento e validação funcional de visão computacional

## Dados inspecionados

{dataset_report['valid_count']} imagens válidas, {dataset_report['invalid_count']} inválidas e {dataset_report['missing_count']} ausentes; {dataset_report['duplicate_count']} grupos de cópias exatas. Distribuição por modalidade e classe: `{dataset_report['counts_by_modality_and_class']}`.

| Arquivo | Rótulo recebido | Modalidade | Leitura |
|---|---|---|---|
{chr(10).join(rows)}

Os rótulos iniciais são obtidos dos nomes de arquivo informados no escopo; não há anotação especializada independente nos arquivos para confirmar o estado metalúrgico. `APROVADA=0`, `REPROVADA=1`.

## Estratégia e estado

Arquitetura demonstrativa: descritores OpenCV HOG + histogramas RGB e médias espaciais, padronizados e classificados por 1-vizinho mais próximo. Foram treinados classificadores separados para as modalidades visual e térmica. Nenhum peso externo foi baixado. PyTorch e torchvision não estão instalados no ambiente; transfer learning não foi executado.

O modo de quatro imagens foi explicitamente autorizado pelo argumento `--allow-tiny-dataset`. Há apenas um exemplar por classe em cada modalidade, portanto cada modelo foi ajustado nesses dois exemplos e não existe conjunto independente de validação ou teste. Nenhuma acurácia, matriz de confusão de teste ou métrica de generalização é reportada. Os artefatos estão marcados como experimentais e inadequados para decisão industrial.

## Limitações

HOG e histogramas são um baseline clássico, não uma rede profunda pré-treinada. O classificador memoriza os poucos exemplos; seus escores de similaridade não são probabilidades calibradas. As imagens térmicas são RGB de falsa cor, sem dados de calibração para inferir graus Celsius. Como a empresa é fictícia e o projeto admite dados simulados, confirme a origem das imagens antes de qualquer interpretação industrial.

## Próxima coleta e execução

Adicione imagens reais independentes em `data/processed/vision/{{visual,termica}}/{{aprovada,reprovada}}/` ou liste-as em `labels.csv` com colunas `path,label,modality,group_id`. Use `group_id` igual para vistas do mesmo corpo de prova, evitando vazamento entre treino e teste. O modo normal exige ao menos {MIN_GROUPS_PER_CLASS_MODALITY} grupos independentes por classe e modalidade; após isso, executa divisão agrupada 70/15/15 e relata métricas separadas por modalidade.

Comandos: `python -m src.vision.train --inspect-only`, `python -m src.vision.train --allow-tiny-dataset` e `python -m pytest tests/test_vision.py -q`.
"""
    (REPORT_DIR / "training_summary.md").write_text(resumo, encoding="utf-8")


def run_training(allow_tiny_dataset: bool = False, inspect_only: bool = False) -> dict[str, Any]:
    """Diagnostica as imagens e treina ou recusa conforme o volume disponível."""
    records, dataset_report = collect_samples()
    write_dataset_report(dataset_report)
    write_class_mapping()
    usable = _usable_records(records)
    counts = _pair_group_counts(usable)
    if inspect_only:
        print(json.dumps(dataset_report, ensure_ascii=False, indent=2))
        return {"dataset_report": dataset_report}
    if dataset_report["invalid_count"] or dataset_report["missing_count"]:
        raise ValueError(f"Há {dataset_report['invalid_count']} imagem(ns) inválida(s) e {dataset_report['missing_count']} ausente(s); corrija o dataset antes do treino.")
    if dataset_report["duplicate_count"]:
        print(f"Aviso: {dataset_report['duplicate_count']} grupo(s) de imagens duplicadas detectado(s); cópias exatas além da primeira não serão usadas.")
    insufficient = {pair: count for pair, count in counts.items() if count < MIN_GROUPS_PER_CLASS_MODALITY}
    tiny = is_tiny_dataset(counts)
    if tiny and not allow_tiny_dataset:
        reasons = [f"{pair}: {count} grupos independentes; mínimo operacional configurado {MIN_GROUPS_PER_CLASS_MODALITY}." for pair, count in insufficient.items()]
        evaluation = insufficient_evaluation(reasons, {m: {p: counts[f"{m}/{p}"] for p in CLASS_TO_INDEX} for m in sorted(MODALITIES)})
        metadata = {"status": "not_trained_insufficient_data", "experimental": True, "limitations": reasons}
        _save_reports(dataset_report, evaluation, metadata)
        raise ValueError("Dados insuficientes para avaliação independente. Para um teste estritamente funcional com rótulo experimental, use --allow-tiny-dataset.")
    for modality in MODALITIES:
        if any(counts[f"{modality}/{label}"] == 0 for label in CLASS_TO_INDEX):
            raise ValueError(f"A modalidade {modality} precisa conter ao menos uma imagem de cada classe.")

    features = [extract_features(r["path"]) for r in usable]
    x_all = np.vstack(features)
    y_all = np.asarray([r["label_index"] for r in usable], dtype=np.int64)
    groups = np.asarray([r["group_id"] for r in usable])
    evaluation: dict[str, Any]
    split_meta: dict[str, Any]
    trained: dict[str, Any] = {}
    if tiny:
        train_indices = np.arange(len(usable))
        val_indices = np.asarray([], dtype=int)
        test_indices = np.asarray([], dtype=int)
        evaluation = insufficient_evaluation(
            ["Modo tiny autorizado: apenas um exemplar por classe/modalidade; não há validação ou teste independentes."],
            {m: {label: counts[f"{m}/{label}"] for label in CLASS_TO_INDEX} for m in sorted(MODALITIES)},
        )
        split_meta = {"strategy": "all_available_samples_for_functional_fit", "train_count": len(usable), "validation_count": 0, "test_count": 0}
    else:
        train_indices, val_indices, test_indices = _group_split(usable)
        evaluation = {"status": "evaluated_on_independent_grouped_test", "per_modality": {}}
        split_meta = {"strategy": "grouped 70/15/15; group_id held in one partition", "train_count": len(train_indices), "validation_count": len(val_indices), "test_count": len(test_indices)}

    for modality in sorted(MODALITIES):
        modality_indices = np.asarray([i for i, r in enumerate(usable) if r["modality"] == modality])
        if tiny:
            fit_indices = modality_indices
        else:
            fit_indices = np.intersect1d(train_indices, modality_indices)
            val_modality = np.intersect1d(val_indices, modality_indices)
            test_modality = np.intersect1d(test_indices, modality_indices)
            # Validação acompanha a seleção de hiperparâmetros. Aqui há um único
            # modelo definido a priori, portanto ela só é registrada como bloco isolado.
            if len(val_modality):
                pass
            final_fit = np.concatenate([fit_indices, val_modality])
            fit_indices = final_fit
        modelo = _make_pipeline()
        modelo.fit(x_all[fit_indices], y_all[fit_indices])
        trained[modality] = {"pipeline": modelo, "modality": modality, "feature_version": FEATURE_VERSION,
                             "image_size": list(IMAGE_SIZE), "experimental": tiny,
                             "train_features": x_all[fit_indices], "train_labels": y_all[fit_indices]}
        if not tiny:
            pred = modelo.predict(x_all[test_modality]).astype(int).tolist()
            metricas = evaluate_predictions(y_all[test_modality].astype(int).tolist(), pred)
            evaluation["per_modality"][modality] = metricas
    if not tiny and all(m in evaluation["per_modality"] for m in MODALITIES):
        evaluation["status"] = "evaluated_on_independent_grouped_test"

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for modality, artifact in trained.items():
        joblib.dump(artifact, MODEL_DIR / f"{modality}_model.joblib")
    created_at = datetime.now(timezone.utc).isoformat()
    source_hashes = {r["relative_path"]: r["sha256"] for r in usable}
    metadata = {
        "status": "experimental_tiny_dataset" if tiny else "trained_with_grouped_independent_evaluation",
        "experimental": tiny,
        "validated_for_industrial_use": False,
        "architecture": "HOG + RGB histograms + 4x4 spatial means + StandardScaler + 1-nearest-neighbor",
        "trained_at_utc": created_at,
        "source_images": source_hashes,
        "classes": {"APROVADA": 0, "REPROVADA": 1},
        "modalities": sorted(trained),
        "input_size_width_height": list(IMAGE_SIZE),
        "preprocessing": {"color": "RGB", "resize": "128x128", "pixel_type": "uint8", "feature_version": FEATURE_VERSION},
        "initial_weights": {"source": None, "pretrained": False},
        "deep_learning_framework": {
            "pytorch_available": importlib.util.find_spec("torch") is not None,
            "torchvision_available": importlib.util.find_spec("torchvision") is not None,
            "transfer_learning_used": False,
            "reason": "PyTorch/torchvision are unavailable; OpenCV + scikit-learn baseline used without external weights.",
        },
        "library_versions": {"python": platform.python_version(), "opencv": cv2.__version__, "scikit_learn": sklearn.__version__, "numpy": np.__version__, "joblib": joblib.__version__},
        "parameters": {"scaler": "StandardScaler", "classifier": "KNeighborsClassifier(n_neighbors=1, metric='euclidean', weights='distance')", "seed": SEED},
        "counts_by_modality_and_class": dataset_report["counts_by_modality_and_class"],
        "unique_groups_by_modality_and_class": counts,
        "split": split_meta,
        "metrics": evaluation,
        "limitations": ["Apenas quatro imagens originais, uma por classe e modalidade; os modelos tiny são demonstrativos e não generalizam de forma avaliável.", "Rótulos recebidos por nome do arquivo, sem validação de especialista independente.", "Empresa fictícia e possibilidade de dados simulados constam na documentação do projeto.", "Thermal RGB false-color has no radiometric calibration; physical temperatures cannot be recovered.", "Similarity scores are not calibrated probabilities."],
    }
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    _save_reports(dataset_report, evaluation, metadata)
    print(f"Dataset: {dataset_report['valid_count']} imagens válidas; por modalidade/classe: {dataset_report['counts_by_modality_and_class']}")
    print(f"Estado: {metadata['status']}; avaliação: {evaluation['status']}")
    print(f"Modelos: {MODEL_DIR}; relatórios: {REPORT_DIR}")
    return {"metadata": metadata, "evaluation": evaluation, "dataset_report": dataset_report}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect-only", action="store_true", help="Inspeciona e grava o diagnóstico sem treinar.")
    parser.add_argument("--allow-tiny-dataset", action="store_true", help="Autoriza ajuste demonstrativo com dados abaixo do mínimo; não gera métricas de generalização.")
    args = parser.parse_args()
    try:
        run_training(allow_tiny_dataset=args.allow_tiny_dataset, inspect_only=args.inspect_only)
    except Exception as error:
        parser.exit(2, f"Erro no pipeline de visão: {error}\n")


if __name__ == "__main__":
    main()

