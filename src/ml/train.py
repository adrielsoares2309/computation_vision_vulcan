"""Treina, compara, seleciona e persiste modelos de classificação de falhas."""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

try:
    from xgboost import XGBClassifier
    XGB_DISPONIVEL = True
except ImportError:
    XGB_DISPONIVEL = False

from .anomaly_detection import treinar_detector
from .evaluate import calcular_metricas, salvar_importancias, salvar_relatorios


RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_FEATURES_PARQUET = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_features.parquet"
CAMINHO_PARQUET = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_tratados.parquet"
CAMINHO_CSV = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_tratados.csv"
PASTA_MODELOS = RAIZ / "models" / "tabular"
PASTA_RELATORIOS = RAIZ / "reports" / "ml"
SEMENTE = 42
TARGET_CANDIDATES = ["tipo_falha"]
EXPLICACAO_CLASSES = {0: "Normal", 1: "Desgaste de ferramenta", 2: "Falha de refrigeração", 3: "Desalinhamento / trinca"}
NOMES_ARQUIVOS = {
    "LogisticRegression": "logistic_regression.joblib",
    "RandomForestClassifier": "random_forest.joblib",
    "ExtraTreesClassifier": "extra_trees.joblib",
    "GradientBoostingClassifier": "gradient_boosting.joblib",
    "XGBClassifier": "xgboost.joblib",
}


def carregar_dataset() -> tuple[pd.DataFrame, Path]:
    """Lê o Parquet com features preferencialmente e valida seu esquema básico."""
    if CAMINHO_FEATURES_PARQUET.is_file():
        caminho = CAMINHO_FEATURES_PARQUET
    elif CAMINHO_PARQUET.is_file():
        caminho = CAMINHO_PARQUET
    else:
        caminho = CAMINHO_CSV
    if not caminho.is_file():
        raise FileNotFoundError("Dataset processado não encontrado em data/processed.")
    try:
        dados = pd.read_parquet(caminho) if caminho.suffix == ".parquet" else pd.read_csv(caminho, parse_dates=["timestamp"])
    except Exception as erro:
        raise RuntimeError(f"Não foi possível ler o dataset {caminho}: {erro}") from erro
    if dados.empty:
        raise ValueError("Dataset está vazio.")
    return dados, caminho


def identificar_alvo(dados: pd.DataFrame) -> str:
    """Confirma o alvo documentado e sua codificação real, sem sintetizar rótulos."""
    candidatos = [c for c in TARGET_CANDIDATES if c in dados.columns]
    if len(candidatos) != 1:
        raise ValueError(f"Esperava uma única coluna-alvo documentada {TARGET_CANDIDATES}; candidatas encontradas: {candidatos}.")
    alvo = candidatos[0]
    if dados[alvo].isna().any():
        raise ValueError(f"A variável-alvo {alvo!r} contém valores ausentes.")
    if set(pd.unique(dados[alvo])) != set(EXPLICACAO_CLASSES):
        raise ValueError(f"Classes reais de {alvo!r} divergentes do dicionário documentado: {sorted(pd.unique(dados[alvo]).tolist())}.")
    return alvo


def diagnosticar(dados: pd.DataFrame, alvo: str) -> dict[str, Any]:
    """Imprime e retorna o diagnóstico para registrar a inspeção antes do treino."""
    print(f"Dimensões: {dados.shape[0]:,} linhas × {dados.shape[1]} colunas")
    print("Colunas:", dados.columns.tolist())
    print("Tipos:\n", dados.dtypes.to_string())
    print("Ausências:\n", dados.isna().sum().to_string())
    numericas = dados.select_dtypes(include=["number"]).columns.tolist()
    infinitos = {c: int(np.isinf(dados[c].dropna().astype(float)).sum()) for c in numericas}
    print("Valores infinitos:", infinitos)
    print("Distribuição das classes:\n", dados[alvo].value_counts(dropna=False).sort_index().to_string())
    if "timestamp" in dados:
        print(f"Período: {dados.timestamp.min()} a {dados.timestamp.max()}; timestamps repetidos: {dados.timestamp.duplicated().sum()}")
    categoricas = dados.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    print("Categóricas:", categoricas)
    print("Numéricas:", numericas)
    return {"shape": list(dados.shape), "columns": dados.columns.tolist(), "dtypes": dados.dtypes.astype(str).to_dict(),
            "missing": dados.isna().sum().astype(int).to_dict(), "infinite": infinitos,
            "class_counts": {str(k): int(v) for k, v in dados[alvo].value_counts().sort_index().items()}}


def dividir_cronologicamente(dados: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Separa 70/15/15 por tempo, respeitando timestamps inteiros em cada bloco."""
    if "timestamp" not in dados:
        raise ValueError("É necessária uma coluna timestamp válida para a separação temporal.")
    datas = pd.to_datetime(dados["timestamp"], errors="coerce")
    if datas.isna().any():
        raise ValueError("A coluna timestamp contém datas inválidas.")
    ordem = np.argsort(datas.to_numpy(), kind="stable")
    datas_ordenadas = datas.iloc[ordem].reset_index(drop=True)
    n = len(dados)
    corte_treino = int(n * .70)
    corte_validacao = int(n * .85)
    data_fim_treino = datas_ordenadas.iloc[corte_treino - 1]
    data_fim_validacao = datas_ordenadas.iloc[corte_validacao - 1]
    treino = np.flatnonzero((datas <= data_fim_treino).to_numpy())
    validacao = np.flatnonzero(((datas > data_fim_treino) & (datas <= data_fim_validacao)).to_numpy())
    teste = np.flatnonzero((datas > data_fim_validacao).to_numpy())
    if min(len(treino), len(validacao), len(teste)) == 0:
        raise ValueError("A divisão cronológica produziu um bloco vazio.")
    return treino, validacao, teste, f"Cronológica 70/15/15; treino ≤ {data_fim_treino}, validação até {data_fim_validacao}, teste posterior. Empates de timestamp ficam no mesmo bloco."


def montar_pipeline(modelo: Any, numericas: list[str], categoricas: list[str], escala: bool) -> Pipeline:
    """Monta o pré-processamento aprendível somente durante o fit do pipeline."""
    passos_numericos: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if escala:
        passos_numericos.append(("scaler", StandardScaler()))
    pipeline_numerico = Pipeline(passos_numericos)
    pipeline_categorico = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    transformador = ColumnTransformer(
        [("numeric", pipeline_numerico, numericas), ("categorical", pipeline_categorico, categoricas)],
        remainder="drop", verbose_feature_names_out=False,
    )
    return Pipeline([("preprocessor", transformador), ("model", modelo)])


def configuracoes_modelos() -> list[tuple[str, Any, bool, dict[str, Any]]]:
    """Pequena busca explícita de configurações sem validação cruzada aleatória."""
    configuracoes = []
    for c in [0.5, 2.0]:
        m = LogisticRegression(C=c, class_weight="balanced", max_iter=1500, random_state=SEMENTE)
        configuracoes.append(("LogisticRegression", m, True, m.get_params()))
    for profundidade, folha in [(None, 1), (16, 3), (20, 2)]:
        m = RandomForestClassifier(n_estimators=300, max_depth=profundidade, min_samples_leaf=folha,
                                   class_weight="balanced_subsample", n_jobs=-1, random_state=SEMENTE)
        configuracoes.append(("RandomForestClassifier", m, False, m.get_params()))
    for profundidade, folha in [(None, 1), (16, 3)]:
        m = ExtraTreesClassifier(n_estimators=250, max_depth=profundidade, min_samples_leaf=folha,
                                 class_weight="balanced", n_jobs=-1, random_state=SEMENTE)
        configuracoes.append(("ExtraTreesClassifier", m, False, m.get_params()))
    for profundidade, taxa in [(2, 0.05), (3, 0.08)]:
        m = GradientBoostingClassifier(n_estimators=120, learning_rate=taxa, max_depth=profundidade, random_state=SEMENTE)
        configuracoes.append(("GradientBoostingClassifier", m, False, m.get_params()))
    if XGB_DISPONIVEL:
        for profundidade, taxa in [(4, 0.08), (6, 0.05), (8, 0.04)]:
            m = XGBClassifier(
                n_estimators=250,
                max_depth=profundidade,
                learning_rate=taxa,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="mlogloss",
                random_state=SEMENTE,
                n_jobs=-1,
            )
            configuracoes.append(("XGBClassifier", m, False, m.get_params()))
    return configuracoes


def treinar(caminho_dataset: str | Path | None = None) -> dict[str, Any]:
    """Executa comparação temporal, teste final e grava artefatos e relatórios."""
    global CAMINHO_PARQUET, CAMINHO_CSV
    if caminho_dataset is not None:
        origem = Path(caminho_dataset).resolve()
        if not origem.is_file():
            raise FileNotFoundError(f"Dataset não encontrado: {origem}")
        dados = pd.read_parquet(origem) if origem.suffix == ".parquet" else pd.read_csv(origem, parse_dates=["timestamp"])
    else:
        dados, origem = carregar_dataset()
    alvo = identificar_alvo(dados)
    diagnostico = diagnosticar(dados, alvo)

    # timestamp é chave temporal e é excluído das features. Célula e liga são
    # contexto operacional nominal, não códigos ordinais nem IDs de linha.
    excluidas = [alvo, "timestamp"]
    features = [c for c in dados.columns if c not in excluidas]
    y = dados[alvo].copy()
    X = dados[features].copy()
    if "id_celula" in X.columns and X["id_celula"].nunique() < 2:
        X = X.drop(columns=["id_celula"])
    colunas_cat = X.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    colunas_num = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    if set(colunas_cat + colunas_num) != set(X.columns):
        raise ValueError(f"Há tipos de preditores sem tratamento: {sorted(set(X.columns) - set(colunas_cat + colunas_num))}")
    if np.isinf(X[colunas_num].to_numpy(dtype=float)).any():
        raise ValueError("Os preditores numéricos contêm infinitos; investigar antes de treinar.")
    treino, validacao, teste, estrategia = dividir_cronologicamente(dados)
    classes = sorted(pd.unique(y).tolist())
    for nome_bloco, indices in [("treino", treino), ("validação", validacao), ("teste", teste)]:
        contagens = y.iloc[indices].value_counts()
        ausentes = sorted(set(classes) - set(contagens.index.tolist()))
        if ausentes:
            raise ValueError(f"Bloco {nome_bloco} não contém todas as classes: {ausentes}; não é possível avaliar a comparação de forma válida.")
        print(f"{nome_bloco}: {len(indices):,} linhas; classes {contagens.sort_index().to_dict()}")
    print(f"Features usadas ({len(features)}): {features}; timestamp excluído para evitar proxy temporal direto.")
    print(f"Tipos de features: {len(colunas_num)} numéricas, {len(colunas_cat)} categóricas.")

    X_treino, y_treino = X.iloc[treino], y.iloc[treino]
    X_val, y_val = X.iloc[validacao], y.iloc[validacao]
    X_dev, y_dev = X.iloc[np.concatenate([treino, validacao])], y.iloc[np.concatenate([treino, validacao])]

    sample_weights_treino = compute_sample_weight("balanced", y_treino)
    sample_weights_dev = compute_sample_weight("balanced", y_dev)

    resultados: list[dict[str, Any]] = []
    melhores_por_familia: dict[str, tuple[float, float, Pipeline, dict[str, Any]]] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        for nome, estimador, escala, parametros in configuracoes_modelos():
            pipeline = montar_pipeline(estimador, colunas_num, colunas_cat, escala)
            if nome == "XGBClassifier":
                pipeline.fit(X_treino, y_treino, model__sample_weight=sample_weights_treino)
            else:
                pipeline.fit(X_treino, y_treino)
            previsao = pipeline.predict(X_val)
            probabilidades = pipeline.predict_proba(X_val) if hasattr(pipeline, "predict_proba") else None
            metricas = calcular_metricas(y_val, previsao, probabilidades, classes)
            registro = {"model": nome, "params": json.dumps(parametros, sort_keys=True, default=str), **metricas}
            resultados.append(registro)
            criterio = (metricas["recall_falhas_macro"], metricas["f1_macro"])
            if nome not in melhores_por_familia or criterio > melhores_por_familia[nome][:2]:
                melhores_por_familia[nome] = (*criterio, pipeline, parametros)
            print(f"{nome} {parametros}: recall falhas={metricas['recall_falhas_macro']:.3f}; F1 macro={metricas['f1_macro']:.3f}")

    comparacao = pd.DataFrame(resultados).sort_values(["recall_falhas_macro", "f1_macro"], ascending=False).reset_index(drop=True)
    familia_vencedora = comparacao.iloc[0]["model"]
    params_vencedores = melhores_por_familia[familia_vencedora][3]
    parametros_json_vencedores = json.dumps(params_vencedores, sort_keys=True, default=str)
    mascara_vencedora = (comparacao.model == familia_vencedora) & (comparacao.params == parametros_json_vencedores)
    linha_vencedora_validacao = comparacao.loc[mascara_vencedora].iloc[0]
    metricas_validacao = {
        chave: valor for chave, valor in linha_vencedora_validacao.to_dict().items()
        if chave not in {"params", "test_metrics"}
    }
    # Refita um representante validado de cada família em desenvolvimento, não no teste.
    pipelines_finais: dict[str, Pipeline] = {}
    for familia, (_, _, pipeline, params) in melhores_por_familia.items():
        final_familia = montar_pipeline(pipeline.named_steps["model"].__class__(**params), colunas_num, colunas_cat,
                                        isinstance(pipeline.named_steps["preprocessor"].named_transformers_["numeric"], Pipeline)
                                        and "scaler" in pipeline.named_steps["preprocessor"].named_transformers_["numeric"].named_steps)
        if familia == "XGBClassifier":
            final_familia.fit(X_dev, y_dev, model__sample_weight=sample_weights_dev)
        else:
            final_familia.fit(X_dev, y_dev)
        pipelines_finais[familia] = final_familia
    melhor_pipeline = pipelines_finais[familia_vencedora]
    previsoes_teste = melhor_pipeline.predict(X.iloc[teste])
    probabilidades_teste = melhor_pipeline.predict_proba(X.iloc[teste]) if hasattr(melhor_pipeline, "predict_proba") else None
    metricas_teste = calcular_metricas(y.iloc[teste], previsoes_teste, probabilidades_teste, classes)
    comparacao["test_metrics"] = ""
    comparacao.loc[mascara_vencedora, "test_metrics"] = json.dumps(metricas_teste, ensure_ascii=False)

    PASTA_MODELOS.mkdir(parents=True, exist_ok=True)
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)
    for familia, pipeline in pipelines_finais.items():
        joblib.dump(pipeline, PASTA_MODELOS / NOMES_ARQUIVOS[familia])
    joblib.dump(melhor_pipeline, PASTA_MODELOS / "best_model.joblib")

    timestamp_utc = datetime.now(timezone.utc).isoformat()
    metadados = {
        "model_name": familia_vencedora,
        "trained_at_utc": timestamp_utc,
        "dataset_path": str(origem.relative_to(RAIZ) if origem.is_relative_to(RAIZ) else origem),
        "dataset_format": origem.suffix.lstrip("."),
        "dataset_sha256": hashlib.sha256(origem.read_bytes()).hexdigest(),
        "dataset_diagnostic": diagnostico,
        "target": alvo,
        "features": features,
        "feature_order": features,
        "feature_types": {c: str(X[c].dtype) for c in features},
        "classes": [{"label": int(c), "name": EXPLICACAO_CLASSES.get(int(c), str(c))} for c in classes],
        "library_versions": {"python": __import__("sys").version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__},
        "best_parameters": params_vencedores,
        "validation_metrics": metricas_validacao,
        "test_metrics": metricas_teste,
        "split_strategy": estrategia,
        "split_counts": {"train": len(treino), "validation": len(validacao), "test": len(teste)},
        "random_seed": SEMENTE,
        "selection_criterion": "Maior recall macro das classes de falha (1, 2, 3) na validação temporal; desempate por F1 macro.",
        "limitations": ["tipo_falha é o rótulo do estado da leitura atual; a tarefa validada é classificação contemporânea, não previsão futura.", "A validação é temporal dentro das mesmas células; generalização para novas células não foi avaliada.", "Custos de falso positivo/falso negativo e horizonte operacional não foram fornecidos.", "Probabilidades não foram calibradas.", "A documentação descreve uma empresa fictícia e admite dados simulados; a origem deste dataset deve ser confirmada antes de extrapolar as métricas para uma fábrica real.", "O dataset tratado já contém interpolação offline feita antes da divisão; não há indicador de quais linhas foram interpoladas, então não é possível descartar completamente possível influência de leituras futuras próximas nas amostras de treino."],
    }
    (PASTA_MODELOS / "model_metadata.json").write_text(json.dumps(metadados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    salvar_relatorios(PASTA_RELATORIOS, comparacao, y.iloc[teste], previsoes_teste, probabilidades_teste, classes,
                      metricas_teste, familia_vencedora, params_vencedores)
    salvar_importancias(melhor_pipeline, PASTA_RELATORIOS)
    print(f"Modelo selecionado: {familia_vencedora}; teste: {metricas_teste}")
    print(f"Modelos: {PASTA_MODELOS}; relatórios: {PASTA_RELATORIOS}")

    print("Treinando detector de anomalias (Isolation Forest)...")
    res_detector = treinar_detector(origem)
    print(f"Detector de anomalias salvo: {res_detector['caminho_modelo']} (limiar={res_detector['limiar_normal']:.4f})")

    return {"best_model": familia_vencedora, "validation_comparison": comparacao, "test_metrics": metricas_teste,
            "features": features, "target": alvo, "model_dir": PASTA_MODELOS, "report_dir": PASTA_RELATORIOS,
            "anomaly_detector": res_detector}


if __name__ == "__main__":
    treinar()

