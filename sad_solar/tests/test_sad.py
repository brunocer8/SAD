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
def ref_ano(e, ano_idx, saldo):
    """Reimplementa o balanço mensal com laços simples; devolve (S, comp, inj, saldo_final) do ano `ano_idx` (0 = ano 1)."""
    mun, perfil = f.carregar_municipios()
    share = perfil[COD] / perfil[COD].sum()
    S = comp = inj_t = 0.0
    for m in range(12):
        g = e["kwp"] * e["ger_esp_anual"] * e["fator_desempenho_real"] * share[m] * (1 - e["degradacao_anual"]) ** ano_idx
        s = min(g, e["consumo_diurno_fracao"] * e["consumo_mes_kwh"])
        inj = g - s
        need = max(e["consumo_mes_kwh"] - s - e["custo_disponibilidade_kwh_mes"], 0)
        uso = min(saldo + inj, need)
        saldo += inj - uso
        S += s; comp += uso; inj_t += inj
    return S, comp, inj_t, saldo


def test_balanco_energetico_confere_com_referencia():
    e = f.montar_entrada(BASE, 20.0)
    r = f.simular(e)
    S, comp, inj, saldo = ref_ano(e, 0, 0.0)
    assert r["autoconsumo_ano1"][0] == pytest.approx(S)
    assert r["compensada_ano1"][0] == pytest.approx(comp)
    assert r["injetada_ano1"][0] == pytest.approx(inj)
    assert r["credito_acumulado_ano1"][0] == pytest.approx(saldo)
    assert r["geracao_ano1"][0] == pytest.approx(S + inj)


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


def test_financiamento_fluxo_comparavel_ao_a_vista():
    """No financiado, t=0 é só a entrada e o capital financiado não vira receita: soma das parcelas > valor financiado."""
    e0 = f.montar_entrada({**BASE, "financiado": 0}, 20.0); e1 = f.montar_entrada({**BASE, "financiado": 1}, 20.0)
    r0, r1 = f.simular(e0, True), f.simular(e1, True)
    inv = r0["investimento"][0]
    assert r1["fluxo"][0][0] == pytest.approx(-inv * e1["entrada_pct"])
    dif = (r1["fluxo"][0] - r0["fluxo"][0])                          # financiado - à vista
    assert dif[0] == pytest.approx(inv * (1 - e1["entrada_pct"]))     # recebe o empréstimo em t=0
    assert -dif[1:].sum() > inv * (1 - e1["entrada_pct"])             # paga mais do que recebeu (juros > 0)


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
    assert w["1) Teórica"] == pytest.approx(0.5208333) and w["4) Modelos preditivos"] == pytest.approx(0.0625)
    assert list(w.values()) == sorted(w.values(), reverse=True)


def test_normalizacao_empate_e_sentidos():
    alts = [dict(vpl=1, payback=2, exposicao_reg=.1, cobertura=.5, sem_divida=1, risco_prejuizo=0, vpl_p10=1),
            dict(vpl=3, payback=4, exposicao_reg=.3, cobertura=.5, sem_divida=1, risco_prejuizo=0, vpl_p10=3)]
    M = saw.matriz_normalizada(alts)
    ids = [c[0] for c in saw.CRITERIOS]
    assert M[:, ids.index("cobertura")].tolist() == [1.0, 1.0]            # todos iguais -> 1
    assert M[:, ids.index("vpl")].tolist() == [0.0, 1.0]                  # ganho
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


def test_veredito_financiado_usa_payback_do_financiado():
    res = dict(vpl=1e5, cobertura_consumo=1.0, fluxo_acumulado=[-1e3, 5e3])
    risco = dict(prob_vpl_positivo=1.0, prob_vpl_positivo_financiado=1.0,
                 payback_a_vista=dict(mediana=9.0), payback_financiado=dict(mediana=1.0))
    assert saw.veredito(res, risco, 0)["nivel"] == "ressalvas"           # à vista: 9 anos > 5
    assert saw.veredito(res, risco, 1)["nivel"] == "sim"                 # financiado: 1 ano, sem ressalva


def test_taxa_de_desconto_e_custo_mudam_o_vpl_no_sentido_esperado():
    e = f.montar_entrada(BASE, 20.0)
    v0 = f.simular(e)["vpl"][0]
    assert f.simular({**e, "taxa_desconto": 0.20})["vpl"][0] < v0
    assert f.simular({**e, "fator_custo": 1.5})["vpl"][0] < v0
    assert f.simular({**e, "tarifa_kwh": 0.5})["vpl"][0] < v0
