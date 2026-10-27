"""
Monte Carlo, classificação da faixa de retorno e análise de risco do SAD solar.

Duas formas de usar a incerteza:
  1. analisar_risco(): para UM cliente, sorteia os parâmetros incertos (tarifa futura, custo,
     desempenho real, taxa de desconto...) e devolve probabilidades e percentis.
  2. gerar_cenarios() + treinar(): sorteia milhares de clientes e cenários, rotula cada um pela
     faixa de retorno e treina árvore de decisão / Random Forest.

PAPEL NO SISTEMA: o classificador (árvore de decisão / Random Forest) é um EXPERIMENTO OFFLINE de mineração
de dados (python montecarlo.py treinar). Ele NÃO participa da recomendação do SAD, e as classes foram criadas
a partir de cortes de payback escolhidos pelo autor sobre cenários sintéticos: a acurácia mede a capacidade de
reproduzir esses rótulos, não de prever PMEs reais. As funções analíticas que alimentam a decisão são a regressão
(geração), a sumarização (indicadores e Monte Carlo) e o agrupamento (ver saw.py).

ACHADO IMPORTANTE (declarar no trabalho): com as premissas atuais, praticamente 100% dos
cenários de PME têm VPL > 0 e payback descontado inferior a 5 anos. Um rótulo absoluto
"viável / inviável" não tem variação para ser aprendido. Por isso a classificação descreve a
FAIXA DE RETORNO do projeto (payback simples À VISTA), com cortes de negócio escolhidos pelo
autor depois de observar a distribuição dos cenários:

    Retorno rápido : VPL > 0 e payback <= LIMITE_RAPIDO anos
    Retorno médio  : VPL > 0 e payback entre LIMITE_RAPIDO e LIMITE_MEDIO anos
    Retorno lento  : VPL > 0 e payback acima de LIMITE_MEDIO anos
    Inviável       : VPL <= 0 ou o investimento não se paga na vida útil

A forma de pagamento (à vista x financiado) é uma decisão separada, comparada pelo VPL.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from financeiro import (buscar_municipio, carregar_municipios, custo_kwp_tabela, dimensionar, montar_entrada,
                        perfil_sazonal, simular)
from parametros import PARAMETROS, UNIVERSO_PME, padroes

LIMITE_RAPIDO = 1.5   # anos (payback simples, à vista)
LIMITE_MEDIO = 2.0    # anos
CLASSES = ["Inviável", "Retorno lento", "Retorno médio", "Retorno rápido"]

# colunas guardadas em cada cenário (para rastreio); só FEATURES entra no classificador
COLUNAS_CENARIO = [
    "razao_ger_consumo", "consumo_mes_kwh", "tarifa_kwh", "ger_esp_anual", "kwp", "custo_kwp_efetivo",
    "reajuste_tarifa", "taxa_desconto", "consumo_diurno_fracao", "fator_desempenho_real",
    "om_pct_investimento", "fio_b_share_tarifa",
]
# Variáveis independentes do classificador (4): determinantes do payback simples = investimento / economia anual
FEATURES = ["tarifa_kwh", "razao_ger_consumo", "custo_kwp_efetivo", "ger_esp_anual"]


def _amostrar(dist, n, rng):
    tipo = dist[0]
    if tipo == "tri":
        return rng.triangular(dist[1], dist[2], dist[3], n)
    if tipo == "uni":
        return rng.uniform(dist[1], dist[2], n)
    if tipo == "uni_int":
        return rng.integers(dist[1], dist[2] + 1, n).astype(float)
    raise ValueError(tipo)


def incertezas(n: int, rng) -> dict:
    """Parâmetros com distribuição (arrays de tamanho n) + os demais fixos nos padrões."""
    e = padroes()
    for k, v in PARAMETROS.items():
        if v["mc"] is not None:
            e[k] = _amostrar(v["mc"], n, rng)
    return e


def rotular(vpl, payback) -> np.ndarray:
    """Índice em CLASSES: 0 inviável, 1 lento, 2 médio, 3 rápido (payback simples, à vista)."""
    pb = np.where(np.isnan(payback), np.inf, payback)
    rot = np.zeros(len(vpl), dtype=int)
    rot[(vpl > 0) & np.isfinite(pb)] = 1
    rot[(vpl > 0) & (pb <= LIMITE_MEDIO)] = 2
    rot[(vpl > 0) & (pb <= LIMITE_RAPIDO)] = 3
    return rot


# ------------------------------------------------------------------ base de cenários
def gerar_cenarios(n: int = 20000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    mun, perfis = carregar_municipios()
    cods = rng.choice(mun.index.to_numpy(), n)
    sazonal = {c: perfil_sazonal(p) for c, p in perfis.items()}
    ger = mun.loc[cods, "ger_esp_anual"].to_numpy()
    lo, hi = UNIVERSO_PME["consumo_mes_kwh"]
    consumo = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
    tarifa = rng.uniform(*UNIVERSO_PME["tarifa_kwh"], n)
    cobertura = rng.uniform(*UNIVERSO_PME["cobertura_alvo"], n)

    e = incertezas(n, rng)
    kwp = np.clip(consumo * 12 * cobertura / (ger * PARAMETROS["fator_desempenho_real"]["padrao"]),
                  UNIVERSO_PME["kwp_min"], PARAMETROS["kwp_max"]["padrao"])
    e.update(kwp=kwp, ger_esp_anual=ger, consumo_mes_kwh=consumo, tarifa_kwh=tarifa,
             perfil=np.array([sazonal[c] for c in cods]))
    r = simular({**e, "financiado": 0.0})   # à vista
    rf = simular({**e, "financiado": 1.0})  # financiado

    df = pd.DataFrame({k: np.broadcast_to(np.asarray(e[k], dtype=float), (n,)) for k in COLUNAS_CENARIO
                       if k not in ("razao_ger_consumo", "custo_kwp_efetivo")})
    df.insert(0, "cod_ibge", cods)
    df["taxa_financiamento"] = e["taxa_financiamento"]
    df["razao_ger_consumo"] = kwp * ger / (consumo * 12)
    df["custo_kwp_efetivo"] = custo_kwp_tabela(kwp) * e["fator_custo"]
    for k in ("investimento", "vpl", "tir", "payback", "payback_descontado", "lcoe", "cobertura_consumo"):
        df[k] = r[k]
    df["vpl_financiado"] = rf["vpl"]
    df["melhor_pagamento"] = np.where(rf["vpl"] > r["vpl"], "Financiado", "À vista")
    df["classe"] = np.array(CLASSES)[rotular(r["vpl"], r["payback"])]
    return df


# ------------------------------------------------------------------ risco de um cliente
def analisar_risco(usuario: dict, kwp: float | None = None, n: int = 2000, seed: int = 7) -> dict:
    """Mantém o cliente fixo (município, consumo, tarifa, kWp) e sorteia as incertezas.
    Avalia o projeto à vista (faixa de retorno) e compara com o financiado."""
    rng = np.random.default_rng(seed)
    kwp = float(kwp if kwp is not None else dimensionar(usuario)["kwp_recomendado"])
    e = incertezas(n, rng)
    e.update({k: v for k, v in usuario.items() if k in PARAMETROS})  # o que o usuário fixou vale
    base = montar_entrada(usuario, kwp)
    for k in ("kwp", "ger_esp_anual", "consumo_mes_kwh", "perfil"):
        e[k] = base[k]
    r = simular({**e, "financiado": 0.0})
    rf = simular({**e, "financiado": 1.0})
    cls = rotular(r["vpl"], r["payback"])
    q = lambda x, p: float(np.nanpercentile(x, p)) if np.isfinite(x).any() else float("nan")
    return dict(
        kwp=kwp, n_cenarios=n,
        prob_vpl_positivo=float((r["vpl"] > 0).mean()),
        prob_vpl_positivo_financiado=float((rf["vpl"] > 0).mean()),
        prob_classe={c: float((cls == i).mean()) for i, c in enumerate(CLASSES)},
        vpl_a_vista=dict(p10=q(r["vpl"], 10), mediana=q(r["vpl"], 50), p90=q(r["vpl"], 90)),
        vpl_financiado=dict(p10=q(rf["vpl"], 10), mediana=q(rf["vpl"], 50), p90=q(rf["vpl"], 90)),
        prob_financiado_melhor=float((rf["vpl"] > r["vpl"]).mean()),
        payback_a_vista=dict(p10=q(r["payback"], 10), mediana=q(r["payback"], 50), p90=q(r["payback"], 90)),
        # payback_a_vista = payback do PROJETO (investimento integral). Recuperação do capital próprio: só a entrada e as parcelas.
        payback_projeto=dict(p10=q(r["payback_projeto"], 10), mediana=q(r["payback_projeto"], 50), p90=q(r["payback_projeto"], 90)),
        payback_capital_proprio=dict(p10=q(rf["payback"], 10), mediana=q(rf["payback"], 50), p90=q(rf["payback"], 90)),
        vpl_projeto=dict(p10=q(r["vpl_projeto"], 10), mediana=q(r["vpl_projeto"], 50), p90=q(r["vpl_projeto"], 90)),
        payback_descontado=dict(p10=q(r["payback_descontado"], 10), mediana=q(r["payback_descontado"], 50),
                                p90=q(r["payback_descontado"], 90)),
        tir_mediana=q(r["tir"], 50),
    )


# ------------------------------------------------------------------ classificador
def treinar(n: int = 20000, seed: int = 42, saida: str = "modelos"):
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier, export_text

    out = Path(__file__).parent / saida
    out.mkdir(exist_ok=True)
    df = gerar_cenarios(n, seed)
    df.sample(min(5000, n), random_state=1).to_csv(out / "cenarios_amostra.csv", index=False, encoding="utf-8-sig")
    print("Distribuição das classes:\n", df["classe"].value_counts(normalize=True).round(3).to_string())

    X, y = df[FEATURES], df["classe"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    modelos = {
        "Árvore de decisão (profundidade 4)": DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, random_state=seed),
        "Random Forest": RandomForestClassifier(n_estimators=150, min_samples_leaf=5, random_state=seed, n_jobs=-1),
    }
    linhas = []
    for nome, m in modelos.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xte)
        linhas.append(dict(modelo=nome, acuracia=accuracy_score(yte, pred), f1_macro=f1_score(yte, pred, average="macro")))
        print(f"\n== {nome}\n", classification_report(yte, pred, digits=3))
        print(pd.DataFrame(confusion_matrix(yte, pred, labels=CLASSES), index=CLASSES, columns=CLASSES))
    pd.DataFrame(linhas).to_csv(out / "metricas_classificador.csv", index=False, encoding="utf-8-sig")

    arv = modelos["Árvore de decisão (profundidade 4)"]
    (out / "regras_arvore.txt").write_text(export_text(arv, feature_names=FEATURES), encoding="utf-8")
    imp = pd.Series(modelos["Random Forest"].feature_importances_, index=FEATURES).sort_values(ascending=False)
    imp.to_csv(out / "importancia_classificador.csv", header=["importancia"], encoding="utf-8-sig")
    print("\nImportância (Random Forest):\n", imp.round(3).head(8).to_string())
    joblib.dump(arv, out / "classificador_arvore.joblib")
    return df, pd.DataFrame(linhas)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "treinar":
        treinar()
    else:
        u = dict(cod_ibge=buscar_municipio("Salvador"), consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=300, financiado=0)
        print(analisar_risco(u))
