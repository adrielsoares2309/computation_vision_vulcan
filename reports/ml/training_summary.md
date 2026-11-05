# Resumo do treinamento e avaliação

## Resultado

- Modelo selecionado: **RandomForestClassifier**.
- Seleção feita exclusivamente na validação cronológica, priorizando o recall macro das classes de falha (1, 2 e 3); empate resolvido pelo F1 macro.
- Hiperparâmetros do modelo: `{"bootstrap": true, "ccp_alpha": 0.0, "class_weight": "balanced_subsample", "criterion": "gini", "max_depth": null, "max_features": "sqrt", "max_leaf_nodes": null, "max_samples": null, "min_impurity_decrease": 0.0, "min_samples_leaf": 1, "min_samples_split": 2, "min_weight_fraction_leaf": 0.0, "monotonic_cst": null, "n_estimators": 300, "n_jobs": -1, "oob_score": false, "random_state": 42, "verbose": 0, "warm_start": false}`.
- Métricas no teste temporal final: accuracy 0.999, precision macro 0.996, recall macro 0.993, F1 macro 0.995, F1 ponderado 0.999, recall macro de falhas 0.991.
- ROC-AUC OVR macro: 0.9999873449223342; PR-AUC macro: 0.9997404949024694.

## Recall por classe no teste

| Classe | Recall |
|---|---:|
| Normal | 1.000 |
| Desgaste de ferramenta | 0.985 |
| Falha de refrigeração | 0.988 |
| Desalinhamento / trinca | 1.000 |

## Método e limitações

Os dados foram divididos cronologicamente em treino, validação e teste, aproximadamente 70%/15%/15%. O teste não participou da seleção ou ajuste. Imputação, codificação e escalonamento fazem parte de cada pipeline e são ajustados apenas no treino (ou, após a seleção, no conjunto de desenvolvimento treino + validação). Classes não foram reamostradas. O identificador da célula foi mantido como categoria contextual; o modelo não foi validado em células desconhecidas.

`tipo_falha` descreve a condição rotulada na própria leitura. Portanto, esta avaliação mede classificação contemporânea, não previsão antecipada de falhas futuras. A base não define horizonte de previsão nem custos operacionais de falsos positivos/falsos negativos. As probabilidades não foram calibradas. Importâncias de variáveis, se geradas, indicam associação preditiva e não causalidade.


## Uso

Na raiz do projeto, execute `python -m src.ml.train`. Para prever, forneça a `prever` um DataFrame com as colunas de entrada do modelo (sem timestamp e sem alvo); `src.ml.predict` carrega o pipeline completo e retorna classe prevista e probabilidades não calibradas. Exemplo: `prever(pd.read_parquet('novas_leituras.parquet'))`. Rode os testes com `python -m pytest tests/test_ml.py -q`.

## Proveniência e limites

A documentação descreve a empresa como fictícia e admite que os dados possam ser simulados. Confirme a origem deste arquivo antes de extrapolar as métricas a uma fábrica real. O Parquet tratado já contém interpolação offline executada antes da divisão temporal; como não há marcador de linhas interpoladas, possível influência de leituras futuras próximas não pode ser totalmente descartada.
