# Treinamento e validação funcional de visão computacional

## Dados inspecionados

4 imagens válidas, 0 inválidas e 0 ausentes; 0 grupos de cópias exatas. Distribuição por modalidade e classe: `{'termica/APROVADA': 1, 'termica/REPROVADA': 1, 'visual/APROVADA': 1, 'visual/REPROVADA': 1}`.

| Arquivo | Rótulo recebido | Modalidade | Leitura |
|---|---|---|---|
| data\raw\imagens\solda_aprovada.png | APROVADA | visual | válida |
| data\raw\imagens\solda_reprovada.png | REPROVADA | visual | válida |
| data\raw\imagens\termica_solda_aprovada.png | APROVADA | termica | válida |
| data\raw\imagens\termica_solda_reprovada.png | REPROVADA | termica | válida |

Os rótulos iniciais são obtidos dos nomes de arquivo informados no escopo; não há anotação especializada independente nos arquivos para confirmar o estado metalúrgico. `APROVADA=0`, `REPROVADA=1`.

## Estratégia e estado

Arquitetura demonstrativa: descritores OpenCV HOG + histogramas RGB e médias espaciais, padronizados e classificados por 1-vizinho mais próximo. Foram treinados classificadores separados para as modalidades visual e térmica. Nenhum peso externo foi baixado. PyTorch e torchvision não estão instalados no ambiente; transfer learning não foi executado.

O modo de quatro imagens foi explicitamente autorizado pelo argumento `--allow-tiny-dataset`. Há apenas um exemplar por classe em cada modalidade, portanto cada modelo foi ajustado nesses dois exemplos e não existe conjunto independente de validação ou teste. Nenhuma acurácia, matriz de confusão de teste ou métrica de generalização é reportada. Os artefatos estão marcados como experimentais e inadequados para decisão industrial.

## Limitações

HOG e histogramas são um baseline clássico, não uma rede profunda pré-treinada. O classificador memoriza os poucos exemplos; seus escores de similaridade não são probabilidades calibradas. As imagens térmicas são RGB de falsa cor, sem dados de calibração para inferir graus Celsius. Como a empresa é fictícia e o projeto admite dados simulados, confirme a origem das imagens antes de qualquer interpretação industrial.

## Próxima coleta e execução

Adicione imagens reais independentes em `data/processed/vision/{visual,termica}/{aprovada,reprovada}/` ou liste-as em `labels.csv` com colunas `path,label,modality,group_id`. Use `group_id` igual para vistas do mesmo corpo de prova, evitando vazamento entre treino e teste. O modo normal exige ao menos 20 grupos independentes por classe e modalidade; após isso, executa divisão agrupada 70/15/15 e relata métricas separadas por modalidade.

Comandos: `python -m src.vision.train --inspect-only`, `python -m src.vision.train --allow-tiny-dataset` e `python -m pytest tests/test_vision.py -q`.
