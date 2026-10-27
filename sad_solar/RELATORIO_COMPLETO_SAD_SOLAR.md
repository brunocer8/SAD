# Relatório técnico completo: SAD "Sol da Bahia" (versão corrigida, 2ª rodada de revisão)

> Finalidade: permitir que uma segunda IA (ou revisor) valide a lógica, os cálculos e a fundamentação teórica do projeto `sad_solar`.
> Este documento descreve o que o código FAZ (não o que deveria fazer). Valores numéricos vêm de execuções reais do código.
> Esta versão incorpora as correções da 2ª revisão (simultaneidade, validade de 60 meses dos créditos, prazo total do financiamento, VPL do projeto x capital próprio, payback pelo primeiro cruzamento, validação de entradas, fatores renomeados). Arquivos citados estão na pasta `sad_solar/`. Pede-se ao validador que aponte erros de lógica, de matemática, de teoria e de aderência ao enunciado.

---

## 0. Contexto acadêmico

Disciplina: Sistemas de Apoio à Decisão (UFBA). Trabalho individual: protótipo funcional executável de um SAD para uma decisão real ou plausível.

Enunciado resumido (seções exigidas no PDF final):
1. Introdução: tema, problema de decisão, objetivo, justificativa, decisores, fundamentação teórica; classificar a decisão (nível gerencial e grau de estruturação).
2. Dados e funções analíticas: fontes, variáveis, indicadores; usar, de forma justificada, **pelo menos três** entre sumarização, agrupamento, associação, regressão e classificação, indicando entrada, processamento e resultado decisório de cada uma.
3. Modelo de decisão: como dados e resultados analíticos viram apoio à decisão (critérios, regras, parâmetros, recomendação); deve evidenciar o que diferencia o sistema de um painel de indicadores ou consulta.
4. Protótipo: executa o fluxo principal (dados simulados/reduzidos aceitos; mockup estático não); entregar link e credenciais, repositório com README, diagrama de arquitetura/fluxo, vídeo de 3 a 5 min.
5. Demonstração, validação e resultados: caso concreto, validação adequada ao método, discussão e limitações.
6. Conclusão e referências.
Entrega: PDF único no Google Sala de Aula. Exigência do autor: variáveis e cálculos precisam de fundamentação teórica.

O enunciado NÃO exige SAW, ROC, gamificação nem a hierarquia de fatores (Teórica, Normativa/Legal, Cultural, Modelos preditivos). Essa hierarquia foi uma escolha do projeto, atribuída pelo autor a uma orientação da disciplina que o validador não consegue conferir.

---

## 1. Problema de decisão

Uma PME baiana (baixa tensão, grupo B) deve instalar um sistema fotovoltaico em telhado (microgeração, até 75 kWp)? Se sim: qual tamanho e qual forma de pagamento (à vista ou financiado)? Ou é melhor não instalar?

- Decisor: proprietário/gestor financeiro da PME.
- Classificação: nível **estratégico** (Anthony, 1965; investimento de 25 anos), **semiestruturada** (Simon, 1960; Gorry e Scott Morton, 1971): parte calculável por regras, parte dependente de preferência e risco.
- Entradas do usuário: município da Bahia (417), consumo mensal médio (kWh), preço do kWh na fatura COM tributos (R$), área de telhado opcional (m²), fração do consumo que ocorre de dia (40%, 60% ou 80% na interface).

---

## 2. Arquitetura e fluxo

```
Entradas -> regressão (geração/kWp por município e mês)
         -> dimensionar (kWp admissível: 75 kW CA ~ kWp x relação CC/CA e área/7 m² por kWp; escolhe o kWp de maior VPL do PROJETO)
         -> 6 alternativas: {recomendado, compacto, ampliado} x {à vista, financiado}  + "Não instalar"
         -> para cada alternativa: simular (balanço mensal com créditos FIFO de 60 meses, fluxo 25 anos do PROJETO e do
            CAPITAL PRÓPRIO: VPL, TIR, payback, LCOE)
                                   + Monte Carlo (1.000 cenários de incerteza) -> sumarização (percentis, probabilidades)
         -> FILTRO: VPL>0 e P(VPL>0)>=50%  (reprovadas ficam sem índice)
         -> SAW (pesos ROC) entre aprovadas + "Não instalar"
         -> sensibilidade dos pesos (±30%, 1.000 sorteios)
         -> AGRUPAMENTO hierárquico do índice SAW
         -> recomendação = alternativa de maior índice (pode ser "Não instalar")
```
Módulos: `financeiro.py` (energia, fluxo, indicadores, dimensionamento), `montecarlo.py` (incerteza, risco, classificador offline), `saw.py` (filtro, SAW, sensibilidade, agrupamento, recomendação), `parametros.py` (premissas), `app.py` (API FastAPI + SQLite + login), `static/index.html` (interface), `tests/` (17 testes), `scripts/` (validação da regressão, caso de demonstração).

Funções analíticas (item 2 do enunciado), todas executadas no fluxo:

| Função | Entrada | Processamento | Resultado decisório |
|---|---|---|---|
| Regressão | irradiação global (ghi), fração difusa, temperatura média, por município e mês | regressão linear múltipla (MQO) sobre geração simulada com pvlib | geração mensal por kWp, base de toda a economia e do VPL |
| Sumarização | fluxos de caixa e 1.000 cenários de Monte Carlo por alternativa | VPL, TIR, payback, LCOE; percentis 10/50/90; P(VPL>0); distribuição de faixas de retorno | filtro de viabilidade e critérios de risco do SAW |
| Agrupamento | índice SAW de cada alternativa | aglomerativo hierárquico, ligação completa, corte baseado no ruído dos pesos | distingue "mais recomendado" de "competitivas" |

O classificador (árvore e Random Forest) existe só como experimento offline e NÃO entra na recomendação.

---

## 3. Dados

`dados/dataset_ba_modelo.csv`: 5.004 linhas = 417 municípios x 12 meses. Colunas relevantes: `ghi` (irradiação global horizontal, kWh/m².dia), `fracao_difusa` (dif/ghi), `temp_media` (°C), `geracao_dia` (kWh/kWp.dia, alvo, simulado com pvlib, perdas de 14%), `geracao_especifica` (= geracao_dia x dias do mês), além de dif, dni, poa, par, ganho_inclinacao, inclinação (= |latitude|), temperatura de célula, pr. Fontes declaradas pelo autor: Atlas Solar/INPE e NASA POWER (versão e período NÃO documentados no repositório).

`dados/modelo_geracao_linear.json` (coeficientes):

```
geracao_dia (kWh/kWp.dia) = 3,824812 + 0,383322*ghi - 3,414855*fracao_difusa - 0,012222*temp_media
```
`financeiro.carregar_municipios()` aplica essa equação a cada município-mês: `geracao_mes = geracao_dia_prev * dias_do_mes`; o perfil mensal (12 valores, kWh/kWp) e o total anual `ger_esp_anual` (kWh/kWp.ano, soma dos 12) saem daí. A fração sazonal usada no balanço é `share_m = perfil_m / soma(perfil)`.

---

## 4. Parâmetros e premissas (`parametros.py`)

Cada parâmetro tem tipo: `fonte` (valor de fonte citada), `estimado` (derivado com conta própria) ou `premissa` (escolha do autor). `mc` = distribuição no Monte Carlo (tri = triangular mín/moda/máx; uni = uniforme).

| Parâmetro | Padrão | Monte Carlo | Tipo | Observação |
|---|---|---|---|---|
| tarifa_kwh | 0,87773 | fixo (usuário informa) | fonte | tarifa B3 Coelba SEM tributos (REH 3.578/2026); usuário informa preço COM tributos |
| reajuste_tarifa | 6,0% a.a. | tri(3,5%; 6,0%; 9,0%) | estimado | histórico Coelba e Focus |
| fio_b_share_tarifa | 28% da tarifa | tri(22%; 28%; 32%) | estimado | aplicado sobre a tarifa COM tributos; NÃO é valor oficial da Coelba |
| fio_b_2029_em_diante | 100% | uni(60%; 100%) | premissa | Lei 14.300 art. 27: 60% (2026), 75% (2027), 90% (2028); de 2029 vale o art. 17 e a regulamentação (não fixa 100%) |
| simultaneidade | 0,85 | uni(0,70; 1,00) | premissa | fração da geração mensal coincidente com a carga (sem curva horária) |
| relacao_dc_ac | 1,0 | fixo | premissa | limite legal é 75 kW em CA; teto de módulos = 75 x relação |
| custo_disponibilidade | 100 kWh/mês | fixo | premissa | mínimo trifásico |
| consumo_diurno_fracao | 0,60 | uni(0,40; 0,80) | premissa | entrada do usuário (0,4/0,6/0,8) fixa o valor no MC |
| fator_custo | 1,00 | tri(0,90; 1,00; 1,15) | estimado | multiplica a tabela de custo |
| om_pct_investimento | 1,0%/ano | tri(0,5%; 1,0%; 1,5%) | premissa | O&M anual, corrigido pelo IPCA |
| degradacao_anual | 0,5% | tri(0,4%; 0,5%; 0,8%) | fonte | |
| vida_util_anos | 25 | fixo | fonte | |
| inversor_ano_troca | 12 | uniforme inteiro 12 a 20 | estimado | |
| inversor_custo_pct | 6% do invest. | uni(5%; 8%) | estimado | corrigido pelo IPCA |
| fator_desempenho_real | 0,95 | tri(0,80; 0,95; 1,00) | premissa | sobre a geração simulada |
| ipca | 4,3% | tri(3,5%; 4,3%; 5,2%) | fonte | Focus 9/10/2026 |
| taxa_desconto | 12% a.a. NOMINAL | uni(10%; 14%) | estimado | |
| taxa_financiamento | 7,9% a.a. | uni(7,9%; 13,25%) | estimado | BNB FNE Sol (piso) a Selic |
| prazo_financiamento | 12 anos (TOTAL, carência incluída) | fixo | fonte | teto do FNE Sol; 144 meses = 6 de carência + 138 parcelas |
| carencia_meses | 6 | fixo | fonte | juros capitalizados |
| entrada_pct | 10% | fixo | fonte/premissa | |
| m2_por_kwp | 7,0 | fixo | premissa | |
| kwp_max | 75 | fixo | fonte | Lei 14.300 (75 kW CA) |
| ano_inicio | 2027 | fixo | premissa | define o % de Fio B |

Custo do sistema instalado (R$/kWp, "Greener SED 1S/2026"; não verificado pelo autor da revisão): 8 kWp: 2.430; 12: 2.220; 30: 2.020; 50: 2.020; 75: 2.350; interpolação linear (`np.interp`), constante fora da faixa. `investimento = kWp x custo_kWp(kWp) x fator_custo`.

---

## 5. Cálculo da energia (balanço MENSAL, `financeiro.simular`)

Para cada cenário, ano t = 1..25 e mês m = 1..12, com lotes de crédito por mês de origem (60 lotes; o mais antigo é o índice 0):

```
g0      = kWp * ger_esp_anual * fator_desempenho_real           (kWh no ano 1)
G_m,t   = g0 * share_m * (1 - degradacao)^(t-1)                 geração do mês
carga_d = consumo_diurno_fracao * consumo_mes                   (kWh/mês consumíveis na hora do sol)
S_m     = min(simultaneidade * G_m, carga_d)                    autoconsumo instantâneo (sem passar pela rede, sem Fio B)
I_m     = G_m - S_m                                             excedente injetado -> novo lote de crédito
N_m     = max(consumo_mes - S_m - custo_disponibilidade, 0)     consumo da rede abatível por créditos
expira  : o lote de 60 meses atrás é descartado (soma em "expirado")
U_m     : N_m é abatido dos lotes do mais antigo para o mais novo (FIFO); U_m = total usado
```
Anuais: `S = soma S_m`, `comp = soma U_m`, `G = S + soma I_m`. `cobertura_consumo (ano 1) = (S + comp) / (12*consumo_mes)`.

Simplificações: sem curva de carga horária (a simultaneidade é uma premissa, não medida); consumo constante mês a mês e ano a ano; fração diurna única; créditos que sobram ao fim da vida útil não valem nada; sem Tarifa Branca, sem grupo A.

## 6. Economia e fluxos de caixa

```
tarifa_t   = tarifa_kwh * (1 + reajuste_tarifa)^(t-1)
ano        = ano_inicio + t - 1
pctFioB    = 0,60 (<=2026) | 0,75 (2027) | 0,90 (2028) | fio_b_2029_em_diante (>=2029)
custoFioB  = tarifa_t * fio_b_share_tarifa * pctFioB * comp          (só sobre energia compensada)
economia_t = tarifa_t * (S + comp) - custoFioB
invest     = kWp * custo_kWp(kWp) * fator_custo
O&M_t      = om_pct * invest * (1 + ipca)^(t-1)
troca_t    = inversor_custo_pct * invest * (1 + ipca)^(t-1)   somente em t = inversor_ano_troca
```
**Fluxo do PROJETO** (sem financiamento): `CF0 = -invest`; `CFt = economia_t - O&M_t - troca_t`. Dele: `vpl_projeto`, `payback_projeto`.

**Financiamento** (Price com carência, juros capitalizados): `F = invest*(1-entrada_pct)`; `im = (1+i)^(1/12)-1`; `Fc = F*(1+im)^carencia`; prazo TOTAL 144 meses → `n = 144 - 6 = 138` parcelas; `PMT = Fc*im / (1-(1+im)^-n)`; parcelas no ano t = clip(min(carencia+n, 12t) - max(carencia, 12(t-1)), 0, 12); `parcelas_t = PMT * esse número`.

**Fluxo do CAPITAL PRÓPRIO**: `CF0 = -(invest - F)` (à vista: `-invest`); `CFt = economia_t - O&M_t - troca_t - parcelas_t`. Dele: `vpl` (capital próprio), `payback` (recuperação do capital próprio), TIR. Para o à vista, os dois fluxos coincidem. Fluxos NOMINAIS, desconto NOMINAL, fim de ano.
`valor da alavancagem = vpl (capital próprio) - vpl_projeto` (positivo quando a dívida custa menos que a taxa de desconto).

## 7. Indicadores
- VPL = soma_{t=0..25} CFt / (1+d)^t (projeto e capital próprio).
- Payback = anos até o PRIMEIRO instante em que o fluxo acumulado fica >= 0, interpolado linearmente no ano do cruzamento; 0 se já começa não negativo; NaN se nunca recupera. (Antes usava o último instante negativo.) Payback descontado: idem sobre fluxos descontados.
- TIR: bisseção vetorizada em [-90%; 1000%], 80 iterações; NaN se não há raiz nesse intervalo; não trata múltiplas raízes.
- LCOE = (invest + VP(O&M + troca)) / VP(geração anual).
- `exposicao_regulatoria` = (tarifa_t*comp - custoFioB) / economia, no ano 1.
- Também: `credito_expirado_ano1`, `credito_expirado_total`, `parcelas_ano1`.

## 8. Dimensionamento
Teto = min(75 x relacao_dc_ac, floor(área/7)); a área deve ser positiva (0 ou negativa: erro); se teto < 3 kWp levanta `AreaInsuficiente` (a API responde 422). O dimensionamento ignora o flag de financiamento (força `financiado = 0`) e escolhe, entre 3 e o teto (passo 1 kWp), o kWp de maior VPL do PROJETO no cenário-base (`kwp_recomendado`). Alternativas: recomendado; compacto = max(3, round(0,5*rec)); ampliado = min(teto, round(1,3*rec)); duplicados removidos.

## 9. Monte Carlo (sumarização de risco, `montecarlo.analisar_risco`)
Para cada alternativa: n = 1000 cenários (semente fixa 7; mesmos sorteios para todas), sorteando os parâmetros com a distribuição `mc` da seção 4; o que o usuário informou (tarifa, fração diurna) fica fixo; município, consumo e kWp fixos. Roda `simular` à vista e financiado. Saídas: P(VPL>0) à vista e financiada (capital próprio); percentis 10/50/90 de VPL (à vista, financiado, projeto), de payback do projeto, do capital próprio e descontado; mediana de TIR; P(financiado > à vista); probabilidade das faixas de retorno (rotuladas por payback: rápido <= 1,5 ano, médio <= 2, lento > 2, inviável se VPL <= 0).

## 10. Modelo de decisão (`saw.py`)

**10.1 Filtro de viabilidade** (premissas do autor): reprovada se `VPL (capital próprio da alternativa) <= 0` ou `P(VPL>0) < 50%`. Reprovadas não recebem índice nem podem ser recomendadas. Entre as aprovadas, o veredito é "Recomendado com ressalvas" se: cobertura < 90%, P(VPL>0) < 90%, mediana do payback do PROJETO > 5 anos, ou (financiado) fluxo do capital próprio negativo no 1º ano; senão "Recomendado". O payback do capital próprio do financiado não entra no veredito.

**10.2 Critérios do SAW** (8, pesos exatos somando 1):

| Fator (ordem assumida) | Critério | Sentido | Peso |
|---|---|---|---|
| 1) Retorno econômico (52,08%) | VPL do projeto (25 anos) | max | 17,36% |
| | Payback do projeto (indefinido = 25 anos = pior valor) | min | 17,36% |
| | Valor da alavancagem por R$ financiado = (VPL cap. próprio - VPL projeto) / valor financiado (0 à vista) | max | 17,36% |
| 2) Exposição regulatória (27,08%) | Exposição regulatória (fração da economia vinda de compensação) | min | 27,08% |
| 3) Preferências do decisor (14,58%) | Cobertura do consumo | max | 7,29% |
| | Sem endividamento (1 à vista, 0 financiado) | max | 7,29% |
| 4) Risco econômico (6,25%) | Probabilidade de prejuízo = 1 - P(VPL>0) (fluxo da própria alternativa) | min | 3,125% |
| | VPL no percentil 10 (fluxo da própria alternativa) | max | 3,125% |

Pesos dos fatores: ROC (Barron e Barrett, 1996), n = 4: w_i = (1/n) * soma_{j=i..n} 1/j. A ORDEM dos fatores é preferência assumida pelo autor (a validar com o decisor), não descoberta pelo método. O custo do Fio B em R$ e a "folga até 75 kWp" não são critérios (dupla contagem; restrição). A alavancagem é por R$ financiado para não premiar sistemas maiores só por terem mais dívida barata.

**10.3 SAW**: `r_ij = (x-min)/(max-min)` (ganho) ou `(max-x)/(max-min)` (custo); max = min → r = 1; NaN vira o pior valor; `S_i = soma_j w_j r_ij`. "Não instalar": VPL projeto 0, payback 25, alavancagem 0, exposição 0, cobertura 0, sem dívida 1, prob. de prejuízo 0, VPL p10 0. O índice é RELATIVO ao conjunto aprovadas + "Não instalar" (reversão de ranking possível; não é nota absoluta). Se "Não instalar" for a única alternativa, o índice não é exibido.

**10.4 Sensibilidade**: 1.000 vezes, cada peso x U(0,7; 1,3), renormalizado. Saídas: desvio-padrão do índice, frequência de liderança e frequência com que o líder supera cada alternativa.

**10.5 Agrupamento**: aglomerativo hierárquico, ligação completa, 1-D sobre o índice; funde grupos vizinhos de menor diâmetro enquanto <= δ; `δ = √2 x média dos desvios-padrão` da sensibilidade. δ é uma HEURÍSTICA do projeto (a frequência com que o líder supera cada alternativa acompanha o agrupamento como evidência complementar).

**10.6 Recomendação**: posição 1; pode ser "Não instalar".

## 11. Resultados (caso concreto, executado)

Entradas: Salvador; 4.000 kWh/mês; R$ 1,10/kWh; 60% diurno; telhado 300 m² (teto 42 kWp; maior VPL do projeto em 34 kWp). Geração específica ~1.488 kWh/kWp.ano.

| Pos. | Grupo | Alternativa | Índice | VPL projeto (R$) | VPL cap. próprio (R$) | Payback projeto | P(VPL>0) | Lidera (pesos) | Líder supera |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Compacto 17 kWp, financiado | 0,702 | 276.058 | 283.300 | 1,37 | 100% | 92% | - |
| 2 | 2 | Recomendado 34 kWp, financiado | 0,656 | 496.244 | 509.761 | 1,45 | 100% | 8% | 92% |
| 3 | 2 | Ampliado 42 kWp, financiado | 0,647 | 477.944 | 494.641 | 1,79 | 100% | 0% | 97% |
| 4 | 3 | Compacto 17 kWp, à vista | 0,601 | 276.058 | 276.058 | 1,37 | 100% | 0% | 100% |
| 5 | 4 | Recomendado 34 kWp, à vista | 0,554 | 496.244 | 496.244 | 1,45 | 100% | 0% | 100% |
| 6 | 4 | Ampliado 42 kWp, à vista | 0,545 | 477.944 | 477.944 | 1,79 | 100% | 0% | 100% |
| 7 | 5 | Não instalar | 0,375 | 0 | 0 | 25 | - | 0% | 100% |

δ = 0,044. **Recomendação: compacto 17 kWp, financiado** (com ressalvas: cobre ~53% do consumo). Por quê: (i) 17 kWp têm a menor exposição regulatória (a maior parte da geração é autoconsumida; com simultaneidade 0,85 há alguma injeção), critério que pesa 27,08%; (ii) o financiamento a 7,9% a.a., descontado a 12%, tem valor de alavancagem positivo (0,219 por R$ financiado), que supera o peso de 7,29% da aversão a dívida. Perde em VPL do projeto (276 mil contra 496 mil do 34 kWp) e em cobertura. O líder só supera o 34 kWp financiado em 92% dos sorteios de pesos; ou seja, a decisão depende da ordem de preferência assumida. Resultados do 34 kWp à vista: investimento R$ 68.680; economia ano 1 R$ 47.322; Fio B ano 1 R$ 4.158; cobertura 97,5%; payback 1,45; VPL R$ 496.244; TIR 72,9%; LCOE R$ 0,203/kWh. No financiado de 34 kWp, parcelas do ano 1 = R$ 4.201 e payback do capital próprio ~0,16 ano (não usado na decisão).

Outros cenários: consumo 15.000 kWh/mês → 75 kWp financiado; tarifa R$ 0,70 → compacto 16 kWp financiado; consumo 300 kWh, tarifa R$ 0,30, 10% diurno → nenhuma instalação passa no filtro, recomendação "Não instalar"; área 15 m² → erro "área insuficiente"; área 0 → erro de validação.

Testes de estresse (34 kWp à vista, um parâmetro por vez, VPL R$): base 496.244; custo +50%: 457.355 (payback 2,17); tarifa -30%: 324.038 (2,07); desempenho 80%: 435.567; simultaneidade 60%: 491.623; Fio B 60% após 2028: 520.019; desconto 20%: 241.258; diurno 20%: 424.386; combinado (custo +50%, tarifa -30%, desempenho 80%): 242.675 (payback 3,31). VPL > 0 em todos. Esses testes variam o próprio modelo e não substituem planilha independente nem orçamentos reais.

Regressão (validação cruzada em 5 grupos de municípios não vistos no ajuste): R² médio 0,956; MAE 0,081 kWh/kWp.dia; RMSE 0,096; erro percentual médio 1,95%; coeficientes refeitos idênticos aos do arquivo. Viés sazonal ~±3% (≈ -0,12 em dezembro, +0,12 em março).

Classificador offline (retreinado após as correções; 20.000 cenários sintéticos, teste 25%): árvore prof. 4: acurácia 73,56%, F1 macro 73,13%; Random Forest: 87,18% / 87,08%. Classes por cortes de payback do autor; não participa da decisão.

## 12. Testes automáticos (26, todos passando)
Balanço mensal e expiração de créditos de 60 meses conferidos por implementação independente em laços (FIFO); conservação de energia; créditos >= 0; simultaneidade menor reduz autoconsumo; VPL recalculado manualmente; cronograma do financiamento (138 parcelas, saldo zera, parcelas do ano 1, ausência de parcelas após o mês 144, conciliação com a diferença de fluxos); VPL do projeto igual à vista e financiado; payback pelo primeiro cruzamento (inclui fluxo que volta a ficar negativo e fluxo sem recuperação); área insuficiente, zero e negativa; dimensionamento independente do flag de financiamento; limite de 75 kWp; pesos ROC; normalização; agrupamento; "Não instalar" pode vencer; reprovada nunca recomendada; veredito usa payback do projeto; alavancagem não premia sistema maior; índice não exibido se única alternativa; API ponta a ponta (instalar, não instalar, 422 por área, 422 por área zero).

## 13. Limitações e pontos fracos conhecidos (peço atenção do validador)
1. Alvo da regressão é simulação pvlib, não geração medida; viés sazonal.
2. Autoconsumo por fator de simultaneidade (premissa 0,85), sem curva de carga horária; a recomendação ainda favorece sistemas pequenos porque o critério de exposição regulatória pesa 27%.
3. Limite legal de 75 kW em CA aproximado em kWp x relação CC/CA (1,0); inversor não modelado.
4. Fio B: 28% da tarifa com tributos é estimativa; regra pós-2028 é cenário (60% a 100%); componente oficial da Coelba não usada.
5. Retornos muito altos (payback ~1,5 ano; TIR 73%; P(VPL>0)=100% no MC): custos por kWp não verificados nas fontes originais; material de 2023/2024 atribuído à Greener indicava payback ~2,4 anos e ~R$ 2,45/Wp para 50 kWp (a tabela do projeto usa R$ 2,02/Wp). Falta orçamento real e planilha independente.
6. Financiamento: taxa 7,9% é piso de referência; carência de 6 meses é premissa; a vantagem do financiado vem da diferença taxa de juros x taxa de desconto (12%) e do peso baixo da aversão a dívida.
7. SAW: min-max amplia diferenças pequenas; ordem e mapeamento dos fatores são preferências assumidas; critérios financeiros correlacionados; índice relativo ao conjunto.
8. Agrupamento com corte heurístico (δ).
9. TIR por bisseção sem tratamento de múltiplas raízes.
10. Classificador treinado em dados sintéticos e fora da decisão.
11. Pendências de entrega: usuário de demonstração, vídeo de 3 a 5 min, PDF único com diagrama renderizado; referências sem edição/página (Brealey et al.; Turban et al.; Greener); versão e período dos dados INPE/NASA.

## 14. Referências usadas
ANEEL REN 1.000/2021 e REH 3.578/2026; Anthony (1965); Barron e Barrett (1996), *Management Science* 42(11):1515-1523; Lei 14.300/2022; Brealey, Myers e Allen, *Principles of Corporate Finance*; Dobos (2014), PVWatts v5, NREL/TP-6A20-62641; Gorry e Scott Morton (1971), *Sloan Management Review* 13(1):55-70; Han, Kamber e Pei, *Data Mining: Concepts and Techniques*; Hertz (1964), *HBR* 42(1):95-106; Holmgren et al. (2018), pvlib python, *JOSS* 3(29):884; Hwang e Yoon (1981), *Multiple Attribute Decision Making*; Simon (1960); Turban, Sharda e Delen, *Decision Support and Business Intelligence Systems*; Greener (estudo 1S/2026); Atlas Solar/INPE; NASA POWER.

## 15. Perguntas para o validador
1. O balanço mensal com simultaneidade e créditos FIFO de 60 meses (seção 5) e os fluxos de projeto e capital próprio (seção 6) estão corretos e coerentes com a Lei 14.300?
2. VPL nominal com desconto nominal está consistente? A separação VPL do projeto x capital próprio e o critério de alavancagem por R$ financiado são defensáveis?
3. Filtro, SAW, ROC, sensibilidade e agrupamento formam um modelo de decisão defensável, que se distingue de um painel de indicadores? Que falhas teóricas existem (normalização, dupla contagem, reversão de ranking, escolha de δ)?
4. As três funções analíticas (regressão, sumarização, agrupamento) são suficientemente caracterizadas para o enunciado?
5. O resultado "compacto 17 kWp" é coerente com a lógica de decisão ou revela distorção dos critérios/pesos?
6. Os retornos altos indicam erro de premissa ou de cálculo? Que checagens independentes recomenda?
7. O que falta para atender cada item do enunciado e para a defesa perante o professor?
