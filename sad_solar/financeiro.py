"""
Módulo financeiro do SAD de viabilidade de energia solar para PMEs na Bahia.

Fluxo:
  1. Geração específica do município (kWh/kWp.ano) pelo modelo de regressão linear
     (irradiação global, fração difusa e temperatura média), treinado sobre a simulação pvlib.
  2. Fluxo de caixa anual de 25 anos: economia na fatura, Fio B (Lei 14.300), O&M,
     troca do inversor, financiamento (Price com carência).
  3. Indicadores: payback simples e descontado, VPL, TIR, LCOE.
  4. Dimensionamento: kWp que maximiza o VPL, limitado por área de telhado e por 75 kWp.

Tudo é vetorizado (cada cenário é uma posição de um array), então o mesmo código
roda um caso determinístico (N = 1) ou milhares de cenários de Monte Carlo.

Balanço energético MENSAL (Lei 14.300/2022): em cada mês, a geração é abatida primeiro do consumo
simultâneo (autoconsumo, limitado pela fração diurna do consumo); o excedente vira crédito de energia,
que é usado nos meses seguintes para abater o consumo que vem da rede (acima do custo de disponibilidade).
Só a energia compensada paga Fio B. O perfil sazonal de geração vem do município (regressão linear).

Simplificações declaradas:
  - Consumo mensal constante (sem sazonalidade de consumo) e constante ao longo da vida do sistema.
  - Créditos com validade de 60 meses (consumo FIFO: os mais antigos primeiro); créditos expirados ou
    que sobram ao final da vida útil não têm valor.
  - Autoconsumo = min(simultaneidade x geração, fração diurna x consumo); sem curva de carga horária.
  - A fração diurna do consumo é a mesma em todos os meses.
  - Tarifa convencional (sem Tarifa Branca). O preço do kWh deve ser informado com tributos.
  - Fluxos de caixa no fim de cada ano; taxa de desconto nominal.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from parametros import CUSTO_KWP_PONTOS, FIO_B_PCT, PARAMETROS, UNIVERSO_PME, padroes

DADOS = Path(__file__).parent / "dados"
DIAS_MES = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
_KWP_PTS = np.array(sorted(CUSTO_KWP_PONTOS))
_CUSTO_PTS = np.array([CUSTO_KWP_PONTOS[k] for k in _KWP_PTS], dtype=float)


class AreaInsuficiente(ValueError):
    """A área de telhado informada não comporta o sistema mínimo (restrição técnica real)."""


KWP_MIN = UNIVERSO_PME["kwp_min"]
VALIDADE_MESES = 60   # validade dos créditos de energia (Lei 14.300/2022, art. 13)


# ------------------------------------------------------------------ dados por município
@lru_cache(maxsize=1)
def carregar_municipios():
    """Retorna (DataFrame por município, dict cod_ibge -> perfil mensal kWh/kWp)."""
    df = pd.read_csv(DADOS / "dataset_ba_modelo.csv")
    modelo = json.load(open(DADOS / "modelo_geracao_linear.json", encoding="utf-8"))
    coef = modelo["coeficientes"]
    df["geracao_dia_prev"] = modelo["intercepto"] + sum(df[k] * v for k, v in coef.items())
    df["dias"] = DIAS_MES[df["mes"].to_numpy() - 1]
    df["geracao_mes_prev"] = df["geracao_dia_prev"] * df["dias"]
    perfil = {c: g.sort_values("mes")["geracao_mes_prev"].to_numpy() for c, g in df.groupby("cod_ibge")}
    mun = (df.groupby(["cod_ibge", "municipio"], as_index=False)
             .agg(latitude=("latitude", "first"), longitude=("longitude", "first"),
                  ger_esp_anual=("geracao_mes_prev", "sum")))
    return mun.set_index("cod_ibge"), perfil


def buscar_municipio(nome: str) -> int:
    mun, _ = carregar_municipios()
    achados = mun[mun["municipio"].str.lower() == nome.lower()]
    if achados.empty:
        achados = mun[mun["municipio"].str.lower().str.contains(nome.lower())]
    if achados.empty:
        raise KeyError(f"Município não encontrado: {nome}")
    return int(achados.index[0])


def custo_kwp_tabela(kwp):
    """R$/kWp do sistema instalado (Greener, jun/2026), interpolado e limitado nas pontas."""
    return np.interp(kwp, _KWP_PTS, _CUSTO_PTS)


# ------------------------------------------------------------------ núcleo vetorizado
def _tir(full: np.ndarray) -> np.ndarray:
    n, tp = full.shape
    tt = np.arange(tp)

    def f(r):
        return (full * (1.0 + r)[:, None] ** (-tt)).sum(axis=1)

    lo, hi = np.full(n, -0.9), np.full(n, 10.0)
    ok = (f(lo) > 0) & (f(hi) < 0)
    for _ in range(80):
        mid = (lo + hi) / 2
        sobe = f(mid) > 0
        lo = np.where(sobe, mid, lo)
        hi = np.where(sobe, hi, mid)
    return np.where(ok, (lo + hi) / 2, np.nan)


def _payback(full: np.ndarray) -> np.ndarray:
    """Anos até o PRIMEIRO instante em que o fluxo acumulado fica >= 0 (interpolação linear no ano do cruzamento).
    0 se já começa não negativo; NaN se nunca recupera na vida útil."""
    cum = np.cumsum(full, axis=1)
    n = cum.shape[0]
    nonneg = cum >= 0
    achou = nonneg.any(axis=1)
    p = np.argmax(nonneg, axis=1)                       # primeiro índice com acumulado >= 0
    k = np.clip(p - 1, 0, None)
    lin = np.arange(n)
    passo = full[lin, p]
    frac = np.where(passo > 0, -cum[lin, k] / np.where(passo > 0, passo, 1.0), 0.0)
    res = np.where(p == 0, 0.0, k + frac)
    return np.where(achou, res, np.nan)


def perfil_sazonal(perfil_kwh_kwp) -> np.ndarray:
    """Converte o perfil mensal (kWh/kWp.mês) na fração da geração anual que ocorre em cada mês (soma 1)."""
    p = np.asarray(perfil_kwh_kwp, dtype=float)
    return p / p.sum(axis=-1, keepdims=True)


def simular(e: dict, devolver_fluxo: bool = False) -> dict:
    """Simula N cenários. Valores de `e` podem ser escalares ou arrays de tamanho N.
    `e["perfil"]` (opcional): fração da geração anual em cada mês, shape (12,) ou (N, 12)."""
    e = dict(e)
    perfil = e.pop("perfil", None)
    brut = np.broadcast_arrays(*[np.asarray(v, dtype=float) for v in e.values()])
    n = int(np.atleast_1d(brut[0]).size)

    def A(k):
        return np.broadcast_to(np.atleast_1d(np.asarray(e[k], dtype=float)), (n,)).astype(float)

    T = int(np.max(A("vida_util_anos")))
    t = np.arange(1, T + 1)[None, :]  # anos 1..T
    P = perfil_sazonal(DIAS_MES if perfil is None else perfil)
    P = np.broadcast_to(np.atleast_2d(P), (n, 12))

    kwp, ger_esp = A("kwp"), A("ger_esp_anual")
    cons_m = A("consumo_mes_kwh")
    cons = (cons_m * 12)[:, None]

    # --- energia: balanço MENSAL com banco de créditos (vetorizado sobre os N cenários)
    g0 = kwp * ger_esp * A("fator_desempenho_real")
    degr = 1 - A("degradacao_anual")
    carga_dia = A("consumo_diurno_fracao") * cons_m      # kWh/mês consumíveis na hora do sol
    minimo = A("custo_disponibilidade_kwh_mes")          # kWh/mês cobrados mesmo com créditos
    sim = A("simultaneidade")
    S = np.zeros((n, T)); comp = np.zeros((n, T)); injetada = np.zeros((n, T)); saldo_fim = np.zeros((n, T))
    expirado = np.zeros((n, T)); kwh_eco = np.zeros((n, T))
    faturavel = np.maximum(cons_m - minimo, 0.0)       # kWh/mês que a geração pode efetivamente abater da fatura
    lotes = np.zeros((n, VALIDADE_MESES))               # créditos por mês de origem (índice 0 = mais antigo)
    for ti in range(T):
        fa = degr ** ti
        for m in range(12):
            g = g0 * P[:, m] * fa
            s_m = np.minimum(sim * g, carga_dia)         # autoconsumo instantâneo: só a parte simultânea da geração
            inj = g - s_m                                # excedente injetado na rede vira crédito
            need = np.maximum(cons_m - s_m - minimo, 0.0)  # consumo da rede que pode ser abatido por créditos
            expirado[:, ti] += lotes[:, 0]               # o lote com 60 meses expira
            lotes = np.concatenate([lotes[:, 1:], inj[:, None]], axis=1)
            antes = np.cumsum(lotes, axis=1) - lotes     # créditos mais antigos que cada lote (consumo FIFO)
            uso = np.clip(need[:, None] - antes, 0.0, lotes)
            lotes = lotes - uso
            u_m = uso.sum(axis=1)
            S[:, ti] += s_m; comp[:, ti] += u_m; injetada[:, ti] += inj
            kwh_eco[:, ti] += np.minimum(s_m + u_m, faturavel)   # economia limitada ao consumo faturável acima do mínimo
        saldo_fim[:, ti] = lotes.sum(axis=1)
    G = S + injetada                                     # geração anual por ano (kWh)

    # --- economia
    tarifa_t = A("tarifa_kwh")[:, None] * (1 + A("reajuste_tarifa"))[:, None] ** (t - 1)
    ano = A("ano_inicio")[:, None] + t - 1
    pct_fio_b = np.where(ano <= 2026, FIO_B_PCT[2026],
                 np.where(ano == 2027, FIO_B_PCT[2027],
                  np.where(ano == 2028, FIO_B_PCT[2028], A("fio_b_2029_em_diante")[:, None])))
    custo_fio_b = tarifa_t * A("fio_b_share_tarifa")[:, None] * pct_fio_b * comp
    economia = tarifa_t * kwh_eco - custo_fio_b
    economia_injetada = tarifa_t * comp - custo_fio_b                       # parte da economia que depende da compensação

    # --- custos
    invest = kwp * custo_kwp_tabela(kwp) * A("fator_custo")
    infl = (1 + A("ipca"))[:, None] ** (t - 1)
    om = A("om_pct_investimento")[:, None] * invest[:, None] * infl
    ano_inv = A("inversor_ano_troca")[:, None]
    troca = (t == ano_inv) * (A("inversor_custo_pct")[:, None] * invest[:, None] * infl)

    # --- financiamento (Price, juros capitalizados na carência)
    fin = A("financiado")
    F = invest * (1 - A("entrada_pct")) * fin
    im = (1 + A("taxa_financiamento")) ** (1 / 12) - 1
    car = A("carencia_meses")
    nparc = np.maximum(A("prazo_financiamento_anos") * 12 - car, 1.0)   # prazo TOTAL inclui a carência
    Fc = F * (1 + im) ** car
    pmt = np.where(im > 0, Fc * im / (1 - (1 + im) ** (-nparc)), Fc / nparc)
    meses = np.clip(np.minimum((car + nparc)[:, None], 12 * t) - np.maximum(car[:, None], 12 * (t - 1)), 0, 12)
    parcelas = pmt[:, None] * meses

    # --- fluxo de caixa
    cf0 = -(invest - F)
    cf = economia - om - troca - parcelas
    full = np.concatenate([cf0[:, None], cf], axis=1)

    # fluxo do PROJETO (sem financiamento): comparável entre tamanhos e formas de pagamento
    full_proj = np.concatenate([-invest[:, None], economia - om - troca], axis=1)
    d = A("taxa_desconto")
    disc = (1 + d)[:, None] ** (-np.arange(0, T + 1))[None, :]
    vpl = (full * disc).sum(axis=1)
    pb = _payback(full)
    pbd = _payback(full * disc)
    vpl_proj = (full_proj * disc).sum(axis=1)
    custo_pv = invest + ((om + troca) * disc[:, 1:]).sum(axis=1)
    lcoe = custo_pv / np.maximum((G * disc[:, 1:]).sum(axis=1), 1e-9)

    out = dict(
        investimento=invest, vpl=vpl, vpl_projeto=vpl_proj, payback_projeto=_payback(full_proj),
        parcelas_ano1=parcelas[:, 0], credito_expirado_ano1=expirado[:, 0], credito_expirado_total=expirado.sum(axis=1), tir=_tir(full), payback=pb, payback_descontado=pbd, lcoe=lcoe,
        geracao_ano1=G[:, 0], economia_ano1=economia[:, 0],
        cobertura_consumo=(S + comp)[:, 0] / cons[:, 0], credito_acumulado_ano1=saldo_fim[:, 0],
        custo_fio_b_ano1=custo_fio_b[:, 0],
        exposicao_regulatoria=np.clip(economia_injetada[:, 0] / np.maximum(economia[:, 0], 1e-9), 0.0, 1.0),
        autoconsumo_ano1=S[:, 0], compensada_ano1=comp[:, 0], injetada_ano1=injetada[:, 0],
    )
    if devolver_fluxo:
        out["fluxo"] = full
    return out


# ------------------------------------------------------------------ interface de alto nível
def montar_entrada(usuario: dict, kwp) -> dict:
    """Combina padrões + o que o usuário informou + dados do município. `kwp` pode ser array."""
    mun, perfil = carregar_municipios()
    cod = int(usuario["cod_ibge"])
    e = padroes()
    e.update({k: v for k, v in usuario.items() if k in PARAMETROS})
    e["ger_esp_anual"] = float(mun.loc[cod, "ger_esp_anual"])
    e["consumo_mes_kwh"] = float(usuario["consumo_mes_kwh"])
    e["financiado"] = float(usuario.get("financiado", 0))
    e["kwp"] = kwp
    e["perfil"] = perfil_sazonal(perfil[cod])
    return e


def dimensionar(usuario: dict) -> dict:
    """Varre o kWp (mínimo a limite de área/potência) e escolhe o que maximiza o VPL no cenário-base."""
    p = padroes()
    usuario = {**usuario, "financiado": 0}          # dimensiona pelo VPL do PROJETO (sem financiamento)
    teto = p["kwp_max"] * p.get("relacao_dc_ac", 1.0)
    if usuario.get("area_m2") is not None:
        if usuario["area_m2"] <= 0:
            raise ValueError("A área de telhado deve ser positiva (ou deixada em branco).")
        teto = min(teto, usuario["area_m2"] / p.get("m2_por_kwp", 7.0))
    teto = int(np.floor(teto))
    if teto < KWP_MIN:
        raise AreaInsuficiente(
            f"A área informada ({usuario['area_m2']:.0f} m²) comporta no máximo {teto} kWp, abaixo do sistema mínimo de "
            f"{KWP_MIN:.0f} kWp (~{KWP_MIN * p.get('m2_por_kwp', 7.0):.0f} m²). Não há alternativa tecnicamente admissível.")
    grade = np.arange(KWP_MIN, teto + 1, dtype=float)
    r = simular(montar_entrada(usuario, grade))
    i = int(np.argmax(r["vpl"]))
    tabela = pd.DataFrame({"kwp": grade, "investimento": r["investimento"], "vpl": r["vpl"],
                           "payback": r["payback"], "cobertura": r["cobertura_consumo"]})
    return dict(kwp_recomendado=float(grade[i]), tabela=tabela, teto_kwp=teto)


def analisar(usuario: dict, kwp: float | None = None) -> dict:
    """Análise determinística completa (cenário-base) para um cliente."""
    mun, perfil = carregar_municipios()
    cod = int(usuario["cod_ibge"])
    dim = dimensionar(usuario)
    kwp = float(kwp if kwp is not None else dim["kwp_recomendado"])
    e = montar_entrada(usuario, kwp)
    r = simular(e, devolver_fluxo=True)
    fator = e["fator_desempenho_real"]
    res = {k: float(v[0]) for k, v in r.items() if k != "fluxo"}
    res.update(
        municipio=str(mun.loc[cod, "municipio"]), kwp=kwp, kwp_recomendado=dim["kwp_recomendado"],
        ger_esp_anual=e["ger_esp_anual"],
        geracao_mensal_kwh=(perfil[cod] * kwp * fator).round(0).tolist(),
        fluxo_acumulado=np.cumsum(r["fluxo"][0]).round(0).tolist(),
    )
    return res


if __name__ == "__main__":
    u = dict(cod_ibge=buscar_municipio("Salvador"), consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=300)
    for fin in (0, 1):
        u["financiado"] = fin
        r = analisar(u)
        print(f"\n== {'Financiado' if fin else 'À vista'} | {r['municipio']} | kWp recomendado: {r['kwp_recomendado']:.0f}")
        for k in ("investimento", "geracao_ano1", "economia_ano1", "cobertura_consumo", "payback",
                  "payback_descontado", "vpl", "tir", "lcoe", "custo_fio_b_ano1"):
            print(f"  {k:20s} {r[k]:>14,.3f}")
