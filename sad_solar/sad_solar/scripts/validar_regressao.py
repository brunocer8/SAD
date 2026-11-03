"""Validação da regressão da geração específica (kWh/kWp.dia) com validação cruzada AGRUPADA POR MUNICÍPIO.

Alvo: `geracao_dia`, simulada com pvlib (ver README: ela aproxima o pvlib, não mede usinas reais).
Preditoras: ghi (kWh/m².dia), fracao_difusa (adimensional), temp_media (°C).
Em cada rodada, 5 grupos de municípios: ajusta OLS em 4/5 dos municípios e mede o erro nos municípios NÃO vistos.
Uso: python scripts/validar_regressao.py   (gera dados/validacao_regressao.csv e imprime o resumo)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "dados"
df = pd.read_csv(D / "dataset_ba_modelo.csv")
X_COLS, Y = ["ghi", "fracao_difusa", "temp_media"], "geracao_dia"


def ajustar(d):
    X = np.column_stack([np.ones(len(d)), d[X_COLS].to_numpy()])
    return np.linalg.lstsq(X, d[Y].to_numpy(), rcond=None)[0]


def prever(b, d):
    return b[0] + d[X_COLS].to_numpy() @ b[1:]


def metricas(y, p):
    e = y - p
    return dict(R2=1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum(), MAE=np.abs(e).mean(),
                RMSE=np.sqrt((e ** 2).mean()), MAPE_pct=100 * np.mean(np.abs(e / y)))


rng = np.random.default_rng(0)
cods = df["cod_ibge"].unique(); rng.shuffle(cods)
folds = np.array_split(cods, 5)
linhas = []
for i, teste in enumerate(folds, 1):
    te = df[df["cod_ibge"].isin(teste)]; tr = df[~df["cod_ibge"].isin(teste)]
    b = ajustar(tr)
    linhas.append(dict(rodada=i, municipios_teste=len(teste), **metricas(te[Y].to_numpy(), prever(b, te))))
res = pd.DataFrame(linhas)
res.to_csv(D / "validacao_regressao.csv", index=False, encoding="utf-8-sig")

b = ajustar(df)
mod = json.load(open(D / "modelo_geracao_linear.json", encoding="utf-8"))
b_arq = np.array([mod["intercepto"]] + [mod["coeficientes"][k] for k in X_COLS])
print("Validação cruzada por município (5 grupos):\n", res.round(4).to_string(index=False))
print("\nMédia:", res[["R2", "MAE", "RMSE", "MAPE_pct"]].mean().round(4).to_dict())
print("\nAjuste em todos os dados:", metricas(df[Y].to_numpy(), prever(b, df)))
print("Coeficientes refeitos :", b.round(4), "\nCoeficientes do arquivo:", b_arq.round(4))
mm = df.assign(p=prever(b_arq, df)).assign(err=lambda x: x[Y] - x["p"]).groupby("mes")["err"].agg(["mean", lambda s: np.abs(s).mean()])
mm.columns = ["vies_medio", "MAE"]; print("\nErro por mês (modelo do arquivo):\n", mm.round(4).to_string())
mun = df.assign(p=prever(b_arq, df)).assign(err=lambda x: np.abs(x[Y] - x["p"])).groupby("cod_ibge")["err"].mean()
print("\nMAE por município: mediana %.4f, máximo %.4f kWh/kWp.dia" % (mun.median(), mun.max()))
