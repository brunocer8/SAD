"""Comparação EXPLORATÓRIA do SAD com estimativas comerciais (não é validação empírica). Gera docs/validacao_orcamentos.md.
Dados: dados/orcamentos_neosolar.csv (NeoSolar, 1 fornecedor) + 2 calculadoras (Portal Solar, WEG). Uso: python scripts/validar_orcamentos.py"""
import os, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import numpy as np, pandas as pd
import financeiro as f
from parametros import padroes

COD = f.buscar_municipio("Salvador")
neo = pd.read_csv(os.path.join(RAIZ, "dados", "orcamentos_neosolar.csv"))
_, perfil = f.carregar_municipios()
premissas = padroes()
ger_modelo_mes = float(perfil[COD].sum() / 12)          # kWh/kWp.mês antes do fator de desempenho
FDES = premissas["fator_desempenho_real"]
ger_sad = ger_modelo_mes * FDES                         # kWh/kWp.mês usado no SAD (1º ano)

def simula(kwp, consumo, tarifa, invest=None, reaj=0.06, fdes=FDES, perda=None):
    e = f.montar_entrada(dict(cod_ibge=COD, consumo_mes_kwh=consumo, tarifa_kwh=tarifa, consumo_diurno_fracao=0.6, financiado=0), kwp)
    if invest: e["custo_kwp_informado"] = invest / kwp
    e["reajuste_tarifa"] = reaj; e["fator_desempenho_real"] = fdes
    if perda is not None: e["degradacao_anual"] = perda
    return f.simular(e)

L = ["# Comparação exploratória do SAD com estimativas comerciais (Salvador)", "",
     "**Natureza:** as referências são estimativas comerciais de um fornecedor (NeoSolar) e duas calculadoras (Portal Solar, WEG), não medições de geração de sistemas instalados. "
     "Os quatro orçamentos NeoSolar de 10/20/30/40 kWp são do mesmo fornecedor e compartilham premissas; não são fontes independentes. "
     "Os cinco registros foram conferidos nos PDFs de orçamento fornecidos pelo autor (`conferido_no_pdf_anexado = sim`). "
     "As propostas têm potência CC de 10,8 a 54 kWp. A regressão do SAD foi treinada com geração simulada (pvlib) e a comparação não a valida empiricamente.", "",
     "## 1. Geração específica (kWh/kWp CC por mês)", "",
     f"SAD: Salvador = {ger_modelo_mes:.1f} kWh/kWp.mês pela regressão (= {ger_modelo_mes*12/365:.2f} kWh/kWp.dia) x fator de desempenho {FDES} = **{ger_sad:.1f}**. "
     "Cadeia auditada: geracao_dia (kWh/kWp.dia) x dias do mês = kWh/kWp.mês; soma dos 12 meses = kWh/kWp.ano; multiplicada por kWp instalado (CC) e pelo fator de desempenho. Sem mistura de unidades encontrada. "
     "Diferença % = (SAD - referência) / **referência**.", "",
     "| Referência | kWp CC | Geração ref. (kWh/mês) | Ref. (kWh/kWp.mês) | SAD (kWh/kWp.mês) | Diferença % (denominador: referência) | Conferido no PDF |", "|---|---|---|---|---|---|---|"]
for _, r in neo.iterrows():
    d = (ger_sad - r.geracao_kwh_kwp_mes) / r.geracao_kwh_kwp_mes
    L.append(f"| {r.rotulo} | {r.kwp_cc:.1f} | {r.geracao_mensal_kwh:,.0f} | {r.geracao_kwh_kwp_mes:.1f} | {ger_sad:.1f} | {d:+.1%} | {r.conferido_no_pdf_anexado} |")
L.append(f"| Portal Solar (calculadora, 80 x 555 Wp) | 44.4 | 5,799 | {5799/44.4:.1f} | {ger_sad:.1f} | {(ger_sad-5799/44.4)/(5799/44.4):+.1%} | n/a (imagem) |")
geracao_ref = neo.geracao_kwh_kwp_mes.to_numpy()
desvio_geracao = ger_sad - geracao_ref
razao = geracao_ref.mean() / ger_sad
L += ["", f"**Discrepância NÃO resolvida:** as propostas NeoSolar estimam entre {neo.geracao_kwh_kwp_mes.min():.0f} e {neo.geracao_kwh_kwp_mes.max():.0f} kWh/kWp.mês, o SAD estima {ger_sad:.0f}, e a Portal Solar ~{5799/44.4:.0f}. "
      f"O desvio médio do SAD frente às cinco propostas é {desvio_geracao.mean():+.2f} kWh/kWp.mês ({(desvio_geracao / geracao_ref).mean():+.1%}, média simples dos desvios relativos). "
      "A NeoSolar declara base NREL/NASA, inclinação ideal, orientação norte e sem sombreamento; não declara perdas, local exato nem PR. "
      "Não foi possível explicar a diferença com as informações disponíveis. Os coeficientes da regressão NÃO foram ajustados para coincidir com os orçamentos.", ""]

fator_custo = premissas["fator_custo"]
custo_ref = neo.custo_rs_kwp_cc.to_numpy()
custo_sad = f.custo_kwp_tabela(neo.kwp_cc.to_numpy()) * fator_custo
desvio_custo = custo_sad - custo_ref
desvio_relativo_custo = desvio_custo / custo_ref
L += ["## 2. Custo instalado por kWp CC", "",
      "| Referência | Investimento cotado (R$) | Cotado (R$/kWp CC) | SAD padrão (R$/kWp CC) | Diferença % |",
      "|---|---|---|---|---|"]
for r, custo, desvio in zip(neo.itertuples(index=False), custo_sad, desvio_relativo_custo):
    L.append(f"| {r.rotulo} | {r.investimento_rs:,.2f} | {r.custo_rs_kwp_cc:,.2f} | {custo:,.2f} | {desvio:+.1%} |")
L += ["", f"O SAD interpola a tabela histórica de custos e aplica o fator de custo padrão {fator_custo:.2f}. "
      f"Os valores estimados variam de R$ {custo_sad.min():,.2f} a R$ {custo_sad.max():,.2f}/kWp, frente a R$ {custo_ref.min():,.2f} a R$ {custo_ref.max():,.2f}/kWp cotados. "
      f"O desvio médio (SAD menos cotado) é de {desvio_custo.mean():+,.2f} R$/kWp e o erro absoluto médio é de {abs(desvio_custo).mean():,.2f} R$/kWp. "
      f"A média dos desvios percentuais é {desvio_relativo_custo.mean():+.1%} (faixa de {desvio_relativo_custo.min():+.1%} a {desvio_relativo_custo.max():+.1%}).",
      "", "As medidas descrevem as cinco propostas. O SAD aceita um orçamento informado no campo `custo_kwp`, que substitui o custo-padrão.", ""]

L += ["## 3. Payback e TIR: duas análises separadas", "",
      "A economia da proposta NeoSolar é bruta (geração x R$ 0,90, conta residual de R$ 45; o PDF avisa que não inclui iluminação pública nem custo de disponibilidade). "
      "A do SAD é líquida (mínimo faturável, Fio B, O&M, troca de inversor). Todas as propostas NeoSolar declaram tarifa R$ 0,90, inflação de energia de 8% a.a. e perda de 0,7%/ano, replicadas aqui (inflação e perda) na tabela 3a e 3b; o consumo é o informado na proposta (campo sem solar).", ""]
payback_sad = {}
for titulo, usa_inv in (("3a. Com o investimento exato de cada proposta", True), ("3b. Com o custo-padrão do SAD", False)):
    paybacks = []
    L += [f"### {titulo}", "", "| Proposta | Consumo (kWh/mês) | Investimento no SAD (R$) | Geração SAD (kWh/mês) | Payback ref. | Payback SAD | TIR ref. | TIR SAD |", "|---|---|---|---|---|---|---|---|"]
    for _, r in neo.iterrows():
        cons = r.consumo_mensal_kwh_informado
        s = simula(r.kwp_cc, cons, r.tarifa_rs_kwh, r.investimento_rs if usa_inv else None, float(r.reajuste_energia), perda=float(r.perda_anual))
        paybacks.append(float(s["payback"][0]))
        L.append(f"| {r.rotulo} | {cons:,.0f} | {s['investimento'][0]:,.0f} | {s['geracao_ano1'][0]/12:,.0f} | {r.payback_informado_anos} | {s['payback'][0]:.2f} | {r.tir_informada:.1%} | {s['tir'][0]:.1%} |")
    L.append("")
    payback_sad[usa_inv] = np.array(paybacks)
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
payback_cotado = neo.payback_informado_anos.to_numpy()
payback_orcamento = payback_sad[True]
payback_padrao = payback_sad[False]
desvio_payback = payback_orcamento - payback_cotado
L += ["", "## 5. Conclusão", "",
      f"Com os investimentos informados nas propostas, o payback estimado pelo SAD variou entre {payback_orcamento.min():.2f} e {payback_orcamento.max():.2f} anos, "
      f"frente ao intervalo cotado de {payback_cotado.min():.1f} a {payback_cotado.max():.1f} anos. O desvio médio ficou em {desvio_payback.mean():+.2f} ano. "
      f"Com o custo-padrão, o payback estimado ficou entre {payback_padrao.min():.2f} e {payback_padrao.max():.2f} anos. "
      "A comparação iguala o investimento no primeiro teste. As estimativas de geração e as regras para calcular a economia ainda diferem.",
      "", "Os resultados mostram sensibilidade às premissas de custo e geração nos cenários comparados. As propostas são estimativas de um único fornecedor para sistemas maiores que o caso residencial de 1,86 kWp. "
      "A comparação é exploratória e não sustenta estimativa de preço típico, confirmação do retorno residencial ou validação da geração em campo."]
open(os.path.join(RAIZ, "docs", "validacao_orcamentos.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
