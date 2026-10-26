"""
Decisão multicritério pelo método SAW (Simple Additive Weighting / Soma Ponderada).

Alternativas: três tamanhos de sistema (recomendado, compacto, ampliado) x dois modos de
pagamento (à vista, financiado) + a opção "não instalar". Cada alternativa recebe um índice
SAW = soma(peso x valor normalizado) e as opções são ordenadas por esse índice.

Pesos por FATOR, em ordem decrescente de preferência (a ordem pedida na disciplina), obtidos pelo método ROC:
    1) Teórica 52%  2) Normativa/Legal 27%  3) Cultural 15%  4) Modelos preditivos 6%
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
# Pesos: a ordem de preferência dos fatores (Teórica > Normativa > Cultural > Preditiva) vira pesos pelo método dos
# centroides de ranking (ROC, Barron e Barrett, 1996): w_i = (1/n) * soma(1/j, j=i..n) -> 52%, 27%, 15% e 6%.
# Dentro de cada fator, os critérios dividem o peso igualmente.
_FAT = ["1) Teórica", "2) Normativa/Legal", "3) Cultural", "4) Modelos preditivos"]
PESO_FATOR = {f: sum(1 / j for j in range(i, len(_FAT) + 1)) / len(_FAT) for i, f in enumerate(_FAT, 1)}
_N = {f: sum(1 for c in CRITERIOS if c[2] == f) for f in _FAT}
CRITERIOS = [(c[0], c[1], c[2], PESO_FATOR[c[2]] / _N[c[2]], c[4]) for c in CRITERIOS]
LIM_PROB, LIM_PAYBACK, LIM_COBERTURA = 0.90, 5.0, 0.90


def veredito(res: dict, risco: dict, fin: int) -> dict:
    """Recomendado / com ressalvas / não recomendado (limites declarados como premissas do autor)."""
    prob = risco["prob_vpl_positivo_financiado" if fin else "prob_vpl_positivo"]
    if res["vpl"] <= 0 or prob < 0.5:
        return dict(classe="Não recomendado no cenário atual", nivel="nao",
                    ressalvas=["o VPL é negativo ou o projeto não se paga com segurança nas condições analisadas"])
    r = []
    if res["cobertura_consumo"] < LIM_COBERTURA:
        r.append(f"o sistema cobre {res['cobertura_consumo']:.0%} do consumo; o restante continua sendo comprado da distribuidora")
    if prob < LIM_PROB:
        r.append(f"em {1 - prob:.0%} dos cenários simulados o VPL é negativo")
    pb = risco["payback_a_vista"]["mediana"]
    if pb != pb or pb > LIM_PAYBACK:
        r.append(f"o retorno à vista passa de {LIM_PAYBACK:.0f} anos")
    fl = res["fluxo_acumulado"]
    if fin and len(fl) > 1 and fl[1] - fl[0] < 0:
        r.append("a parcela do financiamento supera a economia no primeiro ano")
    return dict(classe="Recomendado com ressalvas" if r else "Recomendado", nivel="ressalvas" if r else "sim", ressalvas=r)


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
                vpl_p10=vp["p10"], investimento=r["investimento"], res=r, risco=rk, veredito=veredito(r, rk, fin)))
    alts.append(dict(nome="Não instalar (manter a conta atual)", kwp=0.0, financiado=0, vpl=0.0, payback=float(VIDA), fio_b=0.0,
                     folga_limite=1.0, cobertura=0.0, sem_divida=1, prob_vpl=0.0, vpl_p10=0.0, investimento=0.0))
    return dict(criterios=[dict(id=c[0], nome=c[1], fator=c[2], peso=c[3], sentido=c[4]) for c in CRITERIOS], ranking=agrupar(ranquear(alts)), delta=DELTA)
