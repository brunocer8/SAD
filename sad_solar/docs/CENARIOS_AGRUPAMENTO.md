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

## Resultado da varredura

Das 243 combinações, 17 formaram um grupo com duas ou mais alternativas. A tabela registra os grupos compartilhados. O comando `--grade` também lista as alternativas restantes e a recomendação de cada cenário.

| Município | Consumo (kWh/mês) | Área (m²) | Tarifa (R$/kWh) | Prioridade | Grupo | Alternativas e índices SAW | Limite de distância |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Salvador | 250 | 30 | 1,20000 | cautela | 1 | 1,86 kWp (0,867940978), 2,48 kWp (0,865736045) | 0,031332065 |
| Salvador | 250 | 60 | 1,20000 | cautela | 1 | 1,86 kWp (0,867940978), 2,48 kWp (0,865736045) | 0,031332065 |
| Feira de Santana | 250 | 30 | 0,50000 | cautela | 3 | 1,24 kWp (0,285110069), Não instalar (0,276041667) | 0,032413265 |
| Feira de Santana | 250 | 30 | 0,87773 | cautela | 1 | 1,86 kWp (0,859383305), 2,48 kWp (0,856162406) | 0,032124656 |
| Feira de Santana | 250 | 30 | 1,20000 | cautela | 1 | 2,48 kWp (0,884550951), 1,86 kWp (0,859383305) | 0,032581375 |
| Feira de Santana | 250 | 60 | 0,50000 | cautela | 3 | 1,24 kWp (0,285110069), Não instalar (0,276041667) | 0,032413265 |
| Feira de Santana | 250 | 60 | 0,87773 | cautela | 1 | 1,86 kWp (0,859383305), 2,48 kWp (0,856162406) | 0,032124656 |
| Feira de Santana | 250 | 60 | 1,20000 | cautela | 1 | 2,48 kWp (0,884550951), 1,86 kWp (0,859383305) | 0,032581375 |
| Barreiras | 250 | 30 | 1,20000 | cautela | 1 | 1,86 kWp (0,875719181), 2,48 kWp (0,869400543) | 0,030623789 |
| Barreiras | 250 | 60 | 1,20000 | cautela | 1 | 1,86 kWp (0,875719181), 2,48 kWp (0,869400543) | 0,030623789 |
| Barreiras | 1000 | 60 | 0,50000 | padrao | 1 | 8,06 kWp (0,939994298), 7,44 kWp (0,922462316) | 0,018537353 |
| Barreiras | 1000 | 60 | 0,50000 | retorno | 1 | 8,06 kWp (0,939994298), 7,44 kWp (0,927213212) | 0,017210367 |
| Barreiras | 1000 | 60 | 0,50000 | cautela | 1 | 8,06 kWp (0,861747662), 7,44 kWp (0,831904349) | 0,037065381 |
| Barreiras | 1000 | 60 | 0,87773 | retorno | 1 | 8,06 kWp (0,940428294), 7,44 kWp (0,924140503) | 0,017165400 |
| Barreiras | 1000 | 60 | 0,87773 | cautela | 1 | 8,06 kWp (0,861973340), 7,44 kWp (0,830473827) | 0,037049053 |
| Barreiras | 1000 | 60 | 1,20000 | retorno | 1 | 8,06 kWp (0,940569246), 7,44 kWp (0,923564121) | 0,017151706 |
| Barreiras | 1000 | 60 | 1,20000 | cautela | 1 | 8,06 kWp (0,862046635), 7,44 kWp (0,830928841) | 0,037063202 |
