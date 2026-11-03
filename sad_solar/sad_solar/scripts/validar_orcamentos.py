"""Comparação EXPLORATÓRIA do SAD com estimativas comerciais (não é validação empírica). Gera docs/validacao_orcamentos.md.
Dados: dados/orcamentos_neosolar.csv (NeoSolar, 1 fornecedor) + 2 calculadoras (Portal Solar, WEG). Uso: python scripts/validar_orcamentos.py"""
import os, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import numpy as np, pandas as pd
import financeiro as f

COD = f.buscar_municipio("Salvador")
neo = pd.read_csv(os.path.join(RAIZ, "dados", "orcamentos_neosolar.csv"))
mun, perfil = f.carregar_municipios()
ger_modelo_mes = float(perfil[COD].sum() / 12)          # kWh/kWp.mês antes do fator de desempenho
FDES = 0.95
ger_sad = ger_modelo_mes * FDES                         # kWh/kWp.mês usado no SAD (1º ano)

def simula(kwp, consumo, tarifa, invest=None, reaj=0.06, fdes=FDES, perda=None):
    e = f.montar_entrada(dict(cod_ibge=COD, consumo_mes_kwh=consumo, tarifa_kwh=tarifa, consumo_diurno_fracao=0.6, financiado=0), kwp)
    base = f.custo_kwp_tabela(np.array([kwp]))[0] * kwp
    if invest: e["custo_kwp_informado"] = invest / kwp
    e["reajuste_tarifa"] = reaj; e["fator_desempenho_real"] = fdes
    if perda is not None: e["degradacao_anual"] = perda
    return f.simular(e)

L = ["# Comparação exploratória do SAD com estimativas comerciais (Salvador)", "",
     "**Natureza:** as referências são estimativas comerciais de um fornecedor (NeoSolar) e duas calculadoras (Portal Solar, WEG), não medições de geração de sistemas instalados. "
     "Os quatro orçamentos NeoSolar de 10/20/30/40 kWp são do mesmo fornecedor e compartilham premissas; não são fontes independentes. "
     "Os cinco registros foram conferidos nos PDFs de orçamento fornecidos pelo autor (`conferido_no_pdf_anexado = sim`). "
     "A regressão do SAD foi treinada com geração simulada (pvlib); esta comparação não a valida empiricamente.", "",
     "## 1. Geração específica (kWh/kWp CC por mês)", "",
     f"SAD: Salvador = {ger_modelo_mes:.1f} kWh/kWp.mês pela regressão (= {ger_modelo_mes*12/365:.2f} kWh/kWp.dia) x fator de desempenho {FDES} = **{ger_sad:.1f}**. "
     "Cadeia auditada: geracao_dia (kWh/kWp.dia) x dias do mês = kWh/kWp.mês; soma dos 12 meses = kWh/kWp.ano; multiplicada por kWp instalado (CC) e pelo fator de desempenho. Sem mistura de unidades encontrada. "
     "Diferença % = (SAD - referência) / **referência**.", "",
     "| Referência | kWp CC | Geração ref. (kWh/mês) | Ref. (kWh/kWp.mês) | SAD (kWh/kWp.mês) | Diferença % (denominador: referência) | Conferido no PDF |", "|---|---|---|---|---|---|---|"]
for _, r in neo.iterrows():
    d = (ger_sad - r.geracao_kwh_kwp_mes) / r.geracao_kwh_kwp_mes
    L.append(f"| {r.rotulo} | {r.kwp_cc:.1f} | {r.geracao_mensal_kwh:,.0f} | {r.geracao_kwh_kwp_mes:.1f} | {ger_sad:.1f} | {d:+.1%} | {r.conferido_no_pdf_anexado} |")
L.append(f"| Portal Solar (calculadora, 80 x 555 Wp) | 44.4 | 5,799 | {5799/44.4:.1f} | {ger_sad:.1f} | {(ger_sad-5799/44.4)/(5799/44.4):+.1%} | n/a (imagem) |")
razao = neo.geracao_kwh_kwp_mes.mean() / ger_sad
L += ["", f"**Discrepância NÃO resolvida:** as propostas NeoSolar estimam entre {neo.geracao_kwh_kwp_mes.min():.0f} e {neo.geracao_kwh_kwp_mes.max():.0f} kWh/kWp.mês, o SAD estima {ger_sad:.0f}, e a Portal Solar ~{5799/44.4:.0f}. "
      "A NeoSolar declara base NREL/NASA, inclinação ideal, orientação norte e sem sombreamento; não declara perdas, local exato nem PR. "
      "Não foi possível explicar a diferença com as informações disponíveis. Os coeficientes da regressão NÃO foram ajustados para coincidir com os orçamentos.", ""]

L += ["## 2. Custo instalado por kWp CC", "", "| Referência | Investimento (R$) | R$/kWp CC | R$/Wp |", "|---|---|---|---|"]
for _, r in neo.iterrows():
    L.append(f"| {r.rotulo} | {r.investimento_rs:,.2f} | {r.custo_rs_kwp_cc:,.0f} | {r.custo_rs_kwp_cc/1000:.2f} |")
L.append(f"| Tabela Greener (referência de baixo custo, 40 a 55 kWp) | - | {f.custo_kwp_tabela(np.array([45.]))[0]:,.0f} | {f.custo_kwp_tabela(np.array([45.]))[0]/1000:.2f} |")
L.append(f"| Padrão do SAD (tabela x fator 1,20) | - | {f.custo_kwp_tabela(np.array([45.]))[0]*1.2:,.0f} | {f.custo_kwp_tabela(np.array([45.]))[0]*1.2/1000:.2f} |")
L += ["", "A NeoSolar é um fornecedor; seu preço não é tratado como preço de mercado. O SAD aceita orçamento real (campo `custo_kwp`) e o usa como custo fixo.", ""]

L += ["## 3. Payback e TIR: duas análises separadas", "",
      "A economia da proposta NeoSolar é bruta (geração x R$ 0,90, conta residual de R$ 45; o PDF avisa que não inclui iluminação pública nem custo de disponibilidade). "
      "A do SAD é líquida (mínimo faturável, Fio B, O&M, troca de inversor). Todas as propostas NeoSolar declaram tarifa R$ 0,90, inflação de energia de 8% a.a. e perda de 0,7%/ano, replicadas aqui (inflação e perda) na tabela 3a e 3b; o consumo é o informado na proposta (campo sem solar).", ""]
for titulo, usa_inv in (("3a. Com o INVESTIMENTO exato de cada proposta (isola o modelo financeiro)", True), ("3b. Com o CUSTO-PADRÃO do SAD (mostra o efeito da premissa de custo)", False)):
    L += [f"### {titulo}", "", "| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |", "|---|---|---|---|---|---|---|---|"]
    for _, r in neo.iterrows():
        cons = r.consumo_mensal_kwh_informado
        s = simula(r.kwp_cc, cons, r.tarifa_rs_kwh, r.investimento_rs if usa_inv else None, float(r.reajuste_energia), perda=float(r.perda_anual))
        L.append(f"| {r.rotulo} | {cons:,.0f} | {s['investimento'][0]:,.0f} | {s['geracao_ano1'][0]/12:,.0f} | {r.payback_informado_anos} | {s['payback'][0]:.2f} | {r.tir_informada:.1%} | {s['tir'][0]:.1%} |")
    L.append("")
L += ["Calculadoras (consumo 4.889 kWh/mês, R$ 0,90, investimento da referência): ", "", "| Referência | Payback ref. (anos) | Payback SAD |", "|---|---|---|"]
for nome, kwp, inv, pb in (("Portal Solar (menor valor)", 44.4, 88350, 2.75), ("Portal Solar (maior valor)", 44.4, 106950, 2.75), ("WEG (kWp assumido 40)", 40.0, 94232, 3.8)):
    L.append(f"| {nome} | {pb} | {simula(kwp, 4889, 0.90, inv)['payback'][0]:.2f} |")

L += ["", "## 4. Sensibilidade de baixa geração (NÃO é previsão)", "",
      f"Cenário separado da regressão: o fator de desempenho é multiplicado por {razao:.2f} (média da geração específica das propostas NeoSolar dividida pela do SAD), apenas para mostrar o efeito caso a geração real fique no nível dessas propostas. "
      "Origem: comparação com estimativas comerciais, não medição.", "",
      "| Caso (41 kWp, Salvador, 4.889 kWh/mês, R$ 0,90) | Investimento (R$) | Geração (kWh/mês) | Economia ano 1 (R$) | Payback | VPL (R$) |", "|---|---|---|---|---|---|"]
for nome, inv, fd in (("SAD padrão", None, FDES), ("Geração reduzida ao nível NeoSolar", None, FDES * razao), ("Custo NeoSolar (R$ 5.200/kWp), geração SAD", 41 * 5200, FDES), ("Custo NeoSolar + geração reduzida", 41 * 5200, FDES * razao)):
    s = simula(41.0, 4889, 0.90, inv, fdes=fd)
    L.append(f"| {nome} | {s['investimento'][0]:,.0f} | {s['geracao_ano1'][0]/12:,.0f} | {s['economia_ano1'][0]:,.0f} | {s['payback'][0]:.2f} | {s['vpl'][0]:,.0f} |")
L += ["", "## 5. Conclusão", "",
      "Comparação **exploratória** com estimativas comerciais, não validação empírica. (i) A geração do SAD é bem maior que a das propostas NeoSolar, sem explicação verificável; (ii) o custo-padrão do SAD é menos da metade do preço NeoSolar; "
      "(iii) com o investimento exato, o payback do SAD fica acima do informado pela NeoSolar (cerca de 6,3 contra 5,3 a 5,4 anos) porque a economia do SAD é líquida e limitada ao consumo faturável, de modo que a geração maior do SAD não se converte em economia adicional; com o custo-padrão do SAD o payback fica abaixo (cerca de 3,3 anos); (iv) payback e TIR dependem de custo e geração. Portanto os paybacks do caso-base não devem ser apresentados como confirmados por orçamentos externos; os cenários de custo NeoSolar e de baixa geração mostram o intervalo plausível."]
open(os.path.join(RAIZ, "docs", "validacao_orcamentos.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
