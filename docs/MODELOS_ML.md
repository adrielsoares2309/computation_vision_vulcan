# Modelos de Machine Learning e Detecção de Anomalias

## 1. Formulação do Problema

O objetivo analítico é identificar falhas operacionais e desgastes mecânicos em tempo real a partir do vetor multivariado de sensores.
A variável-alvo é `tipo_falha`, categorizada em:
- **Classe 0:** Operação Normal
- **Classe 1:** Desgaste de Ferramenta
- **Classe 2:** Falha de Refrigeração
- **Classe 3:** Desalinhamento / Trinca Estrutural

---

## 2. Metodologia de Divisão Cronológica (Time-Series Split)

Para simular o ambiente fabril real e evitar qualquer forma de vazamento temporal (data leakage):
- **Treino (70% inicial):** Primeiros 7.000 registros (amostras até momento $T_1$).
- **Validação (15% intermediário):** Próximos 1.500 registros (entre $T_1$ e $T_2$).
- **Teste Cego (15% final):** Últimos 1.500 registros (estritamente posteriores a $T_2$).

A seleção de modelos e hiperparâmetros foi realizada **exclusivamente no conjunto de validação**. O conjunto de teste permaneceu intocado até a avaliação cega final.

---

## 3. Comparação de Algoritmos na Validação

| Modelo | Recall Falhas Macro | F1-Score Macro | Acurácia |
|---|:---:|:---:|:---:|
| **RandomForestClassifier** | **99.5%** | **99.6%** | **99.8%** |
| **XGBClassifier** | **99.5%** | **99.6%** | **99.8%** |
| **ExtraTreesClassifier** | 98.5% | 98.9% | 99.4% |
| **GradientBoostingClassifier** | 99.1% | 99.5% | 99.7% |
| **LogisticRegression** (Baseline) | 88.4% | 89.2% | 91.5% |

**Modelo Selecionado:** `RandomForestClassifier` (n_estimators=300, max_depth=None, class_weight="balanced_subsample").
O `XGBClassifier` também alcançou desempenho excelente de 99.5% de recall, comprovando a robustez dos modelos de árvore ensemble.

---

## 4. Desempenho no Teste Temporal Final

No conjunto de teste cego (1.500 amostras mais recentes da fábrica):
- **Acurácia Global:** 99.87%
- **Recall Macro de Falhas (Classes 1, 2 e 3):** **99.07%** (Meta do projeto: $\ge 90\%$)
- **F1-Score Macro:** 99.47%
- **ROC-AUC OVR Macro:** 0.99998
- **PR-AUC Macro:** 0.99974

### Recall Detalhado por Classe no Teste:
- **Classe 0 (Normal):** 100.0%
- **Classe 1 (Desgaste Ferramenta):** 98.5%
- **Classe 2 (Falha Refrigeração):** 98.8%
- **Classe 3 (Desalinhamento/Trinca):** 100.0%

---

## 5. Detector de Anomalias Não Supervisionado (Isolation Forest)

Como redundância de segurança, implementou-se o **Isolation Forest** (`models/tabular/anomaly_detector.joblib`):
- Treinado exclusivamente sobre o regime nominal (Classe 0).
- Normalização min-max sigmoidal: produz um escore de anomalia calibrado de $0.0$ (normal) a $1.0$ (anomalia crítica).
- Limiar operacional de alarme: escore $> 0.50$.
- Capacidade de sinalizar desvios em regime transitório antes da ocorrência de dano funcional.

