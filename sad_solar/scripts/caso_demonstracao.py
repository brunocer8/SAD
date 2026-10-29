"""Caso concreto de demonstração + testes de estresse (sensibilidade determinística). Gera docs/caso_demonstracao.md.
Uso: python scripts/caso_demonstracao.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import financeiro as f
import saw

U = dict(cod_ibge=f.buscar_municipio("Salvador"), consumo_mes_kwh=4889, tarifa_kwh=0.90, consumo_diurno_fracao=0.6, area_m2=300)
d = saw.decisao(U)
L = ["# Caso de demonstração: PME comercial em Salvador", "",
     "Entradas: Salvador-BA; 4.889 kWh/mês (conta de R$ 4.400); R$ 0,90/kWh (com tributos); 60% do consumo durante o dia; telhado de 300 m² (**premissa explícita do caso demonstrativo, não dado da proposta NeoSolar**; o campo é a área UTILIZÁVEL). Consumo e tarifa vêm da proposta NeoSolar de 54 kWp, usada só como referência externa.", "",
     f"Limite técnico: {f.dimensionar(U)['teto_kwp']} kWp (min. entre 75 kWp e área/7 m² por kWp). "
     f"Tamanho que maximiza o VPL no cenário-base: {f.dimensionar(U)['kwp_recomendado']:.0f} kWp.", "",
     "## Ranking (filtro de viabilidade -> SAW -> agrupamento)", "",
     "| Pos. | Grupo | Alternativa | Índice SAW | VPL projeto (R$) | VPL capital próprio (R$) | Payback projeto (anos) | Prob. VPL>0 | Lidera (pesos) | Líder supera | Veredito |",
     "|---|---|---|---|---|---|---|---|---|---|---|"]
for a in d["ranking"]:
    pr = (a["risco"]["prob_vpl_positivo_financiado" if a["financiado"] else "prob_vpl_positivo"]) if "risco" in a else None
    L.append(f"| {a['posicao'] or '-'} | {a['grupo']} | {a['nome']} | {'-' if a['indice'] is None else f'{a['indice']:.3f}'} | {a['vpl_projeto']:,.0f} | {a['vpl']:,.0f} | "
             f"{a['payback']:.2f} | {'-' if pr is None else f'{pr:.0%}'} | {a['prob_lider']:.0%} | {'-' if a.get('prob_lider_supera') is None else format(a['prob_lider_supera'], '.0%')} | {a['veredito']['classe'] if 'veredito' in a else '-'} |")
rec = d["recomendacao"]
L += ["", f"**Recomendação do SAD:** {rec['nome']} ({rec['motivo']}) Corte do agrupamento: {d['delta']:.3f}.", ""]

# --- decisão sob três prioridades do decisor
L += ["## A recomendação muda com as preferências do decisor", "", "| Prioridade (ordem dos fatores) | Recomendação | Índice | Lidera nos sorteios de pesos |", "|---|---|---|---|"]
nomes = {"padrao": "Padrão: retorno > regulatório > preferências > risco", "retorno": "Retorno financeiro em 1º: retorno > risco > preferências > regulatório",
         "cautela": "Cautela: regulatório > preferências > risco > retorno"}
for p, rot in nomes.items():
    dd = saw.decisao({**U, "prioridade": p}); rc = dd["recomendacao"]
    L.append(f"| {rot} | {rc['nome']} | {'-' if rc['indice'] is None else f'{rc['indice']:.3f}'} | {rc['prob_lider']:.0%} |")
# --- sensibilidade à taxa de financiamento (a taxa é informada pelo decisor; sem ela só há alternativas à vista)
L += ["", "## Sensibilidade à taxa de financiamento (taxa de desconto = 12% a.a.)", "",
      "Fontes de referência: BNB FNE Sol, piso de 7,9% a.a. (notícia, não verificado); BB Crédito Energia Renovável, 1,81% a.m. (~24,0% a.a.) e CET de 30,36% a.a. (texto do site informado pelo autor). Sem taxa informada, o sistema decide só com pagamento à vista.", "",
      "| Taxa de financiamento a.a. | Recomendação (prioridade padrão) | Valor da alavancagem por R$ financiado |", "|---|---|---|"]
dd = saw.decisao(U); L.append(f"| não informada (só à vista) | {dd['recomendacao']['nome']} | - |")
for tx in (0.079, 0.12, 0.2404, 0.3036):
    dd = saw.decisao({**U, "taxa_financiamento": tx}); rc = dd["recomendacao"]
    g = next((a["ganho_fin"] for a in dd["ranking"] if a["financiado"] and a.get("res")), float("nan"))
    L.append(f"| {tx:.2%} | {rc['nome']} | {g:.3f} |")
pf = dd = saw.decisao(U)["perfil"]
L += ["", f"## Perfil (agrupamento k-means de cenários simulados)", "", f"O caso pertence ao grupo {pf['indice']}: {pf['nome']} (centróide de {pf['n']} cenários simulados; P(VPL>0) = {pf['prob_vpl_positivo']:.0%}; payback mediano = {pf['payback_mediano']:.1f} anos)." if pf else "", ""]
# --- cenários de custo, geração e área
def _linha(rot, **kw):
    d = saw.decisao({**U, **kw}); rc = d["recomendacao"]; x = d["ranking"][rc["indice_exibido"]]
    r = x["res"]; pr = x["risco"]["prob_vpl_positivo"]
    return (f"| {rot} | {rc['nome']} | {r['investimento']:,.0f} | {x['vpl_projeto']:,.0f} | {x['payback']:.2f} | {pr:.0%} |")
L += ["## Cenários de custo, geração e área (recalculados pelo código)", "",
      "O custo informado é tratado como fixo no Monte Carlo. A geração reduzida (fator de desempenho x 0,63) é uma **sensibilidade**, não previsão: reproduz o nível de geração específica das propostas NeoSolar (ver `docs/validacao_orcamentos.md`).", "",
      "| Cenário | Recomendação | Investimento da alternativa exibida (R$) | VPL projeto (R$) | Payback (anos) | P(VPL>0) |", "|---|---|---|---|---|---|",
      _linha("Referência Greener de baixo custo (R$ 2.020/kWp)", custo_kwp=2020),
      _linha("Padrão do SAD (tabela x 1,20, incerteza de custo no MC)"),
      _linha("Custo conforme orçamentos NeoSolar (R$ 5.200/kWp)", custo_kwp=5200),
      _linha("Custo NeoSolar + geração reduzida (x0,63)", custo_kwp=5200, fator_desempenho_real=0.95 * 0.63),
      _linha("Área utilizável de 240 m² (teto geométrico ~34 kWp), custo padrão", area_m2=240), ""]
# testes de estresse sobre o sistema "recomendado" à vista (maior VPL), um parâmetro por vez
k = f.dimensionar(U)["kwp_recomendado"]
e0 = f.montar_entrada({**U, "financiado": 0}, k)
r0 = f.simular(e0)
L += ["## Testes de estresse (sistema de maior VPL, à vista, um parâmetro por vez)", "",
      "| Variação | Investimento (R$) | Economia ano 1 (R$) | Payback (anos) | VPL (R$) | VPL > 0? |", "|---|---|---|---|---|---|"]
for nome, mod in {"Cenário-base": {}, "Custo de instalação +50%": {"fator_custo": 1.5}, "Tarifa -30% (R$ 0,77)": {"tarifa_kwh": 0.77},
                  "Desempenho real 80% do projetado": {"fator_desempenho_real": 0.80}, "Simultaneidade 60%": {"simultaneidade": 0.60}, "Fio B 100% desde 2029 (já é o padrão)": {"fio_b_2029_em_diante": 1.0}, "Fio B 60% após 2028": {"fio_b_2029_em_diante": 0.6},
                  "Taxa de desconto 20%": {"taxa_desconto": 0.20}, "Consumo diurno 20%": {"consumo_diurno_fracao": 0.2},
                  "Combinado: custo +50%, tarifa -30%, desempenho 80%": {"fator_custo": 1.5, "tarifa_kwh": 0.77, "fator_desempenho_real": 0.80}}.items():
    r = f.simular({**e0, **mod})
    pb = r["payback"][0]
    L.append(f"| {nome} | {r['investimento'][0]:,.0f} | {r['economia_ano1'][0]:,.0f} | {'sem retorno' if pb != pb else f'{pb:.2f}'} | {r['vpl'][0]:,.0f} | {'sim' if r['vpl'][0] > 0 else 'não'} |")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "caso_demonstracao.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
