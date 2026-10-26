"""
Parâmetros e premissas do SAD de viabilidade de energia solar para PMEs na Bahia.

Cada parâmetro tem:
  padrao  : valor usado na simulação determinística (editável pelo usuário)
  mc      : distribuição usada no Monte Carlo, ou None se não varia
            ("tri", min, moda, max) | ("uni", min, max) | ("uni_int", min, max)
  tipo    : "fonte"    = valor tirado de uma fonte citada
            "estimado" = derivado de fonte(s) com conta própria
            "premissa" = escolha do autor, declarada no trabalho
  fonte   : de onde veio (ou justificativa)
Acesso às fontes na web: 16/10/2026.
"""
import csv
from pathlib import Path

PARAMETROS = {
    # ---------------- Tarifa e regras de compensação ----------------
    "tarifa_kwh": dict(
        padrao=0.87773, mc=None, tipo="fonte", unidade="R$/kWh",
        fonte="Neoenergia Coelba, tarifa B3 consumo ativo SEM tributos, REH ANEEL nº 3.578/2026 "
              "(vigência 22/04/2026 a 21/04/2027). O usuário deve informar o preço da fatura (com tributos).",
    ),
    "reajuste_tarifa": dict(
        padrao=0.060, mc=("tri", 0.035, 0.060, 0.090), tipo="estimado", unidade="% a.a.",
        fonte="Histórico de reajustes da Coelba 2017-2026 (média 7,9%, mediana 6,0%, últimos 3 anos 3,1%) "
              "e Focus 9/10/2026 (IPCA administrados 3,5% a 3,8% em 2027-2029) como cenário baixo.",
    ),
    "fio_b_share_tarifa": dict(
        padrao=0.28, mc=("tri", 0.22, 0.28, 0.32), tipo="estimado", unidade="fração da tarifa",
        fonte="ANEEL (proposta de revisão da REN 482, citada pelo Canal Solar): Fio B ~28% da tarifa; "
              "gráfico da Coelba: 'Distribuição' = 29,1% do preço final. NÃO é o valor oficial da Coelba.",
    ),
    "fio_b_2029_em_diante": dict(
        padrao=1.00, mc=("uni", 0.90, 1.00), tipo="premissa", unidade="fração do Fio B cobrada",
        fonte="Lei 14.300/2022: 60% (2026), 75% (2027), 90% (2028); a partir de 2029 a regra depende de "
              "regulamentação futura. Cenário conservador: 100%.",
    ),
    "custo_disponibilidade_kwh_mes": dict(
        padrao=100, mc=None, tipo="premissa", unidade="kWh/mês",
        fonte="Mínimo faturável de ligação trifásica (30/50/100 kWh). Confirmar na REN 1.000/2021.",
    ),
    "consumo_diurno_fracao": dict(
        padrao=0.60, mc=("uni", 0.40, 0.80), tipo="premissa", unidade="fração do consumo",
        fonte="Parcela do consumo que ocorre durante as horas de sol. A energia gerada e consumida na hora "
              "(limitada por essa parcela) não passa pela rede e não sofre Fio B. Premissa para PME com "
              "expediente diurno; é entrada do usuário no sistema.",
    ),
    # ---------------- Custos e desempenho ----------------
    "fator_custo": dict(
        padrao=1.00, mc=("tri", 0.90, 1.00, 1.15), tipo="estimado", unidade="multiplicador",
        fonte="Greener SED 1S/2026: preços variaram -11% a +7% entre jan/25, jun/25, jan/26 e jun/26.",
    ),
    "om_pct_investimento": dict(
        padrao=0.010, mc=("tri", 0.005, 0.010, 0.015), tipo="premissa", unidade="% do investimento/ano",
        fonte="CBENS (análise de investimento em GD-FV): O&M de 1% do investimento ao ano. "
              "Faixa de 0,5% a 1,5% é premissa do autor.",
    ),
    "degradacao_anual": dict(
        padrao=0.005, mc=("tri", 0.004, 0.005, 0.008), tipo="fonte", unidade="% a.a.",
        fonte="Viana et al. (2012), citado em trabalho do CBENS: 0,5% ao ano, típico no Brasil. Teto de 0,8%: a cartilha do BNB cita garantia de "
              "mais de 80% da produção inicial em 25 anos (20%/25 anos = 0,8% a.a.).",
    ),
    "vida_util_anos": dict(
        padrao=25, mc=None, tipo="fonte", unidade="anos",
        fonte="Garantia típica de módulos de 20 a 30 anos; 25 anos usado no CBENS.",
    ),
    "inversor_ano_troca": dict(
        padrao=12, mc=("uni_int", 12, 20), tipo="estimado", unidade="ano de operação",
        fonte="Fontes divergem: 12-15 anos (SunEarthTools) a ~20 anos de MTBF (Canal Solar/fabricante).",
    ),
    "inversor_custo_pct": dict(
        padrao=0.06, mc=("uni", 0.05, 0.08), tipo="estimado", unidade="% do investimento",
        fonte="SunEarthTools: reposição de ~5% a 8% do valor da planta (texto traduzido; confirmar no original).",
    ),
    "fator_desempenho_real": dict(
        padrao=0.95, mc=("tri", 0.80, 0.95, 1.00), tipo="premissa", unidade="multiplicador",
        fonte="Simulação pvlib já usa perdas de 14%. Estudo de caso (CONTECC 2026, Paraná) mediu 81,6% "
              "da geração projetada comercialmente; faixa 0,80 a 1,00 cobre essa incerteza.",
    ),
    # ---------------- Macroeconomia ----------------
    "ipca": dict(
        padrao=0.043, mc=("tri", 0.035, 0.043, 0.052), tipo="fonte", unidade="% a.a.",
        fonte="Banco Central, Relatório Focus 9/10/2026: IPCA esperado 4,30% (2027), 3,79% (2028), 3,50% (2029).",
    ),
    "taxa_desconto": dict(
        padrao=0.12, mc=("uni", 0.10, 0.14), tipo="estimado", unidade="% a.a. nominal",
        fonte="Focus 9/10/2026: Selic esperada 13,25% (2026), 12,00% (2027), 10,50% (2028), 10,00% (2029).",
    ),
    # ---------------- Financiamento ----------------
    "taxa_financiamento": dict(
        padrao=0.079, mc=("uni", 0.079, 0.1325), tipo="estimado", unidade="% a.a.",
        fonte="BNB, FNE Sol: juros pré-fixados a partir de 7,9% a.a. (piso, notícia de jul/2026). A cartilha do BNB diz apenas 'abaixo da média do mercado', sem número; "
              "há bônus de adimplência (não modelado). Limite superior = Selic atual.",
    ),
    "prazo_financiamento_anos": dict(
        padrao=12, mc=None, tipo="fonte", unidade="anos",
        fonte="Cartilha BNB, FNE Sol Pessoa Jurídica (jun/2022): prazo de até 12 anos. É o teto; o prazo efetivo é negociado. Confirmar condições vigentes no site do BNB.",
    ),
    "carencia_meses": dict(
        padrao=6, mc=None, tipo="fonte", unidade="meses",
        fonte="Cartilha BNB, FNE Sol Pessoa Jurídica: carência de até 6 meses. Juros capitalizados na carência (premissa).",
    ),
    "entrada_pct": dict(
        padrao=0.10, mc=None, tipo="fonte", unidade="fração do investimento",
        fonte="Cartilha BNB: financia até 100% do investimento; com alienação fiduciária como única garantia, até 90% do valor de placas e inversores (limite de R$ 300 mil). Entrada de 10% por conservadorismo.",
    ),
    # ---------------- Sistema ----------------
    "m2_por_kwp": dict(
        padrao=7.0, mc=None, tipo="premissa", unidade="m²/kWp",
        fonte="Módulo de ~550 W ocupa ~2,6 m²; com folgas e espaçamento de telhado, ~7 m² por kWp.",
    ),
    "kwp_max": dict(
        padrao=75, mc=None, tipo="fonte", unidade="kWp",
        fonte="Limite da microgeração distribuída (Lei 14.300/2022).",
    ),
    "ano_inicio": dict(
        padrao=2027, mc=None, tipo="premissa", unidade="ano",
        fonte="Primeiro ano de operação do sistema. Define o percentual do Fio B aplicável.",
    ),
}

# Custo do sistema instalado (kit + integração), telhado, R$/kWp. Greener SED 1S/2026, jun/2026.
CUSTO_KWP_PONTOS = {  # kWp: R$/kWp
    8: 2430, 12: 2220, 30: 2020, 50: 2020, 75: 2350,
}

# Percentual do Fio B (Lei 14.300) por ano calendário
FIO_B_PCT = {2026: 0.60, 2027: 0.75, 2028: 0.90}

# Intervalos usados para sortear cenários de clientes (não são premissas do modelo, definem o "universo")
UNIVERSO_PME = dict(
    consumo_mes_kwh=(1000, 30000),   # log-uniforme; faixa típica de PME em baixa tensão (premissa)
    tarifa_kwh=(0.85, 1.30),         # de B3 sem tributos até um valor com tributos (premissa)
    cobertura_alvo=(0.4, 1.6),       # relação entre geração e consumo do sistema dimensionado
    kwp_min=3.0,
)


def padroes() -> dict:
    return {k: v["padrao"] for k, v in PARAMETROS.items()}


def exportar_csv(caminho: str) -> None:
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["parametro", "valor_padrao", "unidade", "distribuicao_monte_carlo", "tipo", "fonte_ou_justificativa"])
        for k, v in PARAMETROS.items():
            w.writerow([k, v["padrao"], v["unidade"], v["mc"] if v["mc"] else "fixo", v["tipo"], v["fonte"]])
        for kwp, c in CUSTO_KWP_PONTOS.items():
            w.writerow([f"custo_kwp_{kwp}kWp", c, "R$/kWp", "x fator_custo", "fonte",
                        "Greener, Estudo Estratégico SED 1S/2026 (set/2026), preço médio de sistema instalado em jun/2026"])


if __name__ == "__main__":
    exportar_csv(str(Path(__file__).with_name("parametros_premissas.csv")))
    print("Gerado parametros_premissas.csv")
