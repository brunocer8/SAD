"""
Decisão multicritério pelo método SAW (Simple Additive Weighting / Soma Ponderada).

Alternativas: três tamanhos de sistema (recomendado, compacto, ampliado) x dois modos de
pagamento (à vista, financiado) + a opção "não instalar". Cada alternativa recebe um índice
SAW = soma(peso x valor normalizado) e as opções são ordenadas por esse índice.

Pesos por FATOR, em ordem decrescente de preferência (a ordem pedida na disciplina):
    1) Teórica 40%  2) Normativa/Legal 30%  3) Cultural 20%  4) Modelos preditivos 10%
Normalização linear min-max: critério de ganho (max) = (x-min)/(max-min);
critério de custo (min) = (max-x)/(max-min). Se todas as alternativas empatam, vale 1.
Os pesos são premissas do autor (editáveis em CRITERIOS).
"""
from financeiro import analisar, dimensionar
from montecarlo import analisar_risco
from parametros import PARAMETROS

CRITERIOS = [  # id, nome, fator, peso, sentido
    ("vpl", "VPL em 25 anos (R$)", "1) Teórica", 0.25, "max"),
    ("payback", "Payback (anos)", "1) Teórica", 0.15, "min"),
    ("fio_b", "Custo do Fio B no ano 1 (R$), Lei 14.300", "2) Normativa/Legal", 0.15, "min"),
    ("folga_limite", "Folga até o limite de 75 kWp da microgeração", "2) Normativa/Legal", 0.15, "max"),
    ("cobertura", "Cobertura do consumo (autossuficiência)", "3) Cultural", 0.10, "max"),
    ("sem_divida", "Sem endividamento (0 ou 1)", "3) Cultural", 0.10, "max"),
    ("prob_vpl", "Probabilidade de VPL positivo (Monte Carlo)", "4) Modelos preditivos", 0.05, "max"),
    ("vpl_p10", "VPL no cenário pessimista, percentil 10 (R$)", "4) Modelos preditivos", 0.05, "max"),
]
VIDA = PARAMETROS["vida_util_anos"]["padrao"]
KWP_MAX = PARAMETROS["kwp_max"]["padrao"]


FATORES = list(dict.fromkeys(c[2] for c in CRITERIOS))
DELTA = 0.05  # índices a menos de 0,05 do líder do grupo são agrupados (ver agrupar)


def ranquear(alts: list[dict]) -> list[dict]:
    for a in alts:
        a["indice"], a["_n"] = 0.0, {}
    for cid, _, _, peso, sentido in CRITERIOS:
        v = [a[cid] for a in alts]
        lo, hi = min(v), max(v)
        for a in alts:
            n = 1.0 if hi == lo else ((a[cid] - lo) / (hi - lo) if sentido == "max" else (hi - a[cid]) / (hi - lo))
            a["_n"][cid] = n
            a["indice"] += peso * n
    for a in alts:  # desempenho (0 a 100) em cada fator: os "atributos" da carta
        a["atributos"] = {f: 100 * sum(c[3] * a["_n"][c[0]] for c in CRITERIOS if c[2] == f) / sum(c[3] for c in CRITERIOS if c[2] == f)
                          for f in FATORES}
        del a["_n"]
    alts.sort(key=lambda a: -a["indice"])
    for i, a in enumerate(alts, 1):
        a["posicao"] = i
    return alts


def agrupar(ranking: list[dict]) -> list[dict]:
    """Agrupa cenários de índice próximo: um grupo começa no líder e inclui quem está a até DELTA dele.
    DELTA = 0,05 vem da sensibilidade: variando os pesos em +-30%, o índice de cada cenário oscila ~0,02 a 0,03
    (desvio padrão), então diferenças menores que isso não distinguem os cenários."""
    comp = [a for a in ranking if not a["nome"].startswith("Não instalar")]
    grupos = []
    for a in comp:
        if grupos and grupos[-1][0]["indice"] - a["indice"] <= DELTA:
            grupos[-1].append(a)
        else:
            grupos.append([a])
    g = len(grupos)
    for i, gr in enumerate(grupos, 1):
        rot = ("Mais recomendado" if len(gr) == 1 else "Mais recomendados (índices muito próximos)") if i == 1 else \
              ("Menos indicados" if (i == g and g >= 3) else "Alternativas competitivas")
        for a in gr:
            a["grupo"], a["rotulo"] = i, rot
    for a in ranking:
        if a["nome"].startswith("Não instalar"):
            a["grupo"], a["rotulo"] = 0, "Referência: não investir"
    return ranking


def decisao(usuario: dict) -> dict:
    dim = dimensionar(usuario)
    rec, teto = dim["kwp_recomendado"], dim["teto_kwp"]
    tamanhos, vistos = [], set()
    for nome, k in (("Recomendado", rec), ("Compacto", max(3, round(rec * 0.5))), ("Ampliado", min(teto, round(rec * 1.3)))):
        if k not in vistos:
            vistos.add(k)
            tamanhos.append((nome, float(k)))
    alts = []
    for nome, k in tamanhos:
        for fin in (0, 1):
            u = {**usuario, "financiado": fin}
            r = analisar(u, kwp=k)
            rk = analisar_risco(u, kwp=k, n=600)
            vp = rk["vpl_financiado" if fin else "vpl_a_vista"]
            alts.append(dict(
                nome=f"Sistema {nome.lower()} de {k:.0f} kWp, {'financiado' if fin else 'à vista'}", kwp=k, financiado=fin,
                vpl=r["vpl"], payback=r["payback"] if r["payback"] is not None and r["payback"] == r["payback"] else VIDA,
                fio_b=r["custo_fio_b_ano1"], folga_limite=(KWP_MAX - k) / KWP_MAX, cobertura=r["cobertura_consumo"],
                sem_divida=0 if fin else 1, prob_vpl=rk["prob_vpl_positivo_financiado" if fin else "prob_vpl_positivo"],
                vpl_p10=vp["p10"], investimento=r["investimento"]))
    alts.append(dict(nome="Não instalar (manter a conta atual)", kwp=0.0, financiado=0, vpl=0.0, payback=float(VIDA), fio_b=0.0,
                     folga_limite=1.0, cobertura=0.0, sem_divida=1, prob_vpl=0.0, vpl_p10=0.0, investimento=0.0))
    return dict(criterios=[dict(id=c[0], nome=c[1], fator=c[2], peso=c[3], sentido=c[4]) for c in CRITERIOS], ranking=agrupar(ranquear(alts)), delta=DELTA)
