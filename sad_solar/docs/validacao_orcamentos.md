# Comparação exploratória do SAD com estimativas comerciais (Salvador)

**Natureza:** as referências são estimativas comerciais de um fornecedor (NeoSolar) e duas calculadoras (Portal Solar, WEG), não medições de geração de sistemas instalados. Os quatro orçamentos NeoSolar de 10/20/30/40 kWp são do mesmo fornecedor e compartilham premissas; não são fontes independentes. Os cinco registros foram conferidos nos PDFs de orçamento fornecidos pelo autor (`conferido_no_pdf_anexado = sim`). As propostas têm potência CC de 10,8 a 54 kWp. A regressão do SAD foi treinada com geração simulada (pvlib) e a comparação não a valida empiricamente.

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

**Discrepância NÃO resolvida:** as propostas NeoSolar estimam entre 73 e 90 kWh/kWp.mês, o SAD estima 124, e a Portal Solar ~131. O desvio médio do SAD frente às cinco propostas é +46.07 kWh/kWp.mês (+60.0%, média simples dos desvios relativos). A NeoSolar declara base NREL/NASA, inclinação ideal, orientação norte e sem sombreamento; não declara perdas, local exato nem PR. Não foi possível explicar a diferença com as informações disponíveis. Os coeficientes da regressão NÃO foram ajustados para coincidir com os orçamentos.

## 2. Custo instalado por kWp CC

| Referência | Investimento cotado (R$) | Cotado (R$/kWp CC) | SAD padrão (R$/kWp CC) | Diferença % |
|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 270,812.25 | 5,015.04 | 2,072.80 | -58.7% |
| NeoSolar 10 kWp | 57,675.69 | 5,340.34 | 2,280.00 | -57.3% |
| NeoSolar 20 kWp | 122,743.82 | 5,245.46 | 2,093.33 | -60.1% |
| NeoSolar 30 kWp | 185,421.00 | 5,150.58 | 2,020.00 | -60.8% |
| NeoSolar 40 kWp | 245,707.22 | 5,055.70 | 2,020.00 | -60.0% |

O SAD interpola a tabela histórica de custos e aplica o fator de custo padrão 1.00. Os valores estimados variam de R$ 2,020.00 a R$ 2,280.00/kWp, frente a R$ 5,015.04 a R$ 5,340.34/kWp cotados. O desvio médio (SAD menos cotado) é de -3,064.20 R$/kWp e o erro absoluto médio é de 3,064.20 R$/kWp. A média dos desvios percentuais é -59.4% (faixa de -60.8% a -57.3%).

As medidas descrevem as cinco propostas. O SAD aceita um orçamento informado no campo `custo_kwp`, que substitui o custo-padrão.

## 3. Payback e TIR: duas análises separadas

A economia da proposta NeoSolar é bruta (geração x R$ 0,90, conta residual de R$ 45; o PDF avisa que não inclui iluminação pública nem custo de disponibilidade). A do SAD é líquida (mínimo faturável, Fio B, O&M, troca de inversor). Todas as propostas NeoSolar declaram tarifa R$ 0,90, inflação de energia de 8% a.a. e perda de 0,7%/ano, replicadas aqui (inflação e perda) na tabela 3a e 3b; o consumo é o informado na proposta (campo sem solar).

### 3a. Com o investimento exato de cada proposta

| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |
|---|---|---|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 4,889 | 270,812 | 6,697 | 4.5 | 5.34 | 33.1% | 23.0% |
| NeoSolar 10 kWp | 900 | 57,676 | 1,339 | 5.3 | 6.20 | 27.5% | 20.0% |
| NeoSolar 20 kWp | 1,800 | 122,744 | 2,902 | 5.4 | 6.34 | 26.7% | 19.6% |
| NeoSolar 30 kWp | 2,700 | 185,421 | 4,465 | 5.4 | 6.32 | 26.7% | 19.7% |
| NeoSolar 40 kWp | 3,600 | 245,707 | 6,028 | 5.4 | 6.26 | 27.0% | 19.9% |

### 3b. Com o custo-padrão do SAD

| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |
|---|---|---|---|---|---|---|---|
| NeoSolar 54 kWp (proposta anterior) | 4,889 | 111,931 | 6,697 | 4.5 | 2.37 | 33.1% | 47.4% |
| NeoSolar 10 kWp | 900 | 24,624 | 1,339 | 5.3 | 2.88 | 27.5% | 39.8% |
| NeoSolar 20 kWp | 1,800 | 48,984 | 2,902 | 5.4 | 2.78 | 26.7% | 41.2% |
| NeoSolar 30 kWp | 2,700 | 72,720 | 4,465 | 5.4 | 2.72 | 26.7% | 42.0% |
| NeoSolar 40 kWp | 3,600 | 98,172 | 6,028 | 5.4 | 2.74 | 27.0% | 41.7% |

Calculadoras (consumo 4.889 kWh/mês, R$ 0,90, investimento da referência): 

| Referência | Payback ref. (anos) | Payback SAD |
|---|---|---|
| Portal Solar (menor valor) | 2.75 | 1.95 |
| Portal Solar (maior valor) | 2.75 | 2.35 |
| WEG (kWp assumido 40) | 3.8 | 2.10 |

## 4. Sensibilidade de baixa geração (NÃO é previsão)

Cenário separado da regressão: o fator de desempenho é multiplicado por 0.63 (média da geração específica das propostas NeoSolar dividida pela do SAD), apenas para mostrar o efeito caso a geração real fique no nível dessas propostas. Origem: comparação com estimativas comerciais, não medição.

| Caso (41 kWp, Salvador, 4.889 kWh/mês, R$ 0,90) | Investimento (R$) | Geração (kWh/mês) | Economia ano 1 (R$) | Payback | VPL (R$) |
|---|---|---|---|---|---|
| SAD padrão | 82,820 | 5,085 | 45,323 | 1.84 | 431,589 |
| Geração reduzida ao nível NeoSolar | 82,820 | 3,196 | 29,806 | 2.80 | 238,232 |
| Custo NeoSolar (R$ 5.200/kWp), geração SAD | 213,200 | 5,085 | 45,323 | 4.60 | 283,939 |
| Custo NeoSolar + geração reduzida | 213,200 | 3,196 | 29,806 | 6.90 | 90,582 |

## 5. Conclusão

Com os investimentos informados nas propostas, o payback estimado pelo SAD variou entre 5.34 e 6.34 anos, frente ao intervalo cotado de 4.5 a 5.4 anos. O desvio médio ficou em +0.89 ano. Com o custo-padrão, o payback estimado ficou entre 2.37 e 2.88 anos. A comparação iguala o investimento no primeiro teste. As estimativas de geração e as regras para calcular a economia ainda diferem.

Os resultados mostram sensibilidade às premissas de custo e geração nos cenários comparados. As propostas são estimativas de um único fornecedor para sistemas maiores que o caso residencial de 1,86 kWp. A comparação é exploratória e não sustenta estimativa de preço típico, confirmação do retorno residencial ou validação da geração em campo.
