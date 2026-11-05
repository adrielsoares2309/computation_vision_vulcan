"""Inferência modular para imagens visuais e térmicas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .dataset import INDEX_TO_CLASS
from .preprocessing import extract_features
from .train import MODEL_DIR


def predict_image(image_path: str | Path, modality: str | None = None,
                  artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classifica uma imagem; informe visual/termica ou use prefixo térmico no nome."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {path}")
    aviso_modalidade = None
    if modality is None:
        stem = path.stem.casefold()
        if "termica" in stem or "thermal" in stem:
            modality = "termica"
            aviso_modalidade = "Modalidade inferida pelo nome do arquivo; confirme antes de interpretar."
        else:
            modality = "visual"
            aviso_modalidade = "Modalidade visual assumida pelo nome do arquivo; informe modality explicitamente quando não for visual."
    modality = modality.strip().lower()
    if modality not in {"visual", "termica"}:
        raise ValueError("modalidade deve ser 'visual' ou 'termica'.")
    model_path = MODEL_DIR / f"{modality}_model.joblib"
    if not model_path.is_file():
        raise FileNotFoundError(f"Modelo {modality!r} não encontrado: {model_path}. Execute python -m src.vision.train --allow-tiny-dataset para o teste funcional.")
    try:
        artifact = artifact if artifact is not None else joblib.load(model_path)
        features = extract_features(path, tuple(artifact["image_size"]))
        vetor = features.reshape(1, -1)
        modelo = artifact["pipeline"]
        previsto = int(modelo.predict(vetor)[0])
        scaler = modelo.named_steps["standardscaler"]
        knn = modelo.named_steps["kneighborsclassifier"]
        distancia, indices = knn.kneighbors(scaler.transform(vetor), n_neighbors=min(len(artifact["train_labels"]), 4))
        # Similaridades relativas aos protótipos de treino; não são probabilidades.
        distancias_por_classe = {}
        for classe in sorted(INDEX_TO_CLASS):
            distancias_por_classe[classe] = float(min((distancia[0][j] for j, idx in enumerate(indices[0])
                                                       if int(artifact["train_labels"][idx]) == classe), default=np.inf))
        similares = {INDEX_TO_CLASS[classe]: (0.0 if not np.isfinite(dist) else float(1.0 / (dist + 1e-8)))
                     for classe, dist in distancias_por_classe.items()}
        total = sum(similares.values()) or 1.0
        escores = {classe: score / total for classe, score in similares.items()}
        avisos = ["Modelo experimental e não validado para decisões industriais.", "Escores de similaridade não são probabilidades calibradas."]
        if modality == "termica":
            avisos.append("Imagem RGB de falsa cor; sem calibração radiométrica não representa temperatura física.")
        if artifact.get("experimental"):
            avisos.append("Treinado com apenas um exemplar por classe nesta modalidade; a previsão serve apenas para validar o fluxo técnico.")
        if aviso_modalidade:
            avisos.append(aviso_modalidade)
        return {"predicted_class": INDEX_TO_CLASS[previsto], "class_scores": escores,
                "score_type": "relative_nearest_prototype_similarity_not_probability",
                "modality": modality, "model_status": "experimental" if artifact.get("experimental") else "not_industrially_validated",
                "validated_for_industrial_use": False, "warnings": avisos}
    except Exception as error:
        if isinstance(error, (FileNotFoundError, ValueError)):
            raise
        raise RuntimeError(f"Falha ao inferir imagem {path}: {error}") from error


def main() -> None:
    """CLI simples para inferência individual, pronta para chamada por serviço."""
    parser = argparse.ArgumentParser(description="Classifica uma imagem de solda usando um modelo experimental.")
    parser.add_argument("--image", required=True, help="Caminho da imagem para classificar.")
    parser.add_argument("--modality", choices=["visual", "termica"], help="Modalidade; se omitida, usa somente uma heurística pelo nome do arquivo.")
    args = parser.parse_args()
    try:
        print(json.dumps(predict_image(args.image, modality=args.modality), ensure_ascii=False, indent=2))
    except Exception as error:
        parser.exit(2, f"Erro na inferência: {error}\n")


if __name__ == "__main__":
    main()

