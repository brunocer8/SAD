# Validação da decisão — Bom Jesus da Lapa (BA)

**Cenário reproduzível:** consumo 250 kWh/mês; área útil do telhado 30 m²; ligação bifásica; tarifa B1 de R$ 0,87773/kWh, sem tributos; perfil de consumo “dia e noite” (45% no período diurno); aquisição à vista; orçamento automático; perfil de prioridade padrão. Dados de referência, não orçamento ou previsão garantida.

**Resultado:** Sistema recomendado de 1.86 kWp, à vista.

| Alternativa | Investimento (R$) | VPL (R$) | Payback (anos) | Nota SAW | Situação |
|---|---:|---:|---:|---:|---|
| Sistema recomendado de 1.86 kWp, à vista | 6,994.34 | 14,102.86 | 3.71 | 0.946 | Recomendado |
| Sistema compacto de 1.24 kWp, à vista | 5,324.06 | 10,901.44 | 3.51 | 0.769 | Recomendado com ressalvas |
| Não instalar (manter a conta atual) | 0.00 | 0.00 | — | 0.130 | Referência (não instalar) |
| Sistema ampliado de 2.48 kWp, à vista | 8,574.85 | 13,235.81 | 4.35 | — | Não priorizada no perfil econômico |

A configuração de 2,48 kWp foi preservada na Garagem Solar, mas retirada da disputa econômica porque tem **maior investimento, menor VPL, payback maior, cobertura semelhante e risco simulado não superior** em relação ao sistema de 1,86 kWp. A exposição à compensação é uma diferença à parte, que o usuário pode estudar no perfil *Cautela*.

O filtro é **condicional ao perfil escolhido**, não um teorema de dominância de Pareto sobre todos os critérios. A ordenação padrão é uma escolha metodológica declarada, com suporte na literatura para prioridade dada ao VPL e à avaliação de risco. Os pesos são calculados pelo Rank Order Centroid, não tomados como porcentagens publicadas.

Para reproduzir: `python -m pytest -q tests/test_sad.py -k bom_jesus` e o cenário de formulário acima.
