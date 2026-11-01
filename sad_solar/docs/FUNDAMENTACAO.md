# Fundamentação e modelo de decisão — Sol da Bahia (residencial)

## 1. Introdução

**Tema:** sistema de apoio à decisão para avaliar a instalação de um sistema fotovoltaico conectado à rede (*on-grid*) em residências atendidas na Bahia. **Decisão:** instalar um conjunto de módulos, escolher um tamanho entre as alternativas tecnicamente viáveis ou não investir agora? **Objetivo:** combinar dados solares, características informadas pelo usuário, simulação financeira e preferências para apresentar uma decisão explicada e passível de questionamento.

**Decisor:** morador/proprietário da residência, sem exigir conhecimento de engenharia ou planilhas financeiras. **Nível:** estratégico no âmbito doméstico por comprometer recursos financeiros com horizonte longo. **Estruturação:** semiestruturada; há fórmulas de geração e fluxo de caixa, mas preferências, preços futuros e limitações técnicas dependem de premissas, informações incompletas e julgamento humano (Simon; Gorry e Scott Morton).

## 2. Entradas, variáveis e justificativa

| Variável | Tipo/papel | Justificativa |
|---|---|---|
| Município / clima (GHI, fração difusa, temperatura) | Independentes da regressão | Estimam a energia fotovoltaica gerada em cada mês; base disponível para 417 municípios |
| Consumo residencial médio (kWh/mês) | Independente da decisão | Demanda energética que pode ser atendida / compensada |
| Tarifa marginal (R$/kWh) | Independente da decisão | Valor econômico do consumo evitável; valor homologado B1 como referência, sem tributos |
| Área útil do telhado (m²) | Restrição técnica informada | Impede dimensionar instalação acima do espaço declarado; modelo usa 7 m²/kWp como hipótese |
| Tipo de ligação e modalidade tarifária | Independentes/regras | Definem mínimo faturável (30/50/100 kWh/mês) e ressalvas para Tarifa Social |
| Fator de simultaneidade e consumo diurno | Premissas distintas | Simultaneidade: parcela da geração consumida imediatamente; perfil diurno: parcela da carga disponível durante o sol |
| Custo de implantação (R$/kWp) | Independente da decisão | Afeta investimento, VPL e retorno; usuário pode substituir tabela ilustrativa por orçamento |
| Geração específica diária (kWh/kWp/dia) | **Dependente da regressão** | Alvo de modelo linear treinado em geração **simulada por pvlib** |
| Recomendação (instalar/não instalar/tamanho) | **Saída do SAD** | Determinada por filtros, indicadores econômicos, risco e ranking SAW, não por classe real rotulada |

## 3. Funções analíticas exigidas (entrada → processamento → uso decisório)

**Função 1 — Regressão.** Entrada: GHI, fração difusa e temperatura média municipal por mês (`dados/dataset_ba_modelo.csv`). Processamento: regressão linear múltipla com intercepto, cujos coeficientes estão em `dados/modelo_geracao_linear.json`. Resultado: kWh/kWp.dia por município/mês; integra o balanço de geração e o fluxo de caixa. **Validação:** `scripts/validar_regressao.py` separa municípios inteiros entre treino e teste (cinco grupos). A validação é contra geração **simulada**, não medições de campo.

**Função 2 — Sumarização.** Entrada: geração, investimento, consumo, tarifas, custos de manutenção e cenários aleatórios. Processamento: indicadores (geração anual/mensal, cobertura do consumo, economia, VPL, TIR, payback) e distribuição de VPL em simulações de Monte Carlo com percentis P10/P50/P90 e proporção de VPL positivo. Resultado: evidencia viabilidade e risco de cada alternativa, alimenta filtro e critérios do SAW.

**Função 3 — Agrupamento.** Entrada: notas SAW das alternativas aprovadas, incluindo a referência *não instalar*. Processamento: agrupamento hierárquico aglomerativo por ligação completa sobre distância de notas; o limiar é calibrado pela análise de sensibilidade dos pesos (variação ilustrativa de ±30%). Resultado: mostra alternativas com desempenho multicritério muito parecido, evitando tratar pequena diferença numérica como certeza. **Ressalva:** é agrupamento de alternativas, não identificação de perfis reais de consumidores.

## 4. Regras técnicas e financeiras

- Telhado informado: potência máxima aproximada = `area_util_m2 / 7`; as opções usam inteiros de **620 Wp por módulo**. Dois módulos são um mínimo **didático** de 1,24 kWp; depende da compatibilidade real de inversor e módulos. Se o espaço não comporta o mínimo, o SAD devolve erro técnico claro, em vez de inventar área.
- Geração: regressão municipal sazonal × kWp × fator de desempenho × degradação anual.
- Balanço **mensal**: consumo simultâneo é limitado tanto pela produção quanto pela carga diurna; o excedente gera créditos com validade de 60 meses; o uso de créditos respeita a energia da rede que pode ser compensada, acima da disponibilidade. Os dados não permitem modelagem horária completa.
- Cobrança mínima: 30 kWh/mês para monofásica, 50 para bifásica e 100 para trifásica no grupo B (simplificação operacional). Para Tarifa Social, aplica-se limite conservador adicional de 80 kWh/mês sem economia evitável. **Não substitui** cálculo real da fatura nem todas as condições legais de subsídio.
- Fluxo do projeto: `CF0 = -investimento`; `CFt = economia anual - operação/manutenção - substituição do inversor`. VPL compara esse fluxo com uma taxa de desconto; payback calcula o retorno do capital. Financiamento é opcional e só é simulado se o decisor informa uma taxa anual (CET).
- Fio B: cronograma de 60% em 2026, 75% em 2027 e 90% em 2028 sobre a parcela relevante; **100% após 2028 é cenário conservador do programa**, não uma regra definitiva da lei. A participação do Fio B no preço total é estimada e não reproduz fatura completa da Coelba.

## 5. Modelo decisório: por que é um SAD, não um dashboard?

1. **Geração de alternativas:** compara opções discretas (compacta, preferida pelo VPL e ampliada), respeitando limites do telhado, além de *não instalar*.
2. **Filtro de viabilidade:** alternativas de instalação com VPL não positivo ou probabilidade de VPL positivo abaixo de 50% são reprovadas. Financiamento desfavorável em relação à mesma instalação à vista recebe ressalva ou rejeição.
3. **Avaliação multicritério SAW:** normaliza critérios econômicos, exposição à compensação/Fio B, cobertura, endividamento e risco. Pesos são definidos de forma explícita e podem mudar conforme a prioridade selecionada (padrão, retorno, cautela).
4. **Agrupamento e sensibilidade:** quantifica a estabilidade do ranking sob pequenas variações dos pesos e identifica empates técnicos de classificação.
5. **Recomendação final:** indica uma alternativa com motivo, ressalvas e indicadores; *não instalar* participa do ranking e pode vencer. A interface permite explorar alternativas diferentes da primeira colocada.

## 6. Validação e limites

Aplicar cenários de consumo baixo/médio/alto e sensibilidade a tarifa, custo e área; confirmar que áreas pequenas impedem configurações maiores e que opções reprovadas não vencem o ranking. Executar `python -m pytest -q` e `python scripts/validar_regressao.py`. Recalcular indicadores com fórmulas independentes para um caso pequeno e comparar somente sob premissas iguais. Ver `docs/CASO_E_VALIDACAO.md`.

A validade externa é limitada por dados simulados e hipóteses de consumo e preço. Uma conta de energia real pode fornecer entrada observada, **mas não valida a economia futura de um sistema que ainda não existe**. Não incluir contas com dados pessoais no repositório. Ausência de projeto executivo, garantia de inversor, estudo estrutural, vistoria, curvas horárias, detalhes tributários e orçamento são limitações declaradas.

## Referências principais

- COSTA, F. F. A. et al. *Avaliação do payback em sistemas fotovoltaicos on-grid para consumidores residenciais grupo B1 sob a Lei 14300/2022*. Revista Brasileira de Energia Solar, v. 16, n. 2, p. 147–157, dez. 2025.
- ANEEL. *Resolução Homologatória nº 3.578*, de abril de 2026, tarifas Neoenergia Coelba Grupo B, vigentes até abril de 2027.
- BRASIL. *Lei nº 14.300*, de 6 de janeiro de 2022.
- HOLMGREN, W. F.; HANSEN, C. W.; MIKOFSKI, M. A. *pvlib python: a python package for modeling solar energy systems*. Journal of Open Source Software, v. 3, n. 29, 884, 2018.
- GORRY, G. A.; SCOTT MORTON, M. S. *A framework for management information systems*. Sloan Management Review, 13(1), 55–70, 1971.
- SIMON, H. A. *The New Science of Management Decision*. Harper & Row, 1960.
- HERTZ, D. B. *Risk analysis in capital investment*. Harvard Business Review, 42(1), 95–106, 1964.
- HWANG, C.-L.; YOON, K. *Multiple Attribute Decision Making*. Springer, 1981.

As fontes específicas de cada coeficiente/hipótese estão nos arquivos `parametros.py`, `parametros_premissas.csv` e `docs/DICIONARIO_DADOS.md`.
