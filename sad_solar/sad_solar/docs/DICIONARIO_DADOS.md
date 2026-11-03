# Dicionário de dados

## dados/dataset_ba_modelo.csv (5.004 linhas = 417 municípios x 12 meses)
| Coluna | Unidade | Descrição |
|---|---|---|
| cod_ibge, municipio | - | identificação do município baiano |
| mes | 1 a 12 | mês de referência (climatologia mensal) |
| ghi | kWh/m².dia | irradiação global horizontal média (preditora) |
| fracao_difusa | adimensional | irradiação difusa / global (preditora) |
| temp_media | °C | temperatura média do ar (preditora) |
| geracao_dia | kWh/kWp.dia | alvo: geração específica simulada com pvlib (perdas de 14%) |
| geracao_especifica | kWh/kWp.mês | geracao_dia x dias do mês |
| demais (dif, dni, poa, par, inclinação, temp. de célula, pr) | variadas | variáveis intermediárias da simulação pvlib |

Origem declarada pelo autor: Atlas Solar/INPE e NASA POWER. **Completar**: versão, período de referência e resolução dos dados; script que gerou a simulação pvlib.

## dados/modelo_geracao_linear.json
Coeficientes MQO: geracao_dia = intercepto + b1*ghi + b2*fracao_difusa + b3*temp_media. Reproduzíveis com `python scripts/validar_regressao.py`.

## dados/validacao_regressao.csv
Métricas (R², MAE, RMSE, MAPE) por rodada da validação cruzada agrupada por município.

## modelos/
`cenarios_amostra.csv`, `metricas_classificador.csv`, `importancia_classificador.csv`, `regras_arvore.txt`, `classificador_arvore.joblib`: saídas do experimento offline do classificador (não entram na recomendação).

## parametros_premissas.csv
Gerado por `python parametros.py`: cada parâmetro com valor padrão, distribuição no Monte Carlo, tipo (fonte, estimado, premissa) e justificativa.
