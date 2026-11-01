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
    for detail_id in ("comparacao", "graficos", "metodologia"):
        assert not next(a for a in doc.details if a.get("id") == detail_id).get("open")


def test_relatorio_preserva_impressao_e_historico():
    doc = Inputs()
    doc.feed(HTML)
    assert {"rt", "csv", "det", "dbody"} <= doc.ids
    assert "imprimirRelatorio()" in HTML
