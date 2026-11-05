# Gestão e Cálculo do OEE (Overall Equipment Effectiveness)

## 1. Fundamentos e Fórmulas Oficiais

O OEE mede a eficiência real com que o tempo produtivo planejado é convertido em peças conformes:

$$\text{OEE} = \text{Disponibilidade} \times \text{Desempenho} \times \text{Qualidade}$$

### 1.1. Disponibilidade (Availability - A)
Razão entre o tempo em que a célula efetivamente operou e o tempo que estava planejado para operar:

$$A = \frac{\text{Tempo Operacional}}{\text{Tempo Planejado}} = \frac{\text{Tempo Planejado} - \text{Tempo de Paradas}}{\text{Tempo Planejado}}$$

### 1.2. Desempenho (Performance - P)
Mede perdas de velocidade e pequenas paradas operacionais:

$$P = \frac{\text{Tempo de Ciclo Ideal} \times \text{Produção Total}}{\text{Tempo Operacional}}$$

### 1.3. Qualidade (Quality - Q)
Proporção de peças aprovadas em relação ao total de peças processadas:

$$Q = \frac{\text{Produção Conforme (Boas)}}{\text{Produção Total}} = \frac{\text{Produção Total} - \text{Refugo}}{\text{Produção Total}}$$

---

## 2. Regra de Agregação Ponderada

Em conformidade com as boas práticas MES/SCADA:
> **Regra Crítica:** O OEE consolidado de múltiplos lotes, turnos ou células **NUNCA** é calculado como a média simples dos percentuais. Os denominadores e numeradores físicos (minutos e contagens de peças) são somados separadamente para garantir consistência física.

---

## 3. Impacto Preditivo no OEE (`predictive_impact.py`)

A conexão entre a inteligência preditiva e a gestão industrial permite antecipar a degradação de OEE:

| Falha Prevista | MTTR Estimado | Impacto em A | Impacto em P | Impacto em Q |
|---|:---:|:---:|:---:|:---:|
| **Desgaste de Ferramenta (1)** | 45 min | Parada para troca de inserto | Perda de 8% de feed | Aumento de refugo em 4.5% |
| **Falha de Refrigeração (2)** | 90 min | Parada para desobstrução | Perda de 15% de velocidade | Aumento de refugo em 9.0% |
| **Desalinhamento/Trinca (3)** | 180 min | Parada para calibração geométrica | Perda de 30% de feed | Aumento de refugo em 18.0% |

### Quantificação de Perdas Financeiras:
$$\text{Perda Total (R\$)} = (\text{Horas Paradas Não Planejadas} \times 4.500) + (\text{Peças Rejeitadas} \times 850)$$

- **Custo de Máquina Parada:** R\$ 4.500,00 / hora
- **Custo de Peça Nobre Refugada (Titânio/316L):** R\$ 850,00 / unidade
- **Economia com Ação Preditiva Antecipada:** Estima-se recuperação de até **75% das perdas evitáveis**.

