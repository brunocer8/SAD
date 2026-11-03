"""Agrupamento de PERFIS de PME (função analítica de mineração de dados: agrupamento).

Treino offline (python perfis.py): k-means (implementação própria em numpy, 10 inicializações) sobre cenários sintéticos de PME
gerados pelo Monte Carlo, usando APENAS variáveis de entrada do perfil: log10(consumo), tarifa, fração diurna e razão
geração/consumo do sistema dimensionado. Cada grupo é descrito pelos resultados históricos simulados (P(VPL>0), payback mediano).
Em produção, o caso do usuário é atribuído ao centróide mais próximo; se o grupo tem alta taxa de inviabilidade, o veredito
ganha uma ressalva (resultado decisório). Os grupos vêm de cenários simulados, não de PMEs reais.
"""
import json
from pathlib import Path

import numpy as np

ARQ = Path(__file__).parent / "modelos" / "perfis_kmeans.json"
FEATS = ["log_consumo", "tarifa_kwh", "consumo_diurno_fracao", "razao_ger_consumo"]
LIM_INVIAVEL = 0.30   # grupo com mais de 30% de cenários inviáveis gera ressalva


def _x(consumo, tarifa, diurno, razao):
    return np.column_stack([np.log10(consumo), tarifa, diurno, np.minimum(razao, 1.5)])


def kmeans(X, k, seed=0, n_init=10, it=100):
    rng = np.random.default_rng(seed)
    melhor = None
    for _ in range(n_init):
        C = X[rng.choice(len(X), k, replace=False)]
        for _ in range(it):
            lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
            N = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(N, C):
                break
            C = N
        inercia = ((X - C[lab]) ** 2).sum()
        if melhor is None or inercia < melhor[0]:
            melhor = (inercia, C, lab)
    return melhor[1], melhor[2], melhor[0]


def treinar(n=6000, k=4):
    from montecarlo import gerar_cenarios
    df = gerar_cenarios(n, seed=3)
    X = _x(df.consumo_mes_kwh, df.tarifa_kwh, df.consumo_diurno_fracao, df.razao_ger_consumo)
    mu, sd = X.mean(0), X.std(0)
    C, lab, _ = kmeans((X - mu) / sd, k)
    grupos = []
    for j in range(k):
        d = df[lab == j]; c = C[j] * sd + mu
        nome = (f"{'consumo alto' if c[0] > mu[0] else 'consumo baixo'}, {'tarifa alta' if c[1] > mu[1] else 'tarifa baixa'}, "
                f"{'perfil diurno' if c[2] > mu[2] else 'perfil menos diurno'}")
        grupos.append(dict(nome=nome, centroide=[float(v) for v in c], n=int(len(d)),
                           prob_vpl_positivo=float((d.vpl > 0).mean()), payback_mediano=float(d.payback.median()),
                           consumo_mediano=float(d.consumo_mes_kwh.median())))
    ARQ.write_text(json.dumps(dict(features=FEATS, media=mu.tolist(), desvio=sd.tolist(), grupos=grupos), ensure_ascii=False, indent=1), encoding="utf-8")
    return grupos


def atribuir(consumo, tarifa, diurno, razao):
    """Devolve o grupo (dict) mais próximo do caso, ou None se o modelo não foi treinado."""
    if not ARQ.exists():
        return None
    m = json.loads(ARQ.read_text(encoding="utf-8"))
    mu, sd = np.array(m["media"]), np.array(m["desvio"])
    z = (_x(np.array([consumo]), np.array([tarifa]), np.array([diurno]), np.array([razao]))[0] - mu) / sd
    cs = (np.array([g["centroide"] for g in m["grupos"]]) - mu) / sd
    j = int(np.argmin(((cs - z) ** 2).sum(1)))
    return dict(indice=j + 1, **m["grupos"][j])


if __name__ == "__main__":
    for i, g in enumerate(treinar(), 1):
        print(i, g["nome"], f"n={g['n']} P(VPL>0)={g['prob_vpl_positivo']:.0%} payback mediano={g['payback_mediano']:.1f}")
