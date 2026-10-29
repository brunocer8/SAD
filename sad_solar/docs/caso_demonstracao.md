# Caso de demonstração: PME comercial em Salvador

Entradas: Salvador-BA; 4.889 kWh/mês (conta de R$ 4.400); R$ 0,90/kWh (com tributos); 60% do consumo durante o dia; telhado de 300 m² (**premissa explícita do caso demonstrativo, não dado da proposta NeoSolar**; o campo é a área UTILIZÁVEL). Consumo e tarifa vêm da proposta NeoSolar de 54 kWp, usada só como referência externa.

Limite técnico: 42 kWp (min. entre 75 kWp e área/7 m² por kWp). Tamanho que maximiza o VPL no cenário-base: 41 kWp.

## Ranking (filtro de viabilidade -> SAW -> agrupamento)

| Pos. | Grupo | Alternativa | Índice SAW | VPL projeto (R$) | VPL capital próprio (R$) | Payback projeto (anos) | Prob. VPL>0 | Lidera (pesos) | Líder supera | Veredito |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Sistema recomendado de 41 kWp, à vista | 0.727 | 463,660 | 463,660 | 2.09 | 100% | 78% | - | Recomendado |
| 2 | 1 | Sistema ampliado de 42 kWp, à vista | 0.726 | 460,915 | 460,915 | 2.14 | 100% | 0% | 100% | Recomendado |
| 3 | 1 | Sistema compacto de 20 kWp, à vista | 0.694 | 247,912 | 247,912 | 1.96 | 100% | 22% | 78% | Recomendado com ressalvas |
| 4 | 2 | Não instalar (manter a conta atual) | 0.302 | 0 | 0 | 25.00 | - | 0% | 100% | - |

**Recomendação do SAD:** Sistema recomendado de 41 kWp, à vista (Maior índice SAW entre 3 alternativa(s) aprovada(s) no filtro e a opção de não instalar.) Corte do agrupamento: 0.046.

## A recomendação muda com as preferências do decisor

| Prioridade (ordem dos fatores) | Recomendação | Índice | Lidera nos sorteios de pesos |
|---|---|---|---|
| Padrão: retorno > regulatório > preferências > risco | Sistema recomendado de 41 kWp, à vista | 0.727 | 78% |
| Retorno financeiro em 1º: retorno > risco > preferências > regulatório | Sistema recomendado de 41 kWp, à vista | 0.935 | 91% |
| Cautela: regulatório > preferências > risco > retorno | Sistema compacto de 20 kWp, à vista | 0.628 | 78% |

## Sensibilidade à taxa de financiamento (taxa de desconto = 12% a.a.)

Fontes de referência: BNB FNE Sol, piso de 7,9% a.a. (notícia, não verificado); BB Crédito Energia Renovável, 1,81% a.m. (~24,0% a.a.) e CET de 30,36% a.a. (texto do site informado pelo autor). Sem taxa informada, o sistema decide só com pagamento à vista.

| Taxa de financiamento a.a. | Recomendação (prioridade padrão) | Valor da alavancagem por R$ financiado |
|---|---|---|
| não informada (só à vista) | Sistema recomendado de 41 kWp, à vista | - |
| 7.90% | Sistema compacto de 20 kWp, financiado | 0.219 |
| 12.00% | Sistema compacto de 20 kWp, financiado | 0.049 |
| 24.04% | Sistema recomendado de 41 kWp, à vista | -0.519 |
| 30.36% | Sistema recomendado de 41 kWp, à vista | -0.847 |

## Perfil (agrupamento k-means de cenários simulados)

O caso pertence ao grupo 4: consumo baixo, tarifa baixa, perfil diurno (centróide de 1634 cenários simulados; P(VPL>0) = 100%; payback mediano = 3.0 anos).

## Cenários de custo, geração e área (recalculados pelo código)

O custo informado é tratado como fixo no Monte Carlo. A geração reduzida (fator de desempenho x 0,63) é uma **sensibilidade**, não previsão: reproduz o nível de geração específica das propostas NeoSolar (ver `docs/validacao_orcamentos.md`).

| Cenário | Recomendação | Investimento da alternativa exibida (R$) | VPL projeto (R$) | Payback (anos) | P(VPL>0) |
|---|---|---|---|---|---|
| Referência Greener de baixo custo (R$ 2.020/kWp) | Sistema recomendado de 41 kWp, à vista | 82,820 | 482,418 | 1.74 | 100% |
| Padrão do SAD (tabela x 1,20, incerteza de custo no MC) | Sistema recomendado de 41 kWp, à vista | 99,384 | 463,660 | 2.09 | 100% |
| Custo conforme orçamentos NeoSolar (R$ 5.200/kWp) | Sistema recomendado de 41 kWp, à vista | 213,200 | 334,768 | 4.33 | 100% |
| Custo NeoSolar + geração reduzida (x0,63) | Sistema recomendado de 42 kWp, à vista | 218,400 | 156,483 | 5.99 | 100% |
| Área utilizável de 240 m² (teto geométrico ~34 kWp), custo padrão | Sistema recomendado de 34 kWp, à vista | 82,416 | 408,261 | 1.93 | 100% |

## Testes de estresse (sistema de maior VPL, à vista, um parâmetro por vez)

| Variação | Investimento (R$) | Economia ano 1 (R$) | Payback (anos) | VPL (R$) | VPL > 0? |
|---|---|---|---|---|---|
| Cenário-base | 99,384 | 47,513 | 2.09 | 463,660 | sim |
| Custo de instalação +50% | 124,230 | 47,513 | 2.59 | 435,523 | sim |
| Tarifa -30% (R$ 0,77) | 99,384 | 40,650 | 2.43 | 380,430 | sim |
| Desempenho real 80% do projetado | 99,384 | 43,136 | 2.29 | 395,294 | sim |
| Simultaneidade 60% | 99,384 | 47,320 | 2.10 | 458,415 | sim |
| Fio B 100% desde 2029 (já é o padrão) | 99,384 | 47,513 | 2.09 | 463,660 | sim |
| Fio B 60% após 2028 | 99,384 | 47,513 | 2.08 | 487,724 | sim |
| Taxa de desconto 20% | 99,384 | 47,513 | 2.09 | 209,534 | sim |
| Consumo diurno 20% | 99,384 | 43,077 | 2.33 | 391,801 | sim |
| Combinado: custo +50%, tarifa -30%, desempenho 80% | 124,230 | 36,905 | 3.30 | 293,802 | sim |
