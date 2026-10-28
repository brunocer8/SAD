"""Confronta o modelo com 3 referências externas para Salvador (conta de R$ 4.400/mês). Gera docs/validacao_orcamentos.md.
Uso: python scripts/validar_orcamentos.py
Entradas do modelo: consumo 4.889 kWh/mês e tarifa R$ 0,90 (conta de R$ 4.400, dados da proposta NeoSolar), 60% diurno; investimento = o da referência."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import financeiro as f

COD = f.buscar_municipio("Salvador")
U = dict(cod_ibge=COD, consumo_mes_kwh=4889, tarifa_kwh=0.90, consumo_diurno_fracao=0.6, financiado=0)
REFS = [  # nome, kWp, investimento, reajuste tarifa, ger. mensal ref, economia anual ref, payback ref (anos), TIR ref, observação
    ("Portal Solar, calculadora (menor valor)", 44.4, 88350, 0.06, 5799, 54247, 2.75, None, "estimativa de calculadora; 80 módulos de 555 W"),
    ("Portal Solar, calculadora (maior valor)", 44.4, 106950, 0.06, 5799, 54247, 2.75, None, "idem"),
    ("WEG Solar, calculadora", 40.0, 94232, 0.06, None, None, 3.8, None, "kWp NÃO informado (assumido 40 kWp, ~R$ 2,36/Wp)"),
    ("NeoSolar, proposta comercial", 54.0, 270812, 0.08, 4839, 52260, 4.5, 0.3309, "proposta real: 120 painéis de 450 W; tarifa 0,90; inflação 8%; perda 0,7%/ano"),
]
L = ["# Validação do modelo contra orçamentos e simulações externas (Salvador)", "",
     "Entradas comuns: conta de R$ 4.400/mês (consumo 4.889 kWh/mês a R$ 0,90/kWh, como na proposta NeoSolar), 60% do consumo de dia. "
     "O investimento de cada linha é o da referência (fator de custo ajustado); o resto vem do modelo. Os paybacks das referências são simples, "
     "mas as calculadoras não revelam suas premissas.", "",
     "| Referência | kWp | Invest. (R$) | R$/Wp | Ger. ref. (kWh/mês) | Ger. modelo | Econ. ref. (R$/ano) | Econ. modelo | Payback ref. (anos) | Payback modelo | TIR ref. | TIR modelo |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for nome, kwp, inv, reaj, ger, eco, pb, tir, obs in REFS:
    e = f.montar_entrada(U, kwp)
    base = f.custo_kwp_tabela(np.array([kwp]))[0] * kwp
    e["fator_custo"] = inv / base; e["reajuste_tarifa"] = reaj
    r = f.simular(e)
    L.append(f"| {nome} | {kwp} | {inv:,.0f} | {inv / kwp / 1000:.2f} | {ger or '-'} | {r['geracao_ano1'][0] / 12:,.0f} | {eco or '-'} | {r['economia_ano1'][0]:,.0f} | "
             f"{pb} | {r['payback'][0]:.2f} | {'-' if tir is None else f'{tir:.1%}'} | {r['tir'][0]:.1%} |")
L += ["", "Observações das referências: " + "; ".join(f"{x[0]}: {x[8]}" for x in REFS), "",
      "## Leitura", "",
      "- **Proposta NeoSolar (única proposta real e completa):** com o mesmo investimento, tarifa e inflação, o modelo dá payback e TIR mais conservadores que a proposta, "
      "porque desconta Fio B, custo de disponibilidade, O&M e troca de inversor. O motor de cálculo é coerente com uma proposta comercial.",
      "- **Calculadoras (Portal Solar, WEG):** informam paybacks maiores que o modelo para o mesmo investimento (a WEG, quase o dobro). Suas premissas não são divulgadas; "
      "podem usar tarifa efetiva menor (sem tributos ou com bandeira), perfil de consumo diferente ou desconto de capital. Diferença **não explicada**: é incerteza real do resultado.",
      "- **Custo por kWp:** a tabela Greener (R$ 2,02 a 2,07/Wp) está no limite inferior das calculadoras (R$ 1,99 a 2,41/Wp) e muito abaixo da proposta real (R$ 5,01/Wp). "
      "Por isso o fator de custo foi recalibrado (padrão 1,20; sorteio triangular de 0,95 a 2,40).",
      "- **Geração:** o modelo estima 4,08 kWh/kWp.dia para Salvador, entre a NeoSolar (~2,95; fonte NASA/NREL declarada, mas aparentemente conservadora) e a Portal Solar (~4,3).",
      "- **Caso-base anterior (R$ 1,10/kWh e R$ 2,02/Wp)** era otimista (payback 1,45 ano): a tarifa efetiva da conta de R$ 4.400 é ~R$ 0,90/kWh e o custo real é maior."]
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "validacao_orcamentos.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:12]))
