"""Caso concreto de demonstração + testes de estresse (sensibilidade determinística). Gera docs/caso_demonstracao.md.
Uso: python scripts/caso_demonstracao.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import financeiro as f
import saw

U = dict(cod_ibge=f.buscar_municipio("Salvador"), consumo_mes_kwh=4000, tarifa_kwh=1.10, consumo_diurno_fracao=0.6, area_m2=300)
d = saw.decisao(U)
L = ["# Caso de demonstração: PME comercial em Salvador", "",
     "Entradas: Salvador-BA; 4.000 kWh/mês; R$ 1,10/kWh (com tributos); 60% do consumo durante o dia; telhado de 300 m².", "",
     f"Limite técnico: {f.dimensionar(U)['teto_kwp']} kWp (min. entre 75 kWp e área/7 m² por kWp). "
     f"Tamanho que maximiza o VPL no cenário-base: {f.dimensionar(U)['kwp_recomendado']:.0f} kWp.", "",
     "## Ranking (filtro de viabilidade -> SAW -> agrupamento)", "",
     "| Pos. | Grupo | Alternativa | Índice SAW | VPL (R$) | Payback (anos) | Prob. VPL>0 | Lidera nos sorteios de pesos | Veredito |",
     "|---|---|---|---|---|---|---|---|---|"]
for a in d["ranking"]:
    pr = (a["risco"]["prob_vpl_positivo_financiado" if a["financiado"] else "prob_vpl_positivo"]) if "risco" in a else None
    L.append(f"| {a['posicao'] or '-'} | {a['grupo']} | {a['nome']} | {'-' if a['indice'] is None else f'{a['indice']:.3f}'} | {a['vpl']:,.0f} | "
             f"{a['payback']:.2f} | {'-' if pr is None else f'{pr:.0%}'} | {a['prob_lider']:.0%} | {a['veredito']['classe'] if 'veredito' in a else '-'} |")
rec = d["recomendacao"]
L += ["", f"**Recomendação do SAD:** {rec['nome']} ({rec['motivo']}) Corte do agrupamento: {d['delta']:.3f}.", ""]

# testes de estresse sobre o sistema "recomendado" à vista (maior VPL), um parâmetro por vez
k = f.dimensionar(U)["kwp_recomendado"]
e0 = f.montar_entrada({**U, "financiado": 0}, k)
r0 = f.simular(e0)
L += ["## Testes de estresse (sistema de maior VPL, à vista, um parâmetro por vez)", "",
      "| Variação | Investimento (R$) | Economia ano 1 (R$) | Payback (anos) | VPL (R$) | VPL > 0? |", "|---|---|---|---|---|---|"]
for nome, mod in {"Cenário-base": {}, "Custo de instalação +50%": {"fator_custo": 1.5}, "Tarifa -30% (R$ 0,77)": {"tarifa_kwh": 0.77},
                  "Desempenho real 80% do projetado": {"fator_desempenho_real": 0.80}, "Fio B 100% desde 2029 (já é o padrão)": {"fio_b_2029_em_diante": 1.0},
                  "Taxa de desconto 20%": {"taxa_desconto": 0.20}, "Consumo diurno 20%": {"consumo_diurno_fracao": 0.2},
                  "Combinado: custo +50%, tarifa -30%, desempenho 80%": {"fator_custo": 1.5, "tarifa_kwh": 0.77, "fator_desempenho_real": 0.80}}.items():
    r = f.simular({**e0, **mod})
    pb = r["payback"][0]
    L.append(f"| {nome} | {r['investimento'][0]:,.0f} | {r['economia_ano1'][0]:,.0f} | {'sem retorno' if pb != pb else f'{pb:.2f}'} | {r['vpl'][0]:,.0f} | {'sim' if r['vpl'][0] > 0 else 'não'} |")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "caso_demonstracao.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
