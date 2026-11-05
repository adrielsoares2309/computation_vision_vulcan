# Pipeline de Dados e Engenharia de Atributos (Data Pipeline)

## 1. Visão Geral do Dataset

O conjunto de dados original (`data/raw/dados_sensores_vulcantech.csv`) compreende **10.000 registros cronológicos** amostrados a cada **5 minutos** em 4 células operacionais (`CEL-201`, `CEL-202`, `CEL-203`, `CEL-204`) sob 3 ligas metálicas com propriedades tribológicas e usinabilidade distintas:
- `Aco_Carbono_316L`
- `Aluminio_7075`
- `Liga_Titanio_Ti6Al4V`

---

## 2. Diagnóstico de Qualidade e Saneamento

### 2.1. Sentinelas de Ruído Identificados
- **Temperatura do fuso (`temperatura_fuso_c`):** Ocorrência de valores espúrios `999.9 °C` decorrentes de circuito aberto em termopares (250 registros).
- **Vibração triaxial (`vibracao_triaxial_rms_mms`):** Ocorrência de `-99.0 mm/s` causada por perda momentânea de alimentação em acelerômetros piezoelétricos (250 registros).
- **Pressão hidráulica (`pressao_hidraulica_bar`):** Ocorrência de `-1.0 bar` causada por transdutor em saturação negativa (200 registros).

### 2.2. Tratamento e Interpolação Condicional
Os valores sentinela são convertidos em `NaN` e submetidos a uma **interpolação linear temporal segregada por equipamento (`id_celula`)**, assegurando que falhas transitórias de uma célula nunca sofram vazamento ou contaminação de dados de outras máquinas vizinhas.

---

## 3. Feature Engineering Industrial

Atendendo integralmente aos requisitos da **Etapa 1 do Projeto Integrador**, foram criadas as seguintes variáveis calculadas:

### 3.1. Índice de Esforço Mecânico (IEM)
Indicador compósito que correlaciona o torque mecânico e a vibração com a refrigeração disponível:

$$\text{IEM} = \frac{\text{Torque\_Fuso\_Nm} \times \text{Vibracao\_Triaxial\_RMS\_mms}}{\text{Vazao\_Refrigerante\_lmin} + 1}$$

- Valores elevados indicam sobrecarga de usinagem com atrito excessivo e lubrificação deficiente.
- O termo $+1$ no denominador previne indefinição aritmética por divisão por zero.

### 3.2. Médias e Desvios Padrão Móveis (Rolling Features)
Calculados em janelas cronológicas por equipamento:
- **Janela de 30 minutos:** 6 períodos de 5 minutos (`rolling_mean_30m`, `rolling_std_30m`).
- **Janela de 2 horas:** 24 períodos de 5 minutos (`rolling_mean_2h`, `rolling_std_2h`).
- Aplicados sobre: Temperatura, Vibração, Torque e Corrente.

### 3.3. Normalização e Z-Score Condicional por Liga Metálica
Para evitar falsos alarmes em materiais de elevada resistência mecânica (como a liga de Titânio Ti6Al4V em comparação com o Alumínio 7075):
- **Razão Normalizada:** $X_{\text{norm}} = X / \mu_{\text{liga}}$
- **Z-Score Condicional:** $Z_{\text{liga}} = (X - \mu_{\text{liga}}) / \sigma_{\text{liga}}$

---

## 4. Esquema Final dos Dados Tratados

O arquivo resultante `data/processed/dados_sensores_vulcantech_features.parquet` possui **10.000 linhas × 36 colunas**:
1. `timestamp`
2. `id_celula`
3. `liga_metalica`
4. `temperatura_fuso_c`
5. `vibracao_triaxial_rms_mms`
6. `torque_fuso_nm`
7. `vazao_refrigerante_lmin`
8. `corrente_estator_amp`
9. `pressao_hidraulica_bar`
10. `nivel_ruido_db`
11. `tipo_falha` (alvo supervisionado: 0=Normal, 1=Desgaste, 2=Refrigeração, 3=Desalinhamento/Trinca)
12. `indice_esforco_mecanico`
13-20. Médias e desvios móveis (30m)
21-28. Médias e desvios móveis (2h)
29-32. Variáveis normalizadas pela média da liga
33-36. Z-scores condicionais da respectiva liga

