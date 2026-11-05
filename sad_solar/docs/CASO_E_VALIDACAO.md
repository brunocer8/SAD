# Caso de demonstração e validação — Sol da Bahia

**Aviso:** este é um cenário **HIPOTÉTICO e didático**, não uma medição de energia gerada, 
nem a transcrição de conta de energia privada. O preço de R$ 0,87773/kWh é a referência B1 
homologada pela Neoenergia Coelba para 22/04/2026–21/04/2027, sem impostos e encargos adicionais. 
O custo de instalação vem da tabela de referência do protótipo, não de orçamento comercial atual.

## Entradas e restrições

- Município: **Salvador/BA**; consumo médio: **250 kWh/mês** (3.000 kWh/ano).
- Tarifa B1 convencional: **R$ 0,87773/kWh**, sem tributos; ligação bifásica (mínimo de 50 kWh/mês).
- Área **útil** de telhado: **30 m² hipotéticos**; consumo diurno de 45%; pagamento à vista.
- Limite geométrico aproximado: **30/7 = 4.29 kWp**; 
maior sistema discretizado permitido: **3.72 kWp**, 
6 módulos de 620 Wp.
- Sistema de maior VPL do projeto no cenário-base: **1.86 kWp**. 
Essa escolha pode não coincidir com a opção de maior nota SAW.

## Resultado gerado pelo código

**Recomendação multicritério:** Sistema recomendado de 1.86 kWp, à vista. Motivo: Maior índice SAW entre 2 alternativa(s) admissível(is) e a opção de não instalar. O perfil considera VPL e payback, risco financeiro, adequação à demanda e dependência de compensação na ordem escolhida pelo usuário, com pesos ROC. 1 alternativa(s) economicamente dominada(s) não disputaram o ranking no perfil de retorno e viabilidade; continuam visíveis para comparação.

| Posição | Alternativa | Nota SAW | VPL do projeto (R$) | Payback do projeto (anos) | Área aproximada (m²) |
|---:|---|---:|---:|---:|---:|
| 1 | Sistema recomendado de 1.86 kWp, à vista | 0.943 | 13,868.15 | 3.75 | 13.02 |
| 2 | Sistema compacto de 1.24 kWp, à vista | 0.708 | 9,552.26 | 3.81 | 8.68 |
| 3 | Não instalar (manter a conta atual) | 0.130 | 0.00 | — | 0.00 |
| 4 | Sistema ampliado de 2.48 kWp, à vista | — | 12,954.25 | 4.39 | 17.36 |

**Interpretação:** a recomendação é consequência dos filtros e dos pesos da análise multicritério, 
não uma promessa de redução real da fatura. Cada cenário usa geração solar simulada e despesas futuras estimadas.

## Validação por sensibilidade (recalcular entradas do SAD)

| Cenário | Recomendação | Potência exibida (kWp) | VPL exibido (R$) |
|---|---|---:|---:|
| Cenário-base | Sistema recomendado de 1.86 kWp, à vista | 1.86 | 13,868.15 |
| Consumo menor: 150 kWh/mês | Sistema recomendado de 1.24 kWp, à vista | 1.24 | 5,316.98 |
| Consumo maior: 450 kWh/mês | Sistema recomendado de 3.72 kWp, à vista | 3.72 | 30,996.95 |
| Custo de instalação maior: R$ 5.200/kWp | Sistema recomendado de 1.86 kWp, à vista | 1.86 | 10,835.82 |
| Tarifa marginal menor: R$ 0,25/kWh | Não instalar (manter a conta atual) | 1.24 | -1,591.25 |
| Área menor: 12 m² | Sistema recomendado de 1.24 kWp, à vista | 1.24 | 9,552.26 |
| Tarifa Social: limitação simplificada de 80 kWh | Sistema recomendado de 1.86 kWp, à vista | 1.86 | 8,123.98 |

## Estratégia de validação frente ao enunciado

1. **Validação técnica:** conferir `potência = módulos × 620/1000`, área = `potência × 7` 
e rejeição quando a área comporta menos de dois módulos; comparar saídas com cálculos manuais.
2. **Validação analítica:** executar `python scripts/validar_regressao.py` (cinco grupos por município) 
para obter R²/MAE/RMSE contra **geração simulada**, não produção medida.
3. **Validação da decisão:** comparar a recomendação sob tarifas, custos, consumo e área diferentes; 
testar o caso em que *não instalar* deve vencer (`tests/test_api.py`).
4. **Validação do protótipo:** executar `python -m pytest -q`, cadastrar usuário, simular, 
ver ranking, histórico e exportar CSV.

## Limitações que precisam aparecer no relatório acadêmico

- Telhado e custo estimados; sem vistoria estrutural, sombreamento ou proposta de instalador.
- Tarifa homologada B1 sem tributos, enquanto contas reais incluem regras adicionais; 
o cenário Tarifa Social usa simplificação, não cálculo regulatório completo.
- Regressão com alvo **simulado pelo pvlib**, não dados medidos de instalações reais.
- Consumo residencial sem sazonalidade nem curva de carga horária; autoconsumo é estimado.
- Fio B de 2029+ modelado como cenário de 100%, não como percentual fixado diretamente pela lei.
- Não comparar VPL projetado com projeções de outros softwares sem uniformizar hipóteses.
