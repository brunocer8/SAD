"""
Modelo de decisão do SAD Solar: filtro de admissibilidade -> ranking multicritério (SAW) -> agrupamento.

Etapas (nesta ordem):

  1. ALTERNATIVAS. Três tamanhos de sistema (recomendado, compacto, ampliado) x pagamento à vista, e também financiado SOMENTE
     se o decisor informar a taxa de financiamento (CET a.a.); sem taxa, não há alternativa financiada e os critérios
     "alavancagem" e "sem endividamento" ficam com peso 0 + a alternativa "Não instalar". Os tamanhos já respeitam as restrições TÉCNICAS
     (potência <= 75 kWp da microgeração, Lei 14.300/2022; área de telhado). Se a área não comporta o sistema
     mínimo, não há alternativa de instalação (financeiro.AreaInsuficiente).
  2. FILTROS. (a) Viabilidade: VPL > 0 e probabilidade de VPL positivo >= LIM_PROB_MIN.
     (b) Dominância econômica nos perfis padrão e retorno: não recomendar uma instalação que custe
     mais, tenha VPL menor e payback maior que outra, com cobertura e risco no mínimo equivalentes.
     As opções dominadas continuam visíveis, mas não disputam o ranking. No perfil cautela,
     uma preferência explícita de menor risco permite considerar também a diferença na dependência de créditos.
  3. RANKING SAW (Hwang e Yoon, 1981) entre as alternativas aprovadas + "Não instalar". Índice
     S_i = soma_j(w_j * r_ij), com r_ij normalizado por min-max (critério de ganho: (x-min)/(max-min); de
     custo: (max-x)/(max-min); se todas empatam, r_ij = 1). Pesos: ordem de preferência dos quatro fatores
     convertida em pesos pelo método ROC (Barron e Barrett, 1996); dentro de cada fator, o ROC também
     segue a ordem dos indicadores (ex.: VPL antes de payback).
     Na opção padrão, retorno econômico > risco financeiro > adequação à demanda > dependência de compensação.
     Em cada fator, a literatura orienta a ordem dos indicadores e o ROC calcula os pesos dos critérios ativos.
  4. SENSIBILIDADE DOS PESOS. Cada peso é multiplicado por U(0,7; 1,3), renormalizado, e o ranking é refeito
     N vezes. Resultado: desvio-padrão do índice de cada alternativa e frequência com que cada uma lidera.
  5. AGRUPAMENTO (função analítica de mineração de dados). Agrupamento hierárquico aglomerativo,
     ligação completa, sobre o índice SAW (1 dimensão), com distância de corte DELTA = raiz(2) x média dos
     desvios-padrão da etapa 4: duas alternativas só ficam no mesmo grupo se a diferença entre os índices (e
     entre todos os pares do grupo) é menor que o ruído causado por incerteza nos pesos.
  6. RECOMENDAÇÃO = alternativa de maior índice (posição 1), que pode ser "Não instalar".

O índice SAW é RELATIVO ao conjunto de alternativas (normalização min-max): incluir ou excluir alternativas pode mudar o ranking;
não é nota absoluta de viabilidade. O corte do agrupamento é uma heurística do projeto; por isso também se informa, para cada
alternativa, a frequência com que o líder a supera nos sorteios de pesos. A ordem de preferência dos fatores é uma escolha assumida
(a validar com o decisor), não algo "descoberto" pelo ROC.

VPL e payback do critério são os do PROJETO (sem financiamento), comparáveis entre tamanhos e formas de pagamento; o efeito do
financiamento entra em "valor da alavancagem por R$ financiado" (VPL do capital próprio - VPL do projeto, dividido pelo valor financiado, para não premiar sistemas maiores só por terem mais dívida) e em "sem endividamento".

Observação metodológica: o custo do Fio B em R$ NÃO é critério, pois já está descontado no fluxo de caixa (e portanto no VPL).
O critério de exposição regulatória é apenas uma proxy: parcela da economia do primeiro ano que depende de créditos
compensados, NÃO probabilidade de alteração legal ou risco medido. No perfil padrão, não se sobrepõe ao veto de
substituições economicamente dominadas. A regra de dominância não é parte do cálculo SAW, mas filtro explícito anterior.
Limitação conhecida: a normalização min-max amplia diferenças pequenas entre alternativas; por isso a sensibilidade dos pesos
(etapa 4) e a frequência de liderança são exibidas junto da recomendação.

Premissas do projeto (não vêm de norma): pesos de preferência entre fatores, LIM_PROB_MIN, LIM_PROB, LIM_PAYBACK,
LIM_COBERTURA, amplitude de 30% na sensibilidade. Todas estão nas constantes abaixo.
"""
import numpy as np

from financeiro import MODULO_WP, MODULOS_MIN, AreaInsuficiente, analisar, dimensionar  # noqa: F401  (AreaInsuficiente reexportada)
from montecarlo import analisar_risco

from parametros import PARAMETROS

# id, nome, fator, peso (preenchido abaixo), sentido
CRITERIOS = [
    ("vpl_projeto", "VPL do projeto em 25 anos (R$), sem financiamento", "Retorno econômico", 0, "max"),
    ("payback", "Payback do projeto (anos; sem retorno = pior valor)", "Retorno econômico", 0, "min"),
    ("ganho_fin", "Valor da alavancagem por R$ financiado: (VPL do capital próprio - VPL do projeto) / valor financiado", "Retorno econômico", 0, "max"),
    ("exposicao_reg", "Dependência da compensação: parcela da economia do 1º ano associada a créditos de energia", "Dependência da compensação", 0, "min"),
    ("cobertura", "Cobertura do consumo (autossuficiência)", "Adequação ao consumo", 0, "max"),
    ("sem_divida", "Sem endividamento (0 ou 1)", "Adequação ao consumo", 0, "max"),
    ("risco_prejuizo", "Probabilidade de prejuízo, VPL <= 0 (Monte Carlo, fluxo da própria alternativa)", "Risco econômico", 0, "min"),
    ("vpl_p10", "VPL no cenário pessimista, percentil 10 (R$, fluxo da própria alternativa)", "Risco econômico", 0, "max"),
]
# Prioridade substantiva documentada: VPL e payback (rentabilidade), incerteza, atendimento da demanda,
# e por último dependência de compensação — o efeito de Fio B já está no fluxo de caixa.
# A literatura fundamenta a ordem e os indicadores, NÃO percentuais universais de preferências.
# Pesos ROC da ordenação assumida pelo projeto: 52,08%; 27,08%; 14,58%; 6,25%.
_FAT = ["Retorno econômico", "Risco econômico", "Adequação ao consumo", "Dependência da compensação"]
PESO_FATOR = {f: sum(1 / j for j in range(i, len(_FAT) + 1)) / len(_FAT) for i, f in enumerate(_FAT, 1)}
CRITERIOS = [(c[0], c[1], c[2], 0.0, c[4]) for c in CRITERIOS]
FATORES = list(_FAT)

# A ordem no perfil padrão é uma hipótese transparente do projeto para o morador que deseja investir.
# Cada perfil expressa prioridades declaradas pelo decisor; não são pesos extraídos empiricamente da literatura.
PRIORIDADES = {
    "padrao": ["Retorno econômico", "Risco econômico", "Adequação ao consumo", "Dependência da compensação"],
    "retorno": ["Retorno econômico", "Adequação ao consumo", "Risco econômico", "Dependência da compensação"],
    "cautela": ["Risco econômico", "Retorno econômico", "Dependência da compensação", "Adequação ao consumo"],
}

# Ordem intrafator orientada pela avaliação de investimento: VPL representa valor agregado ao longo da
# vida útil; payback informa liquidez/tempo de recuperação, mas ignora fluxos após o retorno.
# Quando há financiamento, a alavancagem é secundária à rentabilidade do projeto.
# Para risco, o P10 discrimina a magnitude de perdas/ganhos em cenários desfavoráveis; a chance de
# VPL positivo é complementar (e pode empatar em 100% para várias opções).
ORDEM_CRITERIOS = {
    "Retorno econômico": ["vpl_projeto", "payback", "ganho_fin"],
    "Risco econômico": ["vpl_p10", "risco_prejuizo"],
    "Adequação ao consumo": ["cobertura", "sem_divida"],
    "Dependência da compensação": ["exposicao_reg"],
}


def roc(n: int) -> list[float]:
    """Rank Order Centroid (Barron e Barrett, 1996) para n critérios hierarquicamente ordenados."""
    return [sum(1 / j for j in range(i, n + 1)) / n for i in range(1, n + 1)]


CRIT_FINANCIAMENTO = ("ganho_fin", "sem_divida")   # só existem se o decisor informar uma taxa de financiamento


def pesos_criterios(prioridade: str = "padrao", com_fin: bool = True) -> list[float]:
    """ROC hierárquico: ordena os fatores e, dentro de cada um, ordena os critérios ativos.

    A importância substantiva é uma premissa declarada; ROC transforma ordenação ordinal em pesos
    cardinais reproduzíveis, sem afirmar que a literatura impôs percentuais específicos.
    """
    ordem = PRIORIDADES.get(prioridade, PRIORIDADES["padrao"])
    pesos_fatores = dict(zip(ordem, roc(len(ordem))))
    ativo = {c[0] for c in CRITERIOS if com_fin or c[0] not in CRIT_FINANCIAMENTO}
    internos = {}
    for fator, prioridades in ORDEM_CRITERIOS.items():
        ids = [cid for cid in prioridades if cid in ativo]
        internos.update({cid: peso for cid, peso in zip(ids, roc(len(ids)))})
    return [pesos_fatores[c[2]] * internos[c[0]] if c[0] in ativo else 0.0 for c in CRITERIOS]


# Referência de pesos quando os critérios de financiamento estão ativos (exibição/compatibilidade).
CRITERIOS = [(c[0], c[1], c[2], w, c[4]) for c, w in zip(CRITERIOS, pesos_criterios())]

# --- filtro de viabilidade e vereditos (premissas do autor)
LIM_PROB_MIN = 0.50   # abaixo disso a alternativa é descartada
LIM_PROB, LIM_PAYBACK, LIM_COBERTURA = 0.90, 8.0, 0.75  # abaixo/acima disso: "recomendado com ressalvas"
AMPLITUDE_PESOS, N_SENS = 0.30, 1000

VIDA = PARAMETROS["vida_util_anos"]["padrao"]
KWP_MAX = PARAMETROS["kwp_max"]["padrao"]
NAO_INSTALAR = "Não instalar (manter a conta atual)"


# ------------------------------------------------------------------ filtro / veredito
def veredito(res: dict, risco: dict, fin: int) -> dict:
    """Classifica a alternativa: não recomendada (reprova no filtro) / com ressalvas / recomendada."""
    prob = risco["prob_vpl_positivo_financiado" if fin else "prob_vpl_positivo"]
    motivos = []
    if res["vpl"] <= 0:
        motivos.append("o VPL no cenário-base é negativo ou nulo")
    if prob < LIM_PROB_MIN:
        motivos.append(f"o VPL só é positivo em {prob:.0%} dos cenários simulados (mínimo exigido: {LIM_PROB_MIN:.0%})")
    if motivos:
        return dict(classe="Não recomendado no cenário atual", nivel="nao", ressalvas=motivos)
    r = []
    if res["cobertura_consumo"] < LIM_COBERTURA:
        r.append(f"o sistema cobre {res['cobertura_consumo']:.0%} do consumo; o restante continua sendo comprado da distribuidora")
    if prob < LIM_PROB:
        r.append(f"em {1 - prob:.0%} dos cenários simulados o VPL é negativo")
    # payback da PRÓPRIA alternativa: à vista = retorno do investimento total; financiado = retorno do capital próprio
    pb = risco["payback_projeto"]["mediana"]       # payback do PROJETO (investimento integral), igual para as duas formas de pagamento
    rotulo = "do projeto (investimento integral)"
    if pb != pb or pb > LIM_PAYBACK:
        r.append(f"o retorno {rotulo} passa de {LIM_PAYBACK:.0f} anos (mediana dos cenários)")
    fl = res["fluxo_acumulado"]
    if fin and len(fl) > 1 and fl[1] - fl[0] < 0:
        r.append("o fluxo de caixa do capital próprio no 1º ano é negativo (parcelas e O&M superam a economia)")
    return dict(classe="Recomendado com ressalvas" if r else "Recomendado", nivel="ressalvas" if r else "sim", ressalvas=r)


def aplicar_dominancia_economica(aprovadas: list[dict], prioridade: str) -> tuple[list[dict], list[dict]]:
    """Filtro de dominância ECONÔMICA para prioridades padrão/retorno, sem falsificar o índice SAW.

    Uma alternativa A é economicamente dominada por B quando B custa pelo menos R$ 1 menos,
    tem VPL superior em ao menos R$ 1, payback menor por pelo menos 0,01 ano, cobertura
    equivalente/superior (tolerância de arredondamento 0,1 pp) e risco de prejuízo e VPL P10
    no mínimo equivalentes (tolerância 1 pp e R$ 1). Compara alternativas com mesma modalidade
    de pagamento; a alternativa "Não instalar" nunca participa desta triagem.

    No perfil de cautela, não excluímos opções: o decisor pode aceitar pior relação financeira
    em troca de menor dependência da compensação de créditos. A decisão continua transparente.
    """
    if prioridade == "cautela":
        return aprovadas, []
    mantidas, dominadas = [], []
    for a in aprovadas:
        dominadora = next((b for b in aprovadas if b is not a
            and b["financiado"] == a["financiado"]
            and b["investimento"] < a["investimento"] - 1.0
            and b["vpl_projeto"] > a["vpl_projeto"] + 1.0
            and b["payback"] < a["payback"] - 0.01
            and b["cobertura"] >= a["cobertura"] - 0.001
            and b["risco_prejuizo"] <= a["risco_prejuizo"] + 0.01
            and b["vpl_p10"] >= a["vpl_p10"] - 1.0), None)
        if dominadora is None:
            mantidas.append(a)
        else:
            a["dominada_por"] = dominadora["nome"]
            a["veredito"] = dict(
                classe="Não priorizada no perfil econômico",
                nivel="dominada",
                ressalvas=[
                    f"{dominadora['nome']} custa menos, possui maior VPL, payback menor, "
                    "cobertura semelhante e risco financeiro não superior. "
                    "A dependência de créditos pode ser diferente; compare o perfil de cautela para outra prioridade."
                ],
            )
            dominadas.append(a)
    return mantidas, dominadas


# ------------------------------------------------------------------ SAW
def matriz_normalizada(alts: list[dict]) -> np.ndarray:
    """Matriz r_ij (alternativas x critérios), normalização min-max. NaN vira o pior valor do critério."""
    M = np.zeros((len(alts), len(CRITERIOS)))
    for j, (cid, _, _, _, sentido) in enumerate(CRITERIOS):
        v = np.array([a[cid] for a in alts], dtype=float)
        ok = np.isfinite(v)
        if not ok.all():
            v = np.where(ok, v, (v[ok].min() if sentido == "max" else v[ok].max()) if ok.any() else 0.0)
        lo, hi = v.min(), v.max()
        M[:, j] = 1.0 if hi == lo else ((v - lo) / (hi - lo) if sentido == "max" else (hi - v) / (hi - lo))
    return M


def pesos(prioridade: str = "padrao", com_fin: bool = True) -> np.ndarray:
    return np.array(pesos_criterios(prioridade, com_fin))


def sensibilidade_pesos(M: np.ndarray, n: int = N_SENS, amp: float = AMPLITUDE_PESOS, seed: int = 11, prioridade: str = "padrao", com_fin: bool = True) -> dict:
    """Refaz o ranking com pesos perturbados (w_j x U(1-amp, 1+amp), renormalizados)."""
    rng = np.random.default_rng(seed)
    W = pesos(prioridade, com_fin)[None, :] * rng.uniform(1 - amp, 1 + amp, (n, M.shape[1]))
    W /= W.sum(axis=1, keepdims=True)
    I = W @ M.T                                   # n x alternativas
    lider = I.argmax(axis=1)
    return dict(desvio=I.std(axis=0), freq_lider=np.bincount(lider, minlength=M.shape[0]) / n, I=I)


def agrupar_indices(indices: np.ndarray, delta: float) -> list[list[int]]:
    """Agrupamento hierárquico aglomerativo (ligação completa) de valores 1-D.
    Funde, a cada passo, os dois grupos vizinhos de menor diâmetro; para quando o diâmetro excede `delta`.
    Retorna listas de posições, do grupo de maior índice para o de menor."""
    ordem = list(np.argsort(-np.asarray(indices)))
    grupos = [[i] for i in ordem]
    while len(grupos) > 1:
        diam = [indices[grupos[k][0]] - indices[grupos[k + 1][-1]] for k in range(len(grupos) - 1)]
        k = int(np.argmin(diam))
        if diam[k] > delta:
            break
        grupos[k:k + 2] = [grupos[k] + grupos[k + 1]]
    return grupos


def ranquear(alts: list[dict], prioridade: str = "padrao", com_fin: bool = True) -> tuple[list[dict], float]:
    """Calcula índice SAW, atributos por fator, sensibilidade e grupos. Retorna (alts ordenadas, delta)."""
    M, W = matriz_normalizada(alts), pesos(prioridade, com_fin)
    idx = M @ W
    sens = sensibilidade_pesos(M, prioridade=prioridade, com_fin=com_fin)
    delta = float(np.sqrt(2) * sens["desvio"].mean())
    for i, a in enumerate(alts):
        a["indice"] = float(idx[i])
        a["prob_lider"] = float(sens["freq_lider"][i])
        a["desvio_indice"] = float(sens["desvio"][i])
        a["atributos"] = {f: 100 * sum(W[j] * M[i, j] for j, c in enumerate(CRITERIOS) if c[2] == f)
                          / sum(W[j] for j, c in enumerate(CRITERIOS) if c[2] == f) for f in FATORES}
    lid = int(np.argmax(idx))
    for i, a in enumerate(alts):                     # frequência com que o líder supera cada alternativa nos sorteios de pesos
        a["prob_lider_supera"] = float((sens["I"][:, lid] > sens["I"][:, i]).mean()) if i != lid else None
    grupos = agrupar_indices(idx, delta)
    g = len(grupos)
    for gi, gr in enumerate(grupos, 1):
        rot = ("Mais recomendado" if len(gr) == 1 else "Mais recomendados (índices dentro do ruído dos pesos)") if gi == 1 else \
              ("Menos indicados" if (gi == g and g >= 3) else "Alternativas competitivas")
        for i in gr:
            alts[i]["grupo"], alts[i]["rotulo"] = gi, rot
    alts.sort(key=lambda a: -a["indice"])
    for k, a in enumerate(alts, 1):
        a["posicao"] = k
    return alts, delta


# ------------------------------------------------------------------ decisão completa
def _alternativa(nome, k, fin, usuario, n_mc):
    u = {**usuario, "financiado": fin}
    r = analisar(u, kwp=k)
    rk = analisar_risco(u, kwp=k, n=n_mc)
    vp = rk["vpl_financiado" if fin else "vpl_a_vista"]
    prob = rk["prob_vpl_positivo_financiado" if fin else "prob_vpl_positivo"]
    alt = dict(
        nome=f"Sistema {nome.lower()} de {k:.2f} kWp, {'financiado' if fin else 'à vista'}", kwp=k, financiado=fin,
        vpl=r["vpl"], vpl_projeto=r["vpl_projeto"], ganho_fin=(r["vpl"] - r["vpl_projeto"]) / (r["investimento"] * (1 - PARAMETROS["entrada_pct"]["padrao"])) if fin else 0.0,
        payback=r["payback_projeto"] if r["payback_projeto"] == r["payback_projeto"] else float(VIDA), fio_b=r["custo_fio_b_ano1"],
        exposicao_reg=r["exposicao_regulatoria"], cobertura=r["cobertura_consumo"], sem_divida=0 if fin else 1,
        risco_prejuizo=1 - prob, vpl_p10=vp["p10"], investimento=r["investimento"], res=r, risco=rk,
        veredito=veredito(r, rk, fin))
    if fin and r["vpl"] <= r["vpl_projeto"]:      # dominada: a mesma instalação à vista rende mais que financiada
        alt["veredito"] = dict(classe="Não recomendado no cenário atual", nivel="nao",
                               ressalvas=["a taxa de financiamento informada é maior que o retorno do capital: financiar rende menos que pagar à vista"])
    return alt


def decisao(usuario: dict, n_mc: int = 1000) -> dict:
    com_fin = bool(usuario.get("taxa_financiamento"))   # financiamento só entra se o decisor informar a taxa (CET)
    prio = usuario.get("prioridade", "padrao")
    dim = dimensionar(usuario)                      # levanta AreaInsuficiente se não houver sistema admissível
    rec, teto = dim["kwp_recomendado"], dim["teto_kwp"]
    # Alternativas em números inteiros de módulos, nunca superando a área.
    n_rec = max(MODULOS_MIN, int(round(rec * 1000 / MODULO_WP)))
    n_teto = int(round(teto * 1000 / MODULO_WP))
    numeros, vistos = [], set()
    for nome, n in (("Recomendado", n_rec), ("Compacto", max(MODULOS_MIN, n_rec - 1)),
                    ("Ampliado", min(n_teto, n_rec + 1))):
        if n not in vistos:
            vistos.add(n)
            numeros.append((nome, float(n * MODULO_WP / 1000)))
    tamanhos = numeros
    todas = [_alternativa(nome, k, fin, usuario, n_mc) for nome, k in tamanhos for fin in ((0, 1) if com_fin else (0,))]
    viaveis = [a for a in todas if a["veredito"]["nivel"] != "nao"]
    reprovadas = [a for a in todas if a["veredito"]["nivel"] == "nao"]
    aprovadas, dominadas = aplicar_dominancia_economica(viaveis, prio)

    nao = dict(nome=NAO_INSTALAR, kwp=0.0, financiado=0, vpl=0.0, vpl_projeto=0.0, ganho_fin=0.0, payback=float(VIDA), fio_b=0.0, exposicao_reg=0.0,
               cobertura=0.0, sem_divida=1, risco_prejuizo=0.0, vpl_p10=0.0, investimento=0.0)
    com_fin = any(a["financiado"] for a in aprovadas)   # critérios de financiamento só pesam se houver alternativa financiada viável
    ranking, delta = ranquear(aprovadas + [nao], prio, com_fin)
    for a in reprovadas + dominadas:                # mostradas para comparação, mas sem índice SAW
        rot = ("Não priorizada: dominância econômica" if a in dominadas
               else "Descartada pelo filtro de viabilidade")
        a.update(indice=None, atributos={}, grupo=-1, rotulo=rot,
                 posicao=None, prob_lider=0.0, desvio_indice=None)
    ranking = ranking + dominadas + reprovadas

    if not aprovadas:                                 # único elemento: índice 1,0 seria artefato da normalização (sem comparação)
        ranking[0]["indice"] = None
    # O agrupamento de consumidores sintéticos de PME foi desativado nesta versão residencial.
    # Permanecem ativos o agrupamento das ALTERNATIVAS SAW e a análise de sensibilidade dos pesos.
    perfil = None
    melhor = ranking[0]
    com_res = [a for a in ranking if a.get("res")]
    exibida = com_res[0] if aprovadas else max(com_res, key=lambda a: a["vpl"])   # cenário mostrado nos gráficos
    empate = [a["nome"] for a in ranking if a.get("grupo") == 1 and a is not melhor]
    if melhor["nome"] == NAO_INSTALAR:
        motivo = ("Nenhuma alternativa de instalação passou nos filtros de viabilidade e preferência econômica." if not aprovadas else
                  "No ranking multicritério, manter a conta atual superou as alternativas de instalação admissíveis.")
        recomendacao = dict(tipo="nao_instalar", nome=NAO_INSTALAR, indice=melhor["indice"], motivo=motivo)
    else:
        motivo = (f"Maior índice SAW entre {len(aprovadas)} alternativa(s) admissível(is) e a opção de não instalar. "
                  "O perfil considera VPL e payback, risco financeiro, adequação à demanda e dependência de compensação "
                  "na ordem escolhida pelo usuário, com pesos ROC.")
        if dominadas:
            motivo += (f" {len(dominadas)} alternativa(s) economicamente dominada(s) não disputaram o ranking "
                       "no perfil de retorno e viabilidade; continuam visíveis para comparação.")
        recomendacao = dict(tipo="instalar", nome=melhor["nome"], indice=melhor["indice"], motivo=motivo)
    if usuario.get("area_m2") is None:
        recomendacao["motivo"] += " Atenção: a área do telhado não foi informada; o espaço físico não limitou o dimensionamento (teto técnico apenas por potência)."
    if usuario.get("custo_kwp"):
        recomendacao["motivo"] += f" Custo de instalação informado pelo decisor: R$ {usuario['custo_kwp']:,.0f}/kWp (tratado como fixo no Monte Carlo)."
    recomendacao.update(empate_tecnico=empate, prob_lider=melhor["prob_lider"], indice_exibido=next(i for i, a in enumerate(ranking) if a is exibida),
                        n_aprovadas=len(aprovadas), n_reprovadas=len(reprovadas), n_dominadas=len(dominadas))
    return dict(criterios=[dict(id=c[0], nome=c[1], fator=c[2], peso=w, sentido=c[4]) for c, w in zip(CRITERIOS, pesos_criterios(prio, com_fin)) if w > 0],
                prioridade=prio, perfil=perfil, com_financiamento=com_fin,
                ranking=ranking, delta=delta, recomendacao=recomendacao,
                filtro=dict(prob_min=LIM_PROB_MIN,
                            regra="VPL > 0 e probabilidade de VPL positivo >= mínimo",
                            dominancia_economica_ativa=prio in ("padrao", "retorno"),
                            regra_dominancia="Custo menor, VPL maior, payback menor, cobertura e risco não inferiores"))
