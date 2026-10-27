"""Teste ponta a ponta da API (cadastro -> simulação -> relatório). Rodar: pytest -q"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "teste.db")
from fastapi.testclient import TestClient
import app as appmod
import financeiro as f

c = TestClient(appmod.app)
COD = f.buscar_municipio("Salvador")


def _h():
    r = c.post("/api/registrar", json={"nome": "teste_sad", "senha": "senha123"})
    if r.status_code == 409:
        r = c.post("/api/login", json={"nome": "teste_sad", "senha": "senha123"})
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_fluxo_completo_instalar():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=300))
    assert r.status_code == 200
    d = r.json(); rec = d["resultado"]["decisao"]["recomendacao"]
    assert rec["tipo"] == "instalar" and d["resultado"]["vpl"] > 0
    assert c.get(f"/api/simulacoes/{d['id']}", headers=h).json()["resultado"]["decisao"]["recomendacao"]["nome"] == rec["nome"]


def test_fluxo_completo_nao_instalar():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=300, tarifa_kwh=0.30,
                                                      consumo_diurno_fracao=0.1))
    assert r.status_code == 200
    d = r.json()
    assert d["resultado"]["decisao"]["recomendacao"]["tipo"] == "nao_instalar"
    assert c.get("/api/simulacoes", headers=h).json()[0]["classe"] == "Não instalar"


def test_area_insuficiente_retorna_422():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=10))
    assert r.status_code == 422 and "área" in r.json()["detail"].lower()


def test_area_zero_retorna_422():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=0))
    assert r.status_code == 422
