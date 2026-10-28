"""Testes do SAD Solar. Rodar: pytest -q   (na pasta sad_solar)"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import financeiro as f
import saw
from parametros import padroes

COD = f.buscar_municipio("Salvador")
BASE = dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, consumo_diurno_fracao=0.6)


# ---------------------------------------------------------------- referência independente (python puro, 1 cenário)
def ref_anos(e, n_anos):
    """Referência independente (python puro): balanço mensal com créditos FIFO de validade 60 meses.
    Devolve lista por ano de (autoconsumo, compensada, injetada, expirada, saldo_final)."""
    mun, perfil = f.carregar_municipios()
    share = perfil[COD] / perfil[COD].sum()
    lotes = []          # lista de [mes_origem, kwh]
    mes = 0
    out = []
    for ano in range(n_anos):
        S = comp = inj_t = exp = 0.0
        for m in range(12):
            g = e["kwp"] * e["ger_esp_anual"] * e["fator_desempenho_real"] * share[m] * (1 - e["degradacao_anual"]) ** ano
            s = min(e["simultaneidade"] * g, e["consumo_diurno_fracao"] * e["consumo_mes_kwh"])
            inj = g - s
            need = max(e["consumo_mes_kwh"] - s - e["custo_disponibilidade_kwh_mes"], 0)
            exp += sum(l[1] for l in lotes if mes - l[0] >= 60)
            lotes = [l for l in lotes if mes - l[0] < 60]
            lotes.append([mes, inj])
            uso = 0.0
            for l in lotes:                                  # mais antigos primeiro
                x = min(l[1], need - uso)
                l[1] -= x; uso += x
            S += s; comp += uso; inj_t += inj; mes += 1
        out.append((S, comp, inj_t, exp, sum(l[1] for l in lotes)))
    return out


def test_balanco_energetico_confere_com_referencia():
    e = f.montar_entrada(BASE, 20.0)
    r = f.simular(e)
    S, comp, inj, exp, saldo = ref_anos(e, 1)[0]
    assert r["autoconsumo_ano1"][0] == pytest.approx(S)
    assert r["compensada_ano1"][0] == pytest.approx(comp)
    assert r["injetada_ano1"][0] == pytest.approx(inj)
    assert r["credito_acumulado_ano1"][0] == pytest.approx(saldo)
    assert r["geracao_ano1"][0] == pytest.approx(S + inj)


def test_expiracao_de_creditos_60_meses_confere_com_referencia():
    """Sistema grande para consumo pequeno: sobra crédito, que expira após 60 meses (comparação com a referência em laços)."""
    u = {**BASE, "consumo_mes_kwh": 500}
    e = f.montar_entrada(u, 40.0)
    r = f.simular(e)
    ref = ref_anos(e, 25)
    assert r["credito_expirado_total"][0] > 0                             # há expiração de fato
    assert r["credito_expirado_total"][0] == pytest.approx(sum(x[3] for x in ref))
    assert r["credito_expirado_ano1"][0] == 0                             # nada expira antes de 60 meses


def test_simultaneidade_menor_reduz_autoconsumo_e_aumenta_injecao():
    e = f.montar_entrada({**BASE, "consumo_mes_kwh": 4000}, 12.0)
    a = f.simular({**e, "simultaneidade": 1.0}); b = f.simular({**e, "simultaneidade": 0.6})
    assert b["autoconsumo_ano1"][0] < a["autoconsumo_ano1"][0]
    assert b["injetada_ano1"][0] > a["injetada_ano1"][0]


def test_financiamento_cronograma_e_amortizacao():
    """Prazo TOTAL = 12 anos (144 meses) incluindo 6 de carência -> 138 parcelas; saldo zera; parcelas conferem com cálculo independente."""
    e = f.montar_entrada({**BASE, "financiado": 1}, 20.0)
    r = f.simular(e, True)
    inv = r["investimento"][0]; F = inv * (1 - e["entrada_pct"])
    im = (1 + e["taxa_financiamento"]) ** (1 / 12) - 1
    car, n = int(e["carencia_meses"]), int(e["prazo_financiamento_anos"] * 12) - int(e["carencia_meses"])
    assert n == 138
    saldo = F * (1 + im) ** car
    pmt = saldo * im / (1 - (1 + im) ** -n)
    total_pago = 0.0
    for _ in range(n):
        saldo = saldo * (1 + im) - pmt; total_pago += pmt
    assert abs(saldo) < 1e-6                                              # amortização completa
    assert r["parcelas_ano1"][0] == pytest.approx(pmt * 6)               # 6 parcelas no 1º ano (após 6 meses de carência)
    e0 = f.simular({**e, "financiado": 0.0}, True)
    # diferença de fluxos (financiado - à vista) = empréstimo em t=0 menos todas as parcelas
    dif = r["fluxo"][0] - e0["fluxo"][0]
    assert dif[0] == pytest.approx(F) and -dif[1:].sum() == pytest.approx(total_pago)
    assert (r["fluxo"][0][13:] == pytest.approx(e0["fluxo"][0][13:]))     # sem parcelas após o mês 144 (ano 12 em diante)


def test_vpl_projeto_igual_nas_duas_formas_de_pagamento():
    a = f.simular(f.montar_entrada({**BASE, "financiado": 0}, 20.0)); b = f.simular(f.montar_entrada({**BASE, "financiado": 1}, 20.0))
    assert a["vpl_projeto"][0] == pytest.approx(b["vpl_projeto"][0]) == pytest.approx(a["vpl"][0])
    assert b["payback_projeto"][0] == pytest.approx(a["payback"][0])


def test_payback_primeiro_cruzamento():
    full = np.array([[-100.0, 60.0, 60.0, -50.0, 80.0, 80.0],     # cruza em 1,67; depois volta a negativo
                     [-100.0, 10.0, 10.0, 10.0, 10.0, 10.0],      # nunca recupera
                     [50.0, 10.0, 10.0, 10.0, 10.0, 10.0]])       # já começa positivo
    pb = f._payback(full)
    assert pb[0] == pytest.approx(1 + 40 / 60)
    assert np.isnan(pb[1]) and pb[2] == 0.0


def test_area_zero_ou_negativa_e_rejeitada():
    with pytest.raises(ValueError):
        f.dimensionar({**BASE, "area_m2": 0})
    with pytest.raises(ValueError):
        f.dimensionar({**BASE, "area_m2": -5})


def test_dimensionamento_independe_do_flag_financiado():
    a = f.dimensionar({**BASE, "financiado": 0, "area_m2": 300})["kwp_recomendado"]
    b = f.dimensionar({**BASE, "financiado": 1, "area_m2": 300})["kwp_recomendado"]
    assert a == b


def test_conservacao_de_energia_e_creditos_nao_negativos():
    for kwp in (3, 10, 34, 75):
        e = f.montar_entrada(BASE, float(kwp)); r = f.simular(e)
        assert r["credito_acumulado_ano1"][0] >= -1e-9
        # tudo que foi gerado é autoconsumo, compensado ou fica como crédito
        assert r["geracao_ano1"][0] == pytest.approx(r["autoconsumo_ano1"][0] + r["injetada_ano1"][0])
        assert r["compensada_ano1"][0] <= r["injetada_ano1"][0] + 1e-9
        assert 0 <= r["cobertura_consumo"][0] <= 1 + 1e-9


def test_vpl_a_vista_confere_com_calculo_manual():
    """VPL recomputado a partir do fluxo (investimento em t=0) com a taxa de desconto."""
    e = f.montar_entrada({**BASE, "financiado": 0}, 20.0)
    r = f.simular(e, devolver_fluxo=True)
    fluxo = r["fluxo"][0]
    assert fluxo[0] == pytest.approx(-r["investimento"][0])          # investimento entra como saída em t=0
    vpl = sum(v / (1 + e["taxa_desconto"]) ** t for t, v in enumerate(fluxo))
    assert r["vpl"][0] == pytest.approx(vpl)


def test_area_insuficiente_nao_gera_alternativa():
    with pytest.raises(f.AreaInsuficiente):
        f.dimensionar({**BASE, "area_m2": 15})
    t = f.dimensionar({**BASE, "area_m2": 70})
    assert t["teto_kwp"] == 10 and t["tabela"]["kwp"].max() <= 10


def test_limite_de_potencia_75kwp():
    t = f.dimensionar({**BASE, "consumo_mes_kwh": 30000})
    assert t["tabela"]["kwp"].max() <= 75


# ---------------------------------------------------------------- SAW / decisão
def test_pesos_roc_somam_um_e_seguem_a_ordem():
    w = saw.PESO_FATOR
    assert sum(c[3] for c in saw.CRITERIOS) == pytest.approx(1.0)
    assert w["1) Retorno econômico"] == pytest.approx(0.5208333) and w["4) Risco econômico"] == pytest.approx(0.0625)
    assert list(w.values()) == sorted(w.values(), reverse=True)


def test_normalizacao_empate_e_sentidos():
    alts = [dict(vpl_projeto=1, payback=2, ganho_fin=0, exposicao_reg=.1, cobertura=.5, sem_divida=1, risco_prejuizo=0, vpl_p10=1),
            dict(vpl_projeto=3, payback=4, ganho_fin=0, exposicao_reg=.3, cobertura=.5, sem_divida=1, risco_prejuizo=0, vpl_p10=3)]
    M = saw.matriz_normalizada(alts)
    ids = [c[0] for c in saw.CRITERIOS]
    assert M[:, ids.index("cobertura")].tolist() == [1.0, 1.0]            # todos iguais -> 1
    assert M[:, ids.index("vpl_projeto")].tolist() == [0.0, 1.0]                  # ganho
    assert M[:, ids.index("payback")].tolist() == [1.0, 0.0]              # custo


def test_agrupamento_hierarquico():
    idx = np.array([0.90, 0.88, 0.60, 0.58, 0.20])
    g = saw.agrupar_indices(idx, 0.05)
    assert [sorted(x) for x in g] == [[0, 1], [2, 3], [4]]
    assert len(saw.agrupar_indices(idx, 1.0)) == 1 and len(saw.agrupar_indices(idx, 0.0)) == 5


def test_caso_viavel_recomenda_instalar_e_ranking_so_com_aprovadas():
    d = saw.decisao({**BASE, "area_m2": 300})
    rec = d["recomendacao"]
    assert rec["tipo"] == "instalar"
    for a in d["ranking"]:
        if a["indice"] is not None:
            assert a["nome"] == saw.NAO_INSTALAR or a["veredito"]["nivel"] != "nao"
        else:
            assert a["veredito"]["nivel"] == "nao" and a["grupo"] == -1


def test_nao_instalar_pode_ser_a_recomendacao():
    """Tarifa baixa, consumo pequeno e consumo noturno: nenhuma instalação passa no filtro."""
    d = saw.decisao({**BASE, "consumo_mes_kwh": 300, "tarifa_kwh": 0.30, "consumo_diurno_fracao": 0.1})
    assert d["recomendacao"]["tipo"] == "nao_instalar"
    assert d["ranking"][0]["nome"] == saw.NAO_INSTALAR
    assert d["recomendacao"]["n_aprovadas"] == 0


def test_alternativa_reprovada_nunca_e_recomendada():
    d = saw.decisao({**BASE, "consumo_mes_kwh": 600, "tarifa_kwh": 0.45, "consumo_diurno_fracao": 0.3})
    rec = d["recomendacao"]
    escolhida = next(a for a in d["ranking"] if a["nome"] == rec["nome"])
    assert escolhida["nome"] == saw.NAO_INSTALAR or escolhida["veredito"]["nivel"] != "nao"


def test_veredito_usa_payback_do_projeto():
    """O veredito usa o payback do PROJETO (investimento integral), não o recuperação da entrada do financiado."""
    res = dict(vpl=1e5, cobertura_consumo=1.0, fluxo_acumulado=[-1e3, 5e3])
    risco = dict(prob_vpl_positivo=1.0, prob_vpl_positivo_financiado=1.0,
                 payback_projeto=dict(mediana=9.0), payback_capital_proprio=dict(mediana=0.1))
    assert saw.veredito(res, risco, 1)["nivel"] == "ressalvas"           # financiado: payback do capital próprio curto não mascara 9 anos do projeto
    assert saw.veredito(res, risco, 0)["nivel"] == "ressalvas"


def test_taxa_de_desconto_e_custo_mudam_o_vpl_no_sentido_esperado():
    e = f.montar_entrada(BASE, 20.0)
    v0 = f.simular(e)["vpl"][0]
    assert f.simular({**e, "taxa_desconto": 0.20})["vpl"][0] < v0
    assert f.simular({**e, "fator_custo": 1.5})["vpl"][0] < v0
    assert f.simular({**e, "tarifa_kwh": 0.5})["vpl"][0] < v0


def test_unica_alternativa_nao_gera_indice_absoluto():
    d = saw.decisao({**BASE, "consumo_mes_kwh": 300, "tarifa_kwh": 0.30, "consumo_diurno_fracao": 0.1})
    assert d["ranking"][0]["indice"] is None


def test_alavancagem_nao_premia_sistema_maior():
    d = saw.decisao({**BASE, "area_m2": 300, "taxa_financiamento": 0.079})
    fin = [a["ganho_fin"] for a in d["ranking"] if a["financiado"] and a["kwp"] > 0]
    assert fin and max(fin) - min(fin) < 1e-6


def test_sem_taxa_informada_so_ha_alternativas_a_vista():
    d = saw.decisao({**BASE, "consumo_mes_kwh": 4889, "tarifa_kwh": 0.90, "area_m2": 300})
    assert not d["com_financiamento"] and all(a["financiado"] == 0 for a in d["ranking"])
    ids = [c["id"] for c in d["criterios"]]
    assert len(ids) == 6 and "ganho_fin" not in ids and "sem_divida" not in ids
    assert sum(c["peso"] for c in d["criterios"]) == pytest.approx(1.0)


def test_taxa_de_financiamento_alta_prefere_a_vista():
    for tx in (0.2404, 0.3036):                                       # BB: 1,81% a.m. e CET de 30,36% a.a.
        d = saw.decisao({**BASE, "consumo_mes_kwh": 4889, "tarifa_kwh": 0.90, "area_m2": 300, "taxa_financiamento": tx})
        assert d["recomendacao"]["tipo"] == "nao_instalar" or "à vista" in d["recomendacao"]["nome"]


def test_economia_limitada_ao_consumo_faturavel_acima_do_minimo():
    """Consumo igual ao custo de disponibilidade (100 kWh): o autoconsumo não reduz a fatura mínima -> economia zero."""
    e = f.montar_entrada({**BASE, "consumo_mes_kwh": 100}, 3.0)
    assert f.simular(e)["economia_ano1"][0] == pytest.approx(0.0, abs=1e-6)
    e2 = f.montar_entrada({**BASE, "consumo_mes_kwh": 150}, 3.0)
    r = f.simular(e2)
    teto = (150 - e2["custo_disponibilidade_kwh_mes"]) * 12 * e2["tarifa_kwh"]
    assert 0 < r["economia_ano1"][0] <= teto + 1e-6


def test_prioridades_do_decisor_mudam_a_recomendacao():
    u = {**BASE, "consumo_mes_kwh": 4889, "tarifa_kwh": 0.90, "area_m2": 300}
    nomes = {p: saw.decisao({**u, "prioridade": p})["recomendacao"]["nome"] for p in saw.PRIORIDADES}
    assert len(set(nomes.values())) > 1
    for p in saw.PRIORIDADES:
        assert sum(saw.pesos_criterios(p)) == pytest.approx(1.0)


def test_perfil_kmeans_atribui_grupo():
    import perfis
    g = perfis.atribuir(4889, 0.90, 0.6, 1.0)
    assert g is not None and 1 <= g["indice"] <= 4 and 0 <= g["prob_vpl_positivo"] <= 1


def test_kmeans_separa_grupos_obvios():
    import perfis
    rng = np.random.default_rng(0)
    X = np.vstack([rng.normal(0, .1, (50, 2)), rng.normal(5, .1, (50, 2))])
    C, lab, _ = perfis.kmeans(X, 2)
    assert len(set(lab[:50])) == 1 and len(set(lab[50:])) == 1 and lab[0] != lab[-1]
