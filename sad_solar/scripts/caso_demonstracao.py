"""Gera docs/CASO_E_VALIDACAO.md com cenário DIDÁTICO e testes de sensibilidade residenciais.
Não lê nem reproduz dados pessoais da conta de luz de qualquer usuário.
Execute: python scripts/caso_demonstracao.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import financeiro as f
import saw

D = Path(__file__).resolve().parents[1] / "docs" / "CASO_E_VALIDACAO.md"
U = dict(cod_ibge=f.buscar_municipio("Salvador"), consumo_mes_kwh=250,
         tarifa_kwh=0.87773, consumo_diurno_fracao=0.45, area_m2=30,
         custo_disponibilidade_kwh_mes=50, tipo_ligacao="bifasica", prioridade="padrao")

r = saw.decisao(U)
dim = f.dimensionar(U)
reco = r["recomendacao"]
view = r["ranking"][reco["indice_exibido"]]

lines = [
    "# Caso de demonstração e validação — Sol da Bahia",
    "",
    "**Aviso:** este é um cenário **HIPOTÉTICO e didático**, não uma medição de energia gerada, ",
    "nem a transcrição de conta de energia privada. O preço de R$ 0,87773/kWh é a referência B1 ",
    "homologada pela Neoenergia Coelba para 22/04/2026–21/04/2027, sem impostos e encargos adicionais. ",
    "O custo de instalação vem da tabela de referência do protótipo, não de orçamento comercial atual.",
    "",
    "## Entradas e restrições",
    "",
    "- Município: **Salvador/BA**; consumo médio: **250 kWh/mês** (3.000 kWh/ano).",
    "- Tarifa B1 convencional: **R$ 0,87773/kWh**, sem tributos; ligação bifásica (mínimo de 50 kWh/mês).",
    "- Área **útil** de telhado: **30 m² hipotéticos**; consumo diurno de 45%; pagamento à vista.",
    f"- Limite geométrico aproximado: **30/7 = {30/7:.2f} kWp**; ",
    f"maior sistema discretizado permitido: **{dim['teto_kwp']:.2f} kWp**, ",
    f"{dim['modulos_max']} módulos de 620 Wp.",
    f"- Sistema de maior VPL do projeto no cenário-base: **{dim['kwp_recomendado']:.2f} kWp**. ",
    "Essa escolha pode não coincidir com a opção de maior nota SAW.",
    "",
    "## Resultado gerado pelo código",
    "",
    f"**Recomendação multicritério:** {reco['nome']}. Motivo: {reco['motivo']}",
    "",
    "| Posição | Alternativa | Nota SAW | VPL do projeto (R$) | Payback do projeto (anos) | Área aproximada (m²) |",
    "|---:|---|---:|---:|---:|---:|",
]
for i, a in enumerate(r["ranking"], 1):
    nota = "—" if a["indice"] is None else f"{a['indice']:.3f}"
    pb = "—" if a["nome"].startswith("Não instalar") else f"{a['payback']:.2f}"
    lines.append(f"| {i} | {a['nome']} | {nota} | {a['vpl_projeto']:,.2f} | {pb} | {a['kwp']*7:.2f} |")

lines += [
    "", "**Interpretação:** a recomendação é consequência dos filtros e dos pesos da análise multicritério, ",
    "não uma promessa de redução real da fatura. Cada cenário usa geração solar simulada e despesas futuras estimadas.",
    "", "## Validação por sensibilidade (recalcular entradas do SAD)", "",
    "| Cenário | Recomendação | Potência exibida (kWp) | VPL exibido (R$) |",
    "|---|---|---:|---:|",
]
casos = [
    ("Cenário-base", {}),
    ("Consumo menor: 150 kWh/mês", {"consumo_mes_kwh": 150}),
    ("Consumo maior: 450 kWh/mês", {"consumo_mes_kwh": 450}),
    ("Custo de instalação maior: R$ 5.200/kWp", {"custo_kwp": 5200}),
    ("Tarifa marginal menor: R$ 0,25/kWh", {"tarifa_kwh": 0.25}),
    ("Área menor: 12 m²", {"area_m2": 12}),
    ("Tarifa Social: limitação simplificada de 80 kWh", {"tarifa_social": True, "tarifa_kwh": 0.74406}),
]
for desc, mods in casos:
    try:
        d = saw.decisao({**U, **mods}, n_mc=120)
        rc = d["recomendacao"]
        x = d["ranking"][rc["indice_exibido"]]
        lines.append(f"| {desc} | {rc['nome']} | {x['kwp']:.2f} | {x['vpl']:,.2f} |")
    except ValueError as exc:
        lines.append(f"| {desc} | Não simulável: {str(exc).replace('|','/')} | — | — |")

lines += [
    "", "## Estratégia de validação frente ao enunciado",
    "", "1. **Validação técnica:** conferir `potência = módulos × 620/1000`, área = `potência × 7` ",
    "e rejeição quando a área comporta menos de dois módulos; comparar saídas com cálculos manuais.",
    "2. **Validação analítica:** executar `python scripts/validar_regressao.py` (cinco grupos por município) ",
    "para obter R²/MAE/RMSE contra **geração simulada**, não produção medida.",
    "3. **Validação da decisão:** comparar a recomendação sob tarifas, custos, consumo e área diferentes; ",
    "testar o caso em que *não instalar* deve vencer (`tests/test_api.py`).",
    "4. **Validação do protótipo:** executar `python -m pytest -q`, cadastrar usuário, simular, ",
    "ver ranking, histórico e exportar CSV.",
    "", "## Limitações que precisam aparecer no relatório acadêmico",
    "", "- Telhado e custo estimados; sem vistoria estrutural, sombreamento ou proposta de instalador.",
    "- Tarifa homologada B1 sem tributos, enquanto contas reais incluem regras adicionais; ",
    "o cenário Tarifa Social usa simplificação, não cálculo regulatório completo.",
    "- Regressão com alvo **simulado pelo pvlib**, não dados medidos de instalações reais.",
    "- Consumo residencial sem sazonalidade nem curva de carga horária; autoconsumo é estimado.",
    "- Fio B de 2029+ modelado como cenário de 100%, não como percentual fixado diretamente pela lei.",
    "- Não comparar VPL projetado com projeções de outros softwares sem uniformizar hipóteses.",
]
D.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Gerado {D}")
print(f"Recomendação do caso didático: {reco['nome']}")
