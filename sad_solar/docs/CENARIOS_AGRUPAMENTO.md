# Agrupamento das alternativas no SAD

O caso-base de Salvador documentado em [Caso de demonstração e validação](CASO_E_VALIDACAO.md) produz grupos unitários. Em um cenário de sensibilidade com tarifa de R$ 1,20/kWh e prioridade Cautela, duas instalações entram no grupo líder. O caso é hipotético e mantém o consumo e a área do exemplo original.

## Entradas

| Entrada | Valor |
| --- | --- |
| Município | Salvador (código IBGE 2927408) |
| Consumo mensal | 250 kWh |
| Área útil | 30 m² |
| Tarifa marginal | R$ 1,20000/kWh |
| Ligação | Bifásica, com mínimo faturável mensal de 50 kWh |
| Consumo diurno | 45% |
| Tarifa Social | Desativada |
| Forma de pagamento | À vista |
| Prioridade | Maior cautela regulatória |
| Custo de instalação | Referência automática do SAD |

## Resultado

| Posição | Alternativa | Índice SAW | Grupo |
| ---: | --- | ---: | ---: |
| 1 | Sistema recomendado de 1,86 kWp | 0,867940978 | 1 |
| 2 | Sistema ampliado de 2,48 kWp | 0,865736045 | 1 |
| 3 | Sistema compacto de 1,24 kWp | 0,646498225 | 2 |
| 4 | Não instalar | 0,276041667 | 3 |

A diferença entre os índices das duas primeiras alternativas é 0,002204933. O agrupamento hierárquico por ligação completa usa o limite de distância de 0,031332065, obtido a partir da dispersão dos índices sob perturbações dos pesos. Como a diferença está dentro desse limite, as duas instalações ficam no grupo líder.

O SAD mantém a instalação de 1,86 kWp como recomendação oficial por ter o maior índice. O resumo informa que existe outra alternativa com pontuação muito próxima, e o cartão de 2,48 kWp indica que ela integra o grupo próximo ao líder. A opção de 1,86 kWp ficou em primeiro lugar em 59,1% das perturbações dos pesos. Essa frequência descreve a estabilidade da classificação frente aos pesos dentro do teste. A probabilidade de VPL positivo é calculada separadamente no Monte Carlo.

## Como reproduzir

Na pasta `sad_solar`, execute:

```sh
python scripts/validar_agrupamento.py
python scripts/validar_agrupamento.py --grade
python -m pytest tests/test_sad.py -k empate_tecnico_no_grupo_lider -q
```

O primeiro comando reproduz o cenário acima. O segundo lista os resultados com grupos compartilhados em 243 combinações de três municípios, consumos de 100 a 1.000 kWh/mês, áreas de 10 a 60 m², tarifas de R$ 0,50 a R$ 1,20/kWh e três perfis de prioridade. Cada decisão usa as sementes fixas do próprio SAD, 7 para o Monte Carlo de viabilidade e 11 para a perturbação dos pesos, com 1.000 sorteios em cada etapa.
