# Relatório de Validação, Integração e Auditoria Visual (WCAG 2.2) — VulcanTech Smart Metals S.A.

## 1. Resumo Executivo da Validação Automatizada (`pytest`)

A integração entre os módulos de domínio (`src/oee/`, `src/data/`, `src/simulation/`, `src/ml/`, `src/vision/`), banco de dados SQLite (`database/`), backend FastAPI (`backend/`) e frontend industrial Streamlit (`frontend/`) foi validada por suíte automatizada (`pytest`) e por execução ao vivo dos processos (`iniciar_aplicacao.ps1`).

- **Total de Testes Executados**: **35 testes** (`35 passed`)
- **Falhas / Erros**: **0**
- **Suítes Cobertas**:
  - `tests/test_oee.py`: Fórmulas de Disponibilidade, Performance, Qualidade, OEE ponderado e tratamento seguro de denominadores nulos ou entradas inválidas.
  - `tests/test_api.py`: Testes de integração com `TestClient` cobrindo `/api/v1/health`, `/api/v1/ready`, `/api/v1/system/status`, `/api/v1/oee/*`, `/api/v1/vision/*`, `/api/v1/maintenance/*`, `/api/v1/sensors/*` e `/api/v1/simulation/*`.
  - `tests/test_frontend_client.py`: Validação do `VulcanTechAPIClient`, integração dos serviços do frontend com a API, tratamento de indisponibilidade (`APIConnectionError`) e **verificação matemática automatizada de contraste WCAG 2.2** (`test_wcag_22_design_tokens_contrast_compliance`).
  - `tests/test_ml.py` e `tests/test_vision.py`: Validação dos pipelines de Machine Learning tabular e Visão Computacional.

---

## 2. Matriz Verificada de Contraste WCAG 2.2 (`frontend/styles.py`)

Todas as combinações cromáticas definidas em `DESIGN_TOKENS` foram auditadas segundo a fórmula de luminância relativa da norma **WCAG 2.2** (mínimo de **4,5:1** para texto normal e **3,0:1** para elementos gráficos, ícones e indicadores de foco):

| Elemento / Contexto da Interface | Cor de Primeiro Plano | Cor de Fundo | Razão Calculada | Mínimo WCAG 2.2 | Resultado |
|---|---|---|---|---|---|
| Texto principal sobre superfície de painel/tabela | `#0F172A` | `#FFFFFF` | **17,85:1** | 4,5:1 | Aprovado (AAA) |
| Texto principal sobre fundo geral do app | `#0F172A` | `#F3F5F8` | **16,32:1** | 4,5:1 | Aprovado (AAA) |
| Texto secundário sobre superfície de card/tabela | `#334155` | `#FFFFFF` | **10,21:1** | 4,5:1 | Aprovado (AAA) |
| Texto secundário sobre superfície alternativa | `#334155` | `#F8FAFC` | **9,78:1** | 4,5:1 | Aprovado (AAA) |
| Rótulos/captions (`text_muted`) sobre superfície | `#475569` | `#FFFFFF` | **7,36:1** | 4,5:1 | Aprovado (AAA) |
| Rótulos/captions (`text_muted`) sobre painel | `#475569` | `#F8FAFC` | **7,05:1** | 4,5:1 | Aprovado (AAA) |
| Rótulos/captions (`text_muted`) sobre fundo do app | `#475569` | `#F3F5F8` | **6,73:1** | 4,5:1 | Aprovado (AA) |
| Sidebar: texto principal sobre fundo corporativo | `#F8FAFC` | `#0F1E36` | **15,62:1** | 4,5:1 | Aprovado (AAA) |
| Sidebar: texto secundário sobre fundo corporativo | `#CBD5E1` | `#0F1E36` | **10,99:1** | 4,5:1 | Aprovado (AAA) |
| Sidebar: título de seção (`MÓDULOS OPERACIONAIS`) | `#94A3B8` | `#0F1E36` | **6,46:1** | 4,5:1 | Aprovado (AA) |
| Sidebar: item de navegação selecionado | `#FFFFFF` | `#1D4ED8` | **6,70:1** | 4,5:1 | Aprovado (AA) |
| Sidebar: item de navegação em `:hover` | `#F8FAFC` | `#1A3154` | **12,72:1** | 4,5:1 | Aprovado (AAA) |
| Botão primário (estado normal) | `#FFFFFF` | `#0B4F9F` | **8,32:1** | 4,5:1 | Aprovado (AAA) |
| Botão primário (estado `:hover`) | `#FFFFFF` | `#083B7A` | **10,89:1** | 4,5:1 | Aprovado (AAA) |
| Botão secundário (estado normal) | `#0F172A` | `#FFFFFF` | **17,85:1** | 4,5:1 | Aprovado (AAA) |
| Botão secundário (estado `:hover`) | `#0F172A` | `#EFF6FF` | **16,28:1** | 4,5:1 | Aprovado (AAA) |
| Botão desabilitado (`:disabled`) | `#475569` | `#E2E8F0` | **5,74:1** | 4,5:1 | Aprovado (AA) |
| Badge Semântico Sucesso (`APROVADA` / `Normal`) | `#065F46` | `#ECFDF5` | **7,53:1** | 4,5:1 | Aprovado (AAA) |
| Badge Semântico Atenção (`ALERTA` / `Experimental`) | `#78350F` | `#FFFBEB` | **8,44:1** | 4,5:1 | Aprovado (AAA) |
| Badge Semântico Erro (`REPROVADA` / `Falha Crítica`) | `#991B1B` | `#FEF2F2` | **7,73:1** | 4,5:1 | Aprovado (AAA) |
| Badge Semântico Neutro (`INDETERMINADA` / `N/D`) | `#334155` | `#F1F5F9` | **9,16:1** | 4,5:1 | Aprovado (AAA) |
| Badge Semântico Info (`SIMULADO` / `API`) | `#1E3A8A` | `#EFF6FF` | **8,92:1** | 4,5:1 | Aprovado (AAA) |
| Série gráfica azul sobre canvas branco | `#0B4F9F` | `#FFFFFF` | **8,32:1** | 3,0:1 | Aprovado |
| Série gráfica teal sobre canvas branco | `#0F766E` | `#FFFFFF` | **5,44:1** | 3,0:1 | Aprovado |
| Série gráfica âmbar sobre canvas branco | `#B45309` | `#FFFFFF` | **5,02:1** | 3,0:1 | Aprovado |
| Série gráfica vermelha sobre canvas branco | `#B91C1C` | `#FFFFFF` | **6,47:1** | 3,0:1 | Aprovado |
| Anel de foco (`:focus-visible`) sobre fundo claro | `#1D4ED8` | `#FFFFFF` | **6,70:1** | 3,0:1 | Aprovado |

---

## 3. Revisão dos 10 Critérios de Interface Industrial (Estilo MES / SCADA / TOTVS)

1. **Aparência de software industrial comercial**: Sidebar escura compacta (`#0F1E36`), fundo de área de trabalho cinza-claro técnico (`#F3F5F8`), superfícies brancas com bordas estruturadas (`1px solid #CBD5E1`) e tipografia tabular monoespaçada (`JetBrains Mono`) para valores numéricos e IDs de células.
2. **Ausência de textos explicativos longos ou elementos decorativos**: Foram removidos os parágrafos introdutórios e avisos extensos permanentes no meio das telas; notas técnicas residem em badges discretos ou expanders recolhidos.
3. **Hierarquia visual clara**: Barra de cabeçalho curta com título, escopo ativo, badge de fonte de dados e botão de atualização na mesma linha.
4. **Contraste de botões em todos os estados**: Corrigido o bug do botão primário em `:hover` (que antes ficava azul sobre azul); agora o estado `:hover` escurece para `#083B7A` mantendo texto `#FFFFFF` (contraste `10,89:1`).
5. **Legibilidade de textos sobre fundos**: Todos os pares texto/fundo possuem razão $\ge 5,74:1$.
6. **Gráficos compreensíveis e equilibrados**: Alturas padronizadas (`210px` a `320px`), paleta de alto contraste e organização em abas operacionais (`st.tabs`) para evitar empilhamento excessivo.
7. **Alinhamento consistente de filtros e tabelas**: Filtros integrados em uma única barra superior próxima aos KPIs e dados que controlam.
8. **Responsividade**: Uso de `grid-template-columns` com media queries para telas menores (`@media (max-width: 980px)`).
9. **Identidade visual unificada nas 3 páginas**: `OEE`, `Visão Computacional` e `Manutenção Preditiva` compartilham o mesmo cabeçalho `.vt-header-bar`, cartões `.vt-kpi`, painéis `.vt-panel` e badges `.vt-badge` com ícone SVG + rótulo.
10. **Estados de erro, carregamento e indisponibilidade claros**: Indicadores `N/D`, `INDETERMINADA` e `API OFFLINE` comunicados com ícone vetorial + texto + cor sem substituir silenciosamente dados reais por mocks.
