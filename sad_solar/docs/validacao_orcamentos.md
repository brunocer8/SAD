# Validação do modelo contra orçamentos e simulações externas (Salvador)

Entradas comuns: conta de R$ 4.400/mês (consumo 4.889 kWh/mês a R$ 0,90/kWh, como na proposta NeoSolar), 60% do consumo de dia. O investimento de cada linha é o da referência (fator de custo ajustado); o resto vem do modelo. Os paybacks das referências são simples, mas as calculadoras não revelam suas premissas.

| Referência | kWp | Invest. (R$) | R$/Wp | Ger. ref. (kWh/mês) | Ger. modelo | Econ. ref. (R$/ano) | Econ. modelo | Payback ref. (anos) | Payback modelo | TIR ref. | TIR modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Portal Solar, calculadora (menor valor) | 44.4 | 88,350 | 1.99 | 5799 | 5,507 | 54247 | 47,513 | 2.75 | 1.86 | - | 57.9% |
| Portal Solar, calculadora (maior valor) | 44.4 | 106,950 | 2.41 | 5799 | 5,507 | 54247 | 47,513 | 2.75 | 2.24 | - | 48.6% |
| WEG Solar, calculadora | 40.0 | 94,232 | 2.36 | - | 4,961 | - | 47,513 | 3.8 | 1.98 | - | 54.5% |
| NeoSolar, proposta comercial | 54.0 | 270,812 | 5.02 | 4839 | 6,697 | 52260 | 47,513 | 4.5 | 5.20 | 33.1% | 23.6% |

Observações das referências: Portal Solar, calculadora (menor valor): estimativa de calculadora; 80 módulos de 555 W; Portal Solar, calculadora (maior valor): idem; WEG Solar, calculadora: kWp NÃO informado (assumido 40 kWp, ~R$ 2,36/Wp); NeoSolar, proposta comercial: proposta real: 120 painéis de 450 W; tarifa 0,90; inflação 8%; perda 0,7%/ano

## Leitura

- **Proposta NeoSolar (única proposta real e completa):** com o mesmo investimento, tarifa e inflação, o modelo dá payback e TIR mais conservadores que a proposta, porque desconta Fio B, custo de disponibilidade, O&M e troca de inversor. O motor de cálculo é coerente com uma proposta comercial.
- **Calculadoras (Portal Solar, WEG):** informam paybacks maiores que o modelo para o mesmo investimento (a WEG, quase o dobro). Suas premissas não são divulgadas; podem usar tarifa efetiva menor (sem tributos ou com bandeira), perfil de consumo diferente ou desconto de capital. Diferença **não explicada**: é incerteza real do resultado.
- **Custo por kWp:** a tabela Greener (R$ 2,02 a 2,07/Wp) está no limite inferior das calculadoras (R$ 1,99 a 2,41/Wp) e muito abaixo da proposta real (R$ 5,01/Wp). Por isso o fator de custo foi recalibrado (padrão 1,20; sorteio triangular de 0,95 a 2,40).
- **Geração:** o modelo estima 4,08 kWh/kWp.dia para Salvador, entre a NeoSolar (~2,95; fonte NASA/NREL declarada, mas aparentemente conservadora) e a Portal Solar (~4,3).
- **Caso-base anterior (R$ 1,10/kWh e R$ 2,02/Wp)** era otimista (payback 1,45 ano): a tarifa efetiva da conta de R$ 4.400 é ~R$ 0,90/kWh e o custo real é maior.
