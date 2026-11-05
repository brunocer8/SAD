"""As informações acadêmicas permanecem acessíveis, mas não poluem a tela principal."""
from pathlib import Path
from html.parser import HTMLParser

HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.details = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            assert a["id"] not in self.ids, f"ID HTML duplicado: {a['id']}"
            self.ids.add(a["id"])
        if tag == "details":
            self.details.append(a)


def test_simulacao_inclui_campos_essenciais_e_detalhes_opcionais():
    doc = Inputs()
    doc.feed(HTML)
    assert {"mun", "cons", "area", "form-advanced", "f"} <= doc.ids
    assert not next(a for a in doc.details if a.get("id") == "form-advanced").get("open")
    assert "Orçamento real (R$/kWp)" in HTML


def test_resultado_preserva_comparacao_analise_e_modelo_de_decisao():
    doc = Inputs()
    doc.feed(HTML)
    assert {"veredito", "kpis", "comparacao", "graficos", "metodologia", "metodo", "decisao", "risco"} <= doc.ids
    assert "Não instalar" in HTML
    assert "Regressão" in HTML and "Sumarização" in HTML and "Agrupamento" in HTML
    # As alternativas são o elemento de escolha em destaque, e não um acordeão escondido.
    assert "Garagem solar" in HTML
    assert "escolhaHTML(D,sel)" in HTML
    assert "solar-choice" in HTML
    assert {"option-inspector", "deck-prev", "deck-next", "opcao-titulo"} <= doc.ids
    assert all(a.get("id") != "comparacao" for a in doc.details)
    for detail_id in ("graficos", "metodologia"):
        assert not next(a for a in doc.details if a.get("id") == detail_id).get("open")


def test_relatorio_preserva_impressao_e_historico():
    doc = Inputs()
    doc.feed(HTML)
    assert {"rt", "csv", "det", "dbody"} <= doc.ids
    assert "imprimirRelatorio()" in HTML


def test_graficos_retorno_apresentam_tooltip_em_reais():
    assert 'function tooltipRetorno()' in HTML
    assert HTML.count('options:tooltipRetorno()') == 2  # Painel e Simulação
    assert 'Saldo acumulado:' in HTML and 'pt-BR' in HTML
    assert 'pointHoverRadius:6' in HTML


def test_interpretacao_ia_estah_visivel_e_recuperavel_no_relatorio():
    doc=Inputs();doc.feed(HTML)
    assert {'explicacao','explicacao-fonte','explicacao-texto'} <= doc.ids
    assert 'carregarExplicacao(d.id' in HTML
    assert '/explicacao`' in HTML
    assert 'id="rel-explicacao-texto"' in HTML
    assert 'd.fonte==="gemini"' in HTML


def test_garagem_diferencia_ordem_visual_de_ranking_saw():
    """O índice SAW e o índice real da opção não mudam por ordenação de cartões."""
    assert 'function alternativasParaExibicao(D)' in HTML
    assert 'alternativasParaExibicao(D).map(({a,i})=>' in HTML
    assert 'onclick="selecionar(${i},true)"' in HTML
    assert 'VIÁVEL · NÃO PRIORIZADA' in HTML
    assert 'Não atribuído' in HTML
    assert 'REFERÊNCIA · NÃO INSTALAR' in HTML
    assert 'Esta ordem visual não substitui o ranking SAW' in HTML


def test_ordenacao_visual_casos_recomendado_e_nao_instalar():
    """Testa a função JS de apresentação com índices originais preservados."""
    import shutil
    import subprocess
    import pytest

    if not shutil.which('node'):
        pytest.skip('Node não instalado; validação JS de ordenação opcional')
    inicio = HTML.index('function alternativasParaExibicao(D){')
    fim = HTML.index('\nfunction escolhaHTML(D,sel){', inicio)
    funcao_js = HTML[inicio:fim]
    script = '''const assert=require('node:assert/strict');
''' + funcao_js + '''
const d={recomendacao:{nome:'1,86'}, ranking:[
  {nome:'1,86', res:{}, veredito:{nivel:'sim'},indice:.94},
  {nome:'1,24', res:{}, veredito:{nivel:'sim'},indice:.71},
  {nome:'Não instalar', indice:.13},
  {nome:'2,48', res:{}, veredito:{nivel:'dominada'}, indice:null},
  {nome:'3,10', res:{}, veredito:{nivel:'nao'}, indice:null},
]};
let ordered=alternativasParaExibicao(d);
assert.deepEqual(ordered.map(x=>x.a.nome), ['1,86','1,24','2,48','Não instalar','3,10']);
assert.deepEqual(ordered.map(x=>x.i), [0,1,3,2,4]);
assert.equal(d.ranking[2].nome,'Não instalar');
assert.equal(d.ranking[2].indice,.13);
const d2={recomendacao:{nome:'Não instalar'},ranking:[
  {nome:'Não instalar',indice:.9},
  {nome:'2,48',res:{},veredito:{nivel:'nao'},indice:null},
]};
assert.deepEqual(alternativasParaExibicao(d2).map(x=>x.a.nome),['Não instalar','2,48']);
const d3={recomendacao:{nome:'1,86'},ranking:[
  {nome:'Não instalar'},
  {nome:'1,24',res:{},veredito:{nivel:'ressalvas'}},
  {nome:'1,86',res:{},veredito:{nivel:'sim'}},
  {nome:'2,48',res:{},veredito:{nivel:'dominada'}},
]};
assert.deepEqual(alternativasParaExibicao(d3).map(x=>x.a.nome), ['1,86','1,24','2,48','Não instalar']);
'''
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
