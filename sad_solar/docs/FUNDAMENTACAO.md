# Fundamentação teórica, modelo e validação

## 1. Classificação da decisão
- **Nível gerencial: estratégico** (Anthony, 1965): investimento de longo prazo (25 anos), alocação de capital e efeito sobre o custo operacional futuro. Em PMEs pequenas pode ser tratada como decisão tática; a classificação depende do porte e do peso do investimento no caixa.
- **Estruturação: semiestruturada** (Simon, 1960; Gorry e Scott Morton, 1971): os cálculos energéticos e financeiros seguem regras matemáticas (parte estruturada), mas o tamanho, a forma de pagamento e a aceitação de risco dependem de preferências do decisor e de premissas incertas (parte não estruturada).

## 2. Variáveis e justificativa
| Grupo | Variáveis | Fundamento |
|---|---|---|
| Entrada do decisor | município, consumo mensal, tarifa com tributos, área do telhado, fração do consumo diurno | descrevem a empresa; a fração diurna define quanto da geração é autoconsumida |
| Regressão (alvo e preditoras) | alvo: geração específica diária (kWh/kWp.dia) simulada com pvlib; preditoras: irradiação global (ghi), fração difusa, temperatura média | modelos de produção FV (pvlib, PVWatts) dependem de irradiância, componente difusa e temperatura de célula (Holmgren et al., 2018; Dobos, 2014) |
| Indicadores econômicos | investimento, economia, VPL, TIR, payback, LCOE | engenharia econômica (Brealey, Myers e Allen) |
| Incerteza | reajuste tarifário, custo, desempenho real, degradação, O&M, inversor, taxas | Monte Carlo para análise de risco de investimentos (Hertz, 1964); distribuições e fontes em `parametros.py` |
| Critérios do SAW | VPL, payback (Teórica); exposição regulatória (Normativa/Legal); cobertura, ausência de dívida (Preferências/"Cultural"); prob. de prejuízo, VPL p10 (Risco) | ver seção 4 |

## 3. Modelo de energia e fluxo de caixa
Em cada mês *m* do ano *t*: `G = kWp x gerEsp x fDesempenho x share_m x (1-degr)^(t-1)`; autoconsumo `S = min(G, fd x C)`; injeção `I = G - S`;
consumo abatível `N = max(C - S - disp, 0)`; uso de créditos `U = min(saldo + I, N)`; `saldo <- saldo + I - U`.
Economia anual `= tarifa_t x (S + U) - tarifa_t x shareFioB x pctFioB(ano) x U` (Fio B só sobre a energia compensada; 60%, 75% e 90% em 2026, 2027 e 2028, Lei 14.300/2022, art. 27; de 2029 em diante adotado 100% como premissa conservadora, sorteado entre 90% e 100% no Monte Carlo).
Fluxo: `CF0 = -(investimento - financiado)`; `CFt = economia - O&M - troca do inversor - parcelas`. Todos os fluxos são **nominais** e a taxa de desconto (12% a.a.) também é **nominal**. O investimento entra como saída em t=0 e o empréstimo como entrada em t=0, o que torna à vista e financiado comparáveis (teste `test_financiamento_fluxo_comparavel_ao_a_vista`).

## 4. Modelo de decisão (o que diferencia de um painel)
1. **Restrições técnicas**: potência <= 75 kWp e área do telhado (7 m²/kWp); sem área para 3 kWp, não há alternativa e o sistema informa.
2. **Filtro de viabilidade**: alternativa só concorre se VPL > 0 e P(VPL > 0) >= 50% (Monte Carlo). Reprovadas são exibidas, com o motivo, sem índice.
3. **SAW** entre as aprovadas e "Não instalar": `S_i = soma(w_j r_ij)`, normalização min-max (Hwang e Yoon, 1981). Pesos: ordem de preferência dos quatro fatores (Teórica > Normativa/Legal > Cultural > Risco) convertida pelo método **ROC** (Barron e Barrett, 1996): 52,08%, 27,08%, 14,58%, 6,25%; dentro do fator, pesos iguais.
4. **Sensibilidade dos pesos** (±30%, 1.000 sorteios): mostra com que frequência cada alternativa lidera.
5. **Agrupamento hierárquico** do índice com corte = raiz(2) x desvio médio do índice sob a sensibilidade.
6. **Recomendação** = maior índice, que pode ser "Não instalar".

Escolhas do projeto (não vêm de norma): ordem e mapeamento dos fatores, limites 50%/90%/5 anos/90% do veredito, amplitude de 30%, 7 m²/kWp.
Observação: o custo do Fio B em R$ **não** é critério do SAW porque já reduz a economia (e o VPL); contá-lo de novo seria dupla contagem.

## 5. Validação
- **Testes automáticos** (`pytest -q`, 17 testes): balanço de energia conferido por implementação independente em laços; conservação de energia; créditos não negativos; VPL recomputado manualmente; fluxo financiado comparável ao à vista; área insuficiente; limite de 75 kWp; pesos ROC somam 1; normalização; agrupamento; "Não instalar" pode vencer; alternativa reprovada nunca é recomendada; veredito do financiado usa o payback do financiado; API ponta a ponta.
- **Regressão** (`scripts/validar_regressao.py`, validação cruzada agrupada por município, 5 grupos): R² médio 0,956; MAE 0,081 kWh/kWp.dia; RMSE 0,096; erro percentual médio 1,9%. Coeficientes refeitos coincidem com os do arquivo. O erro tem **viés sazonal** (cerca de -0,12 em dezembro e +0,12 em março, ~±3%), pois um modelo linear não capta toda a sazonalidade. Como o alvo é simulado, a métrica mede a aproximação do pvlib, **não** a precisão em usinas reais.
- **Caso concreto e estresse**: `docs/caso_demonstracao.md`.

## 6. Limitações
- Alvo da regressão é simulação (pvlib), sem validação contra geração medida.
- Consumo mensal constante; fração diurna única; créditos sem prazo de validade de 60 meses; sem Tarifa Branca nem demanda contratada (Grupo A).
- A normalização min-max amplia diferenças pequenas; o resultado depende dos pesos e do mapeamento de critérios, que são preferências do decisor.
- VPL, p10 e probabilidade de prejuízo são correlacionados (dupla contagem parcial de preferência por retorno/risco).
- Com as premissas atuais o Monte Carlo quase nunca produz VPL negativo, então P(VPL>0) discrimina pouco; o payback do financiado é muito curto porque a taxa de financiamento (7,9%) é bem inferior ao retorno do projeto.
- Os retornos são altos (payback ~1,5 ano no caso-base); a tabela de custo por kWp (Greener 1S/2026) e o Fio B de 28% da tarifa devem ser conferidos nas fontes originais antes de citar. Para comparação, material citado pela imprensa da Greener de 2023 apontava payback de 2,4 anos para sistemas comerciais de 50 kWp.
- A TIR por bisseção devolve "n/d" quando o fluxo não cruza zero uma única vez (ex.: financiado com TIR altíssima).
- O classificador é experimental e treinado em cenários sintéticos.

## 7. Referências
- ANEEL. Resolução Normativa nº 1.000/2021; Resolução Homologatória nº 3.578/2026 (tarifas Coelba).
- Anthony, R. N. *Planning and Control Systems: A Framework for Analysis*. Harvard University, 1965.
- Barron, F. H.; Barrett, B. E. Decision quality using ranked attribute weights. *Management Science*, 42(11), 1515-1523, 1996.
- Brasil. Lei nº 14.300, de 6 de janeiro de 2022 (marco legal da microgeração e minigeração distribuída).
- Brealey, R. A.; Myers, S. C.; Allen, F. *Principles of Corporate Finance* (edição e capítulos de orçamento de capital a registrar).
- Dobos, A. P. *PVWatts Version 5 Manual*. NREL/TP-6A20-62641, 2014.
- Gorry, G. A.; Scott Morton, M. S. A framework for management information systems. *Sloan Management Review*, 13(1), 55-70, 1971.
- Han, J.; Kamber, M.; Pei, J. *Data Mining: Concepts and Techniques*. Morgan Kaufmann (funções de mineração: sumarização, agrupamento, regressão, classificação).
- Hertz, D. B. Risk analysis in capital investment. *Harvard Business Review*, 42(1), 95-106, 1964.
- Holmgren, W. F.; Hansen, C. W.; Mikofski, M. A. pvlib python: a python package for modeling solar energy systems. *Journal of Open Source Software*, 3(29), 884, 2018.
- Hwang, C.-L.; Yoon, K. *Multiple Attribute Decision Making: Methods and Applications*. Springer, 1981.
- Simon, H. A. *The New Science of Management Decision*. Harper & Row, 1960.
- Turban, E.; Sharda, R.; Delen, D. *Decision Support and Business Intelligence Systems* (edição a registrar).
- Greener. Estudo Estratégico: Geração Distribuída, mercado fotovoltaico, 1S/2026 (indicar tabela exata dos preços por kWp).
- Dados de irradiação: Atlas Solar/INPE e NASA POWER (indicar versão e período utilizados).
