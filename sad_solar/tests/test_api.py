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
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=250, tarifa_kwh=0.25,area_m2=30,
                                                      consumo_diurno_fracao=0.1))
    assert r.status_code == 200
    d = r.json()
    assert d["resultado"]["decisao"]["recomendacao"]["tipo"] == "nao_instalar"
    assert c.get("/api/simulacoes", headers=h).json()[0]["classe"] == "Não instalar"


def test_area_insuficiente_retorna_422():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=8))
    assert r.status_code == 422 and "área" in r.json()["detail"].lower()


def test_area_zero_retorna_422():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=0))
    assert r.status_code == 422


def test_custo_informado_pela_api():
    h = _h()
    r = c.post("/api/analisar", headers=h, json=dict(cod_ibge=COD, consumo_mes_kwh=4000, tarifa_kwh=1.10, area_m2=300, custo_kwp=5200))
    assert r.status_code == 200
    res = r.json()["resultado"]
    assert res["investimento"] == res["kwp"] * 5200 or abs(res["investimento"] - res["kwp"] * 5200) < 1


def test_area_obrigatoria_e_ligacao():
    h=_h()
    sem_area=c.post("/api/analisar",headers=h,json=dict(cod_ibge=COD,consumo_mes_kwh=250,tarifa_kwh=0.87773))
    assert sem_area.status_code==422
    mono=c.post("/api/analisar",headers=h,json=dict(cod_ibge=COD,consumo_mes_kwh=250,tarifa_kwh=0.87773,
                                                     area_m2=30,tipo_ligacao="monofasica"))
    assert mono.status_code==200
    assert mono.json()["entrada"]["custo_disponibilidade_kwh_mes"]==30
    assert mono.json()["resultado"]["area_informada_m2"]==30


def test_tarifa_social_api_sinaliza_entrada():
    h=_h()
    res=c.post("/api/analisar",headers=h,json=dict(cod_ibge=COD,consumo_mes_kwh=169,tarifa_kwh=0.74406,
                                                   area_m2=30,tipo_ligacao="bifasica",tarifa_social=True))
    assert res.status_code==200
    assert res.json()["entrada"]["tarifa_social"] is True


def test_historico_exibe_recomendacao_e_nao_apenas_faixa_financeira():
    h = _h()
    c.post("/api/analisar", headers=h, json=dict(
        cod_ibge=COD, consumo_mes_kwh=250, tarifa_kwh=0.25,
        area_m2=30, consumo_diurno_fracao=0.1))
    historico = c.get("/api/simulacoes", headers=h).json()
    assert historico[0]["decisao_resumo"] == "Não instalar"
    assert "resultado" not in historico[0]  # não enviar objetos pesados para a listagem


def test_explicacao_automatica_usa_recomendacao_e_nao_vaza_pessoais(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    h = _h()
    req = dict(cod_ibge=COD, consumo_mes_kwh=250, tarifa_kwh=0.25,
               area_m2=30, consumo_diurno_fracao=0.1)
    sim = c.post('/api/analisar', headers=h, json=req)
    assert sim.status_code == 200
    sid = sim.json()['id']
    assert sim.json()['resultado']['decisao']['recomendacao']['tipo'] == 'nao_instalar'
    r = c.get(f'/api/simulacoes/{sid}/explicacao', headers=h)
    assert r.status_code == 200
    assert r.json()['fonte'] == 'automatico'
    assert 'não instalar' in r.json()['texto'].lower()
    assert 'apenas para comparação' in r.json()['texto'].lower()
    assert c.get(f'/api/simulacoes/{sid}/explicacao').status_code == 401
    assert c.get('/api/simulacoes/999999/explicacao', headers=h).status_code == 404


def test_explicacao_por_ia_eh_cacheada_e_nunca_envia_credenciais(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'chave_teste_nao_real')
    h = _h()
    sim = c.post('/api/analisar', headers=h, json=dict(
        cod_ibge=COD, consumo_mes_kwh=250, tarifa_kwh=0.87773, area_m2=30))
    assert sim.status_code == 200
    sid = sim.json()['id']
    chamadas=[]
    texto_ia = ('O modelo recomenda instalar apenas nas condições simuladas. '
                'O investimento e o retorno dependem das premissas. '
                'Antes de contratar, consulte um profissional para vistoria e orçamento.')
    class Resposta:
        def raise_for_status(self): pass
        def json(self):
            return {'candidates':[{'content':{'parts':[{'text':texto_ia}]}}]}
    def falso_post(url, **kw):
        chamadas.append((url,kw))
        return Resposta()
    monkeypatch.setattr(appmod.requests, 'post', falso_post)
    primeiro=c.get(f'/api/simulacoes/{sid}/explicacao',headers=h)
    segundo=c.get(f'/api/simulacoes/{sid}/explicacao',headers=h)
    assert primeiro.status_code==200 and primeiro.json()==segundo.json()
    assert primeiro.json()['fonte']=='gemini' and len(chamadas)==1
    prompt=chamadas[0][1]['json']['contents'][0]['parts'][0]['text']
    assert 'senha123' not in prompt and 'teste_sad' not in prompt and 'chave_teste_nao_real' not in prompt


def test_explicacao_ia_indisponivel_tem_fallback(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'chave_teste_nao_real')
    h=_h()
    sim=c.post('/api/analisar',headers=h,json=dict(cod_ibge=COD,consumo_mes_kwh=250,tarifa_kwh=0.87773,area_m2=30))
    sid=sim.json()['id']
    def falhar(*args, **kwargs):
        raise appmod.requests.Timeout('Fora do ar')
    monkeypatch.setattr(appmod.requests,'post',falhar)
    r=c.get(f'/api/simulacoes/{sid}/explicacao',headers=h)
    assert r.status_code==200 and r.json()['fonte']=='automatico'
    assert 'Sol da Bahia' in r.json()['texto'] or 'SAD recomenda' in r.json()['texto']
