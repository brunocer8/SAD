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
| Critérios do SAW | VPL e payback do projeto, valor da alavancagem (retorno econômico); exposição regulatória; cobertura e ausência de dívida (preferências do decisor); probabilidade de prejuízo e VPL p10 (risco econômico) | ver seção 4 |

## 3. Modelo de energia e fluxo de caixa
Em cada mês *m* do ano *t*: `G = kWp x gerEsp x fDesempenho x share_m x (1-degr)^(t-1)`; autoconsumo `S = min(simult x G, fd x C)`; injeção `I = G - S`;
consumo abatível `N = max(C - S - disp, 0)`; os créditos `I` formam lotes por mês de origem, **expiram após 60 meses** (Lei 14.300/2022, art. 13) e são usados dos mais antigos para os mais novos: `U = min(créditos válidos, N)`.
`simult` (simultaneidade, 0,85; sorteada em 0,70 a 1,00) é uma **premissa**: sem curva de carga horária, só parte da geração coincide com a carga no mesmo instante; o restante é injetado.
Economia anual `= tarifa_t x (S + U) - tarifa_t x shareFioB x pctFioB(ano) x U` (Fio B só sobre a energia compensada; 60%, 75% e 90% em 2026, 2027 e 2028, art. 27; de 2029 em diante o art. 17 remete à regulamentação: adota-se 100% como cenário-base conservador e o Monte Carlo varre 60% a 100%).
**Fluxo do projeto** (sem financiamento): `CF0 = -investimento`; `CFt = economia - O&M - troca do inversor`. Dele saem o **VPL do projeto** e o **payback do projeto**, comparáveis entre tamanhos e formas de pagamento.
**Fluxo do capital próprio**: `CF0 = -(investimento - financiado)`; `CFt = economia - O&M - troca - parcelas`. Financiamento Price com carência de 6 meses (juros capitalizados); o prazo de 12 anos é **total** (carência incluída): 138 parcelas. A diferença entre o VPL do capital próprio e o do projeto mede o valor da alavancagem (dívida a 7,9% a.a. descontada a 12% a.a.).
Todos os fluxos são **nominais** e a taxa de desconto também. Potência: o limite legal de 75 kW refere-se à potência em **corrente alternada**; o protótipo limita os módulos a `75 x relação CC/CA` kWp (relação padrão 1,0), sem modelar o inversor.

## 4. Modelo de decisão (o que diferencia de um painel)
1. **Restrições técnicas**: potência (75 kW CA, aproximada em kWp) e área do telhado (7 m²/kWp, deve ser positiva); sem área para 3 kWp, não há alternativa e o sistema informa. O dimensionamento usa o VPL do **projeto**, independente da forma de pagamento.
2. **Filtro de viabilidade**: a alternativa só concorre se VPL > 0 e P(VPL > 0) >= 50% (Monte Carlo, no fluxo da própria alternativa). Reprovadas são exibidas, com o motivo, sem índice.
3. **SAW** entre as aprovadas e "Não instalar": `S_i = soma(w_j r_ij)`, normalização min-max (Hwang e Yoon, 1981). Quatro fatores, em ordem de preferência **assumida pelo autor (a validar com o decisor)**, convertida em pesos pelo método **ROC** (Barron e Barrett, 1996): 52,08%, 27,08%, 14,58%, 6,25%; dentro do fator, pesos iguais:
   - Retorno econômico (3 critérios): VPL do projeto, payback do projeto, valor da alavancagem por R$ financiado (separa a escolha da forma de pagamento do dimensionamento, sem premiar sistemas maiores só por terem mais dívida).
   - Exposição regulatória (1): parcela da economia que depende da compensação de créditos.
   - Preferências do decisor (2): cobertura do consumo; ausência de endividamento.
   - Risco econômico (2): probabilidade de prejuízo; VPL no percentil 10.
4. **Sensibilidade dos pesos** (±30%, 1.000 sorteios): frequência com que cada alternativa lidera e com que o líder supera cada uma.
5. **Agrupamento hierárquico** (ligação completa) do índice, com corte = raiz(2) x desvio médio do índice sob a sensibilidade. O corte é uma **heurística do projeto**, não um limite estatístico validado; por isso a frequência com que o líder supera cada alternativa acompanha o agrupamento.
6. **Recomendação** = maior índice, que pode ser "Não instalar". Se for a única alternativa, o índice não é exibido (seria artefato da normalização).

O índice SAW é **relativo ao conjunto** de alternativas (min-max): incluir ou excluir alternativas pode mudar o ranking; não é nota absoluta de viabilidade.
Escolhas do projeto (não vêm de norma): ordem dos fatores, limites 50%/90%/5 anos/90% do veredito, amplitude de 30%, 7 m²/kWp, simultaneidade, 100% de Fio B pós-2028.
Observações: o custo do Fio B em R$ **não** é critério, pois já reduz a economia (e o VPL). VPL, payback e VPL p10 são correlacionados; a correlação não foi removida, apenas reconhecida.

## 5. Validação
- **Testes automáticos** (`pytest -q`, 26 testes): balanço mensal e expiração de créditos de 60 meses conferidos por implementação independente em laços (FIFO); conservação de energia; simultaneidade; VPL recalculado manualmente; cronograma do financiamento (138 parcelas, saldo zera, parcelas e juros conferidos por cálculo independente, sem parcelas após o mês 144); VPL do projeto igual nas duas formas de pagamento; payback pelo primeiro cruzamento; área zero/negativa rejeitada; dimensionamento independente do flag de financiamento; pesos ROC; normalização; agrupamento; "Não instalar" pode vencer; reprovada nunca é recomendada; veredito usa o payback do projeto; API ponta a ponta.
- **Regressão** (`scripts/validar_regressao.py`, validação cruzada agrupada por município, 5 grupos): R² médio 0,956; MAE 0,081 kWh/kWp.dia; RMSE 0,096; erro percentual médio 1,9%. Coeficientes refeitos coincidem com os do arquivo. O erro tem **viés sazonal** (cerca de ±3%). Como o alvo é simulado, mede a aproximação do pvlib, **não** a precisão em usinas reais.
- **Caso concreto e estresse**: `docs/caso_demonstracao.md`. Os testes de estresse variam parâmetros do próprio modelo e portanto não substituem uma planilha independente nem orçamentos reais.

## 6. Limitações
- Alvo da regressão é simulação (pvlib), sem validação contra geração medida; há viés sazonal.
- Autoconsumo: usa fator de simultaneidade (premissa), não curva de carga horária; o resultado depende dele e a recomendação favorece sistemas que consomem quase toda a geração. Consumo mensal constante; sem Tarifa Branca nem grupo A.
- Potência: a restrição legal é em kW CA; o protótipo aproxima por kWp x relação CC/CA, sem modelar o inversor.
- Fio B: 28% da tarifa com tributos é estimativa, não a componente oficial da Coelba; a regra de 2029 em diante é cenário (60% a 100%).
- Financiamento: taxa de 7,9% a.a. é piso de referência, não garantida; o valor da alavancagem depende da diferença para a taxa de desconto (12%), o que favorece financiar. O payback do capital próprio do financiado (~0,16 ano) **não** é usado na decisão; só o payback do projeto.
- SAW: min-max amplia diferenças pequenas; resultado depende da ordem e do mapeamento dos fatores (preferências assumidas); critérios financeiros correlacionados; índice relativo ao conjunto.
- Agrupamento: corte heurístico.
- Retornos altos (payback ~1,5 ano) e Monte Carlo quase sem VPL negativo (P(VPL>0)=100%): P(VPL>0) discrimina pouco. Custos por kWp (Greener 1S/2026) não verificados nas fontes; materiais de 2023/2024 atribuídos à Greener indicavam paybacks e custos maiores. Obter orçamentos reais.
- TIR por bisseção devolve "n/d" sem raiz única no intervalo.
- O classificador é experimental, treinado em cenários sintéticos, e não participa da recomendação.

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
