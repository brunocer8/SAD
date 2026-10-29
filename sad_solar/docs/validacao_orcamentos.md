# Comparação exploratória do SAD com estimativas comerciais (Salvador)

**Natureza:** as referências são estimativas comerciais de um fornecedor (NeoSolar) e duas calculadoras (Portal Solar, WEG), não medições de geração de sistemas instalados. Os quatro orçamentos NeoSolar de 10/20/30/40 kWp são do mesmo fornecedor e compartilham premissas; não são fontes independentes. Os cinco registros foram conferidos nos PDFs de orçamento fornecidos pelo autor (`conferido_no_pdf_anexado = sim`). A regressão do SAD foi treinada com geração simulada (pvlib); esta comparação não a valida empiricamente.

## 1. Geração específica (kWh/kWp CC por mês)

SAD: Salvador = 130.6 kWh/kWp.mês pela regressão (= 4.29 kWh/kWp.dia) x fator de desempenho 0.95 = **124.0**. Cadeia auditada: geracao_dia (kWh/kWp.dia) x dias do mês = kWh/kWp.mês; soma dos 12 meses = kWh/kWp.ano; multiplicada por kWp instalado (CC) e pelo fator de desempenho. Sem mistura de unidades encontrada. Diferença % = (SAD - referência) / **referência**.

| Referência | kWp CC | Geração ref. (kWh/mês) | Ref. (kWh/kWp.mês) | SAD (kWh/kWp.mês) | Diferença % (denominador: referência) | Conferido no PDF |
|---|---|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 54.0 | 4,839 | 89.6 | 124.0 | +38.4% | sim |
| NeoSolar 10 kWp | 10.8 | 850 | 78.7 | 124.0 | +57.6% | sim |
| NeoSolar 20 kWp | 23.4 | 1,750 | 74.8 | 124.0 | +65.8% | sim |
| NeoSolar 30 kWp | 36.0 | 2,650 | 73.6 | 124.0 | +68.5% | sim |
| NeoSolar 40 kWp | 48.6 | 3,550 | 73.0 | 124.0 | +69.8% | sim |
| Portal Solar (calculadora, 80 x 555 Wp) | 44.4 | 5,799 | 130.6 | 124.0 | -5.0% | n/a (imagem) |

**Discrepância NÃO resolvida:** as propostas NeoSolar estimam entre 73 e 90 kWh/kWp.mês, o SAD estima 124, e a Portal Solar ~131. A NeoSolar declara base NREL/NASA, inclinação ideal, orientação norte e sem sombreamento; não declara perdas, local exato nem PR. Não foi possível explicar a diferença com as informações disponíveis. Os coeficientes da regressão NÃO foram ajustados para coincidir com os orçamentos.

## 2. Custo instalado por kWp CC

| Referência | Investimento (R$) | R$/kWp CC | R$/Wp |
|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 270,812.25 | 5,015 | 5.02 |
| NeoSolar 10 kWp | 57,675.69 | 5,340 | 5.34 |
| NeoSolar 20 kWp | 122,743.82 | 5,245 | 5.25 |
| NeoSolar 30 kWp | 185,421.00 | 5,151 | 5.15 |
| NeoSolar 40 kWp | 245,707.22 | 5,056 | 5.06 |
| Tabela Greener (referência de baixo custo, 40 a 55 kWp) | - | 2,020 | 2.02 |
| Padrão do SAD (tabela x fator 1,20) | - | 2,424 | 2.42 |

A NeoSolar é um fornecedor; seu preço não é tratado como preço de mercado. O SAD aceita orçamento real (campo `custo_kwp`) e o usa como custo fixo.

## 3. Payback e TIR: duas análises separadas

A economia da proposta NeoSolar é bruta (geração x R$ 0,90, conta residual de R$ 45; o PDF avisa que não inclui iluminação pública nem custo de disponibilidade). A do SAD é líquida (mínimo faturável, Fio B, O&M, troca de inversor). Todas as propostas NeoSolar declaram tarifa R$ 0,90, inflação de energia de 8% a.a. e perda de 0,7%/ano, replicadas aqui (inflação e perda) na tabela 3a e 3b; o consumo é o informado na proposta (campo sem solar).

### 3a. Com o INVESTIMENTO exato de cada proposta (isola o modelo financeiro)

| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |
|---|---|---|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 4,889 | 270,812 | 6,697 | 4.5 | 5.20 | 33.1% | 23.6% |
| NeoSolar 10 kWp | 900 | 57,676 | 1,339 | 5.3 | 6.31 | 27.5% | 19.8% |
| NeoSolar 20 kWp | 1,800 | 122,744 | 2,902 | 5.4 | 6.38 | 26.7% | 19.6% |
| NeoSolar 30 kWp | 2,700 | 185,421 | 4,465 | 5.4 | 6.33 | 26.7% | 19.7% |
| NeoSolar 40 kWp | 3,600 | 245,707 | 6,028 | 5.4 | 6.26 | 27.0% | 19.9% |

### 3b. Com o CUSTO-PADRÃO do SAD (mostra o efeito da premissa de custo)

| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |
|---|---|---|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 4,889 | 134,317 | 6,697 | 4.5 | 2.75 | 33.1% | 41.7% |
| NeoSolar 10 kWp | 900 | 29,588 | 1,339 | 5.3 | 3.50 | 27.5% | 33.6% |
| NeoSolar 20 kWp | 1,800 | 58,781 | 2,902 | 5.4 | 3.32 | 26.7% | 35.2% |
| NeoSolar 30 kWp | 2,700 | 87,264 | 4,465 | 5.4 | 3.24 | 26.7% | 36.0% |
| NeoSolar 40 kWp | 3,600 | 117,806 | 6,028 | 5.4 | 3.25 | 27.0% | 35.8% |

Calculadoras (consumo 4.889 kWh/mês, R$ 0,90, investimento da referência): 

| Referência | Payback ref. (anos) | Payback SAD |
|---|---|---|
| Portal Solar (menor valor) | 2.75 | 1.86 |
| Portal Solar (maior valor) | 2.75 | 2.24 |
| WEG (kWp assumido 40) | 3.8 | 1.98 |

## 4. Sensibilidade de baixa geração (NÃO é previsão)

Cenário separado da regressão: o fator de desempenho é multiplicado por 0.63 (média da geração específica das propostas NeoSolar dividida pela do SAD), apenas para mostrar o efeito caso a geração real fique no nível dessas propostas. Origem: comparação com estimativas comerciais, não medição.

| Caso (41 kWp, Salvador, 4.889 kWh/mês, R$ 0,90) | Investimento (R$) | Geração (kWh/mês) | Economia ano 1 (R$) | Payback | VPL (R$) |
|---|---|---|---|---|---|
| SAD padrão | 99,384 | 5,085 | 47,513 | 2.09 | 463,660 |
| Geração reduzida ao nível NeoSolar | 99,384 | 3,196 | 33,360 | 2.93 | 281,161 |
| Custo NeoSolar (R$ 5.200/kWp), geração SAD | 213,200 | 5,085 | 47,513 | 4.33 | 334,768 |
| Custo NeoSolar + geração reduzida | 213,200 | 3,196 | 33,360 | 5.99 | 152,270 |

## 5. Conclusão

Comparação **exploratória** com estimativas comerciais, não validação empírica. (i) A geração do SAD é bem maior que a das propostas NeoSolar, sem explicação verificável; (ii) o custo-padrão do SAD é menos da metade do preço NeoSolar; (iii) com o investimento exato, o payback do SAD fica acima do informado pela NeoSolar (cerca de 6,3 contra 5,3 a 5,4 anos) porque a economia do SAD é líquida e limitada ao consumo faturável, de modo que a geração maior do SAD não se converte em economia adicional; com o custo-padrão do SAD o payback fica abaixo (cerca de 3,3 anos); (iv) payback e TIR dependem de custo e geração. Portanto os paybacks do caso-base não devem ser apresentados como confirmados por orçamentos externos; os cenários de custo NeoSolar e de baixa geração mostram o intervalo plausível.
