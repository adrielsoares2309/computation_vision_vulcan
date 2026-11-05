"""Métricas e relatórios para classificação multiclasse de falhas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


NOMES_CLASSES = {
    0: "Normal",
    1: "Desgaste de ferramenta",
    2: "Falha de refrigeração",
    3: "Desalinhamento / trinca",
}


def calcular_metricas(
    y_verdadeiro: pd.Series | np.ndarray,
    y_previsto: np.ndarray,
    probabilidades: np.ndarray | None = None,
    classes: list[Any] | np.ndarray | None = None,
) -> dict[str, Any]:
    """Calcula métricas globais e por classe; AUCs são opcionais."""
    rotulos = list(classes) if classes is not None else sorted(pd.unique(y_verdadeiro).tolist())
    falhas = [rotulo for rotulo in rotulos if rotulo != 0]
    metricas: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_verdadeiro, y_previsto)),
        "precision_macro": float(precision_score(y_verdadeiro, y_previsto, labels=rotulos, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_verdadeiro, y_previsto, labels=rotulos, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_verdadeiro, y_previsto, labels=rotulos, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_verdadeiro, y_previsto, labels=rotulos, average="weighted", zero_division=0)),
        "recall_falhas_macro": float(recall_score(y_verdadeiro, y_previsto, labels=falhas, average="macro", zero_division=0)),
        "recall_por_classe": {
            str(rotulo): float(valor)
            for rotulo, valor in zip(
                rotulos,
                recall_score(y_verdadeiro, y_previsto, labels=rotulos, average=None, zero_division=0),
            )
        },
    }
    if probabilidades is not None:
        y_binario = pd.get_dummies(pd.Series(y_verdadeiro)).reindex(columns=rotulos, fill_value=0).to_numpy()
        try:
            metricas["roc_auc_ovr_macro"] = float(roc_auc_score(y_verdadeiro, probabilidades, labels=rotulos, multi_class="ovr", average="macro"))
            metricas["pr_auc_macro"] = float(average_precision_score(y_binario, probabilidades, average="macro"))
        except ValueError:
            metricas["roc_auc_ovr_macro"] = None
            metricas["pr_auc_macro"] = None
    return metricas


def salvar_relatorios(
    pasta: Path,
    comparacao: pd.DataFrame,
    y_teste: pd.Series,
    previsoes: np.ndarray,
    probabilidades: np.ndarray | None,
    classes: list[Any],
    metricas_teste: dict[str, Any],
    nome_modelo: str,
    parametros: dict[str, Any],
) -> None:
    """Grava comparação, relatório por classe, matriz e gráficos."""
    pasta.mkdir(parents=True, exist_ok=True)
    comparacao.to_csv(pasta / "model_comparison.csv", index=False, encoding="utf-8")
    nomes = [NOMES_CLASSES.get(int(c), str(c)) for c in classes]
    relatorio = classification_report(
        y_teste,
        previsoes,
        labels=classes,
        target_names=nomes,
        output_dict=True,
        zero_division=0,
    )
    (pasta / "classification_report.json").write_text(
        json.dumps({"metrics": metricas_teste, "per_class": relatorio}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    matriz = confusion_matrix(y_teste, previsoes, labels=classes)
    pd.DataFrame(matriz, index=nomes, columns=nomes).to_csv(pasta / "confusion_matrix.csv", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7, 6))
    imagem = ax.imshow(matriz, cmap="Blues")
    ax.set(xticks=np.arange(len(nomes)), yticks=np.arange(len(nomes)), xticklabels=nomes, yticklabels=nomes,
           xlabel="Classe prevista", ylabel="Classe real", title="Matriz de confusão — teste temporal")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    limite = matriz.max() / 2 if matriz.size else 0
    for linha in range(matriz.shape[0]):
        for coluna in range(matriz.shape[1]):
            ax.text(coluna, linha, f"{matriz[linha, coluna]:,}", ha="center", va="center",
                    color="white" if matriz[linha, coluna] > limite else "black")
    fig.colorbar(imagem, ax=ax, label="Registros")
    fig.tight_layout()
    fig.savefig(pasta / "confusion_matrix.png", dpi=160)
    plt.close(fig)

    metricas_validacao = [col for col in ["recall_falhas_macro", "f1_macro", "precision_macro", "accuracy"] if col in comparacao]
    fig, ax = plt.subplots(figsize=(10, 5))
    comparacao.set_index("model")[metricas_validacao].plot(kind="bar", ax=ax)
    ax.set(title="Comparação dos modelos na validação cronológica", ylabel="Métrica", xlabel="Modelo")
    ax.set_ylim(0, 1)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta / "model_comparison.png", dpi=160)
    plt.close(fig)

    tabela_classes = "\n".join(
        f"| {NOMES_CLASSES.get(int(classe), classe)} | {metricas_teste['recall_por_classe'].get(str(classe), 0):.3f} |"
        for classe in classes
    )
    texto = f"""# Resumo do treinamento e avaliação

## Resultado

- Modelo selecionado: **{nome_modelo}**.
- Seleção feita exclusivamente na validação cronológica, priorizando o recall macro das classes de falha (1, 2 e 3); empate resolvido pelo F1 macro.
- Hiperparâmetros do modelo: `{json.dumps(parametros, ensure_ascii=False, sort_keys=True)}`.
- Métricas no teste temporal final: accuracy {metricas_teste['accuracy']:.3f}, precision macro {metricas_teste['precision_macro']:.3f}, recall macro {metricas_teste['recall_macro']:.3f}, F1 macro {metricas_teste['f1_macro']:.3f}, F1 ponderado {metricas_teste['f1_weighted']:.3f}, recall macro de falhas {metricas_teste['recall_falhas_macro']:.3f}.
- ROC-AUC OVR macro: {metricas_teste.get('roc_auc_ovr_macro')}; PR-AUC macro: {metricas_teste.get('pr_auc_macro')}.

## Recall por classe no teste

| Classe | Recall |
|---|---:|
{tabela_classes}

## Método e limitações

Os dados foram divididos cronologicamente em treino, validação e teste, aproximadamente 70%/15%/15%. O teste não participou da seleção ou ajuste. Imputação, codificação e escalonamento fazem parte de cada pipeline e são ajustados apenas no treino (ou, após a seleção, no conjunto de desenvolvimento treino + validação). Classes não foram reamostradas. O identificador da célula foi mantido como categoria contextual; o modelo não foi validado em células desconhecidas.

`tipo_falha` descreve a condição rotulada na própria leitura. Portanto, esta avaliação mede classificação contemporânea, não previsão antecipada de falhas futuras. A base não define horizonte de previsão nem custos operacionais de falsos positivos/falsos negativos. As probabilidades não foram calibradas. Importâncias de variáveis, se geradas, indicam associação preditiva e não causalidade.
"""
    texto += """

## Uso

Na raiz do projeto, execute `python -m src.ml.train`. Para prever, forneça a `prever` um DataFrame com as colunas de entrada do modelo (sem timestamp e sem alvo); `src.ml.predict` carrega o pipeline completo e retorna classe prevista e probabilidades não calibradas. Exemplo: `prever(pd.read_parquet('novas_leituras.parquet'))`. Rode os testes com `python -m pytest tests/test_ml.py -q`.

## Proveniência e limites

A documentação descreve a empresa como fictícia e admite que os dados possam ser simulados. Confirme a origem deste arquivo antes de extrapolar as métricas a uma fábrica real. O Parquet tratado já contém interpolação offline executada antes da divisão temporal; como não há marcador de linhas interpoladas, possível influência de leituras futuras próximas não pode ser totalmente descartada.
"""
    (pasta / "training_summary.md").write_text(texto, encoding="utf-8")


def salvar_importancias(pipeline: Any, pasta: Path) -> None:
    """Grava importância de árvore quando o estimador selecionado a expõe."""
    estimador = pipeline.named_steps["model"]
    if hasattr(estimador, "feature_importances_"):
        valores = estimador.feature_importances_
        metodo = "Tree impurity importance; association, not causation."
    elif hasattr(estimador, "coef_"):
        valores = np.mean(np.abs(estimador.coef_), axis=0)
        metodo = "Mean absolute class coefficient; association, not causation."
    else:
        return
    nomes = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importancia = pd.DataFrame({"feature": nomes, "importance": valores, "method": metodo}).sort_values("importance", ascending=False)
    importancia.to_csv(pasta / "feature_importance.csv", index=False, encoding="utf-8")
    fig, ax = plt.subplots(figsize=(9, max(4, min(10, len(importancia.head(20)) * .35))))
    importancia.head(20).sort_values("importance").plot.barh(x="feature", y="importance", legend=False, ax=ax)
    ax.set(title="Importância de variáveis do modelo selecionado (associação, não causalidade)", xlabel="Importância", ylabel="Variável")
    fig.tight_layout()
    fig.savefig(pasta / "feature_importance.png", dpi=160)
    plt.close(fig)

