"""
Parâmetros e premissas do SAD de viabilidade de energia solar para residências na Bahia.

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
        fonte="Neoenergia Coelba, tarifa B1 residencial convencional consumo ativo SEM tributos, REH ANEEL nº 3.578/2026 "
              "(vigência 22/04/2026 a 21/04/2027). O usuário pode informar tarifa marginal de energia da fatura; não usar total da fatura dividido pelos kWh quando houver descontos, CIP ou Tarifa Social.",
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
        padrao=1.00, mc=("uni", 0.60, 1.00), tipo="premissa", unidade="fração do Fio B cobrada",
        fonte="Lei 14.300/2022, art. 27: 60% (2026), 75% (2027), 90% (2028); de 2029 em diante vale o art. 17 e a regulamentação "
              "da ANEEL, que não fixa 100% do Fio B. Cenário-base conservador: 100%; o Monte Carlo varre de 60% (nível de 2026) a 100%.",
    ),
    "simultaneidade": dict(
        padrao=0.35, mc=("tri", 0.20, 0.35, 0.55), tipo="premissa", unidade="fração da geração coincidente com carga",
        fonte="Costa et al., Revista Brasileira de Energia Solar 16(2), 2025, p.149: 35% de simultaneidade em caso residencial. Faixa 20%-55% é sensibilidade assumida e não medição da residência.",
    ),
    "custo_disponibilidade_kwh_mes": dict(
        padrao=50, mc=None, tipo="premissa", unidade="kWh/mês",
        fonte="Mínimo faturável conforme ligação informada: mono 30, bi 50, tri 100 kWh/mês. Confirmar na REN 1.000/2021.",
    ),
    "consumo_diurno_fracao": dict(
        padrao=0.45, mc=("tri", 0.25, 0.45, 0.65), tipo="premissa", unidade="fração do consumo",
        fonte="Perfil residencial simplificado: fração de demanda no período com sol. Não equivale ao fator de simultaneidade (35% da geração). Sem medição horária, valor apenas ilustrativo.",
    ),
    # ---------------- Custos e desempenho ----------------
    "fator_custo": dict(
        padrao=1.00, mc=("tri", 0.85, 1.00, 1.35), tipo="premissa", unidade="multiplicador",
        fonte="Tabela histórica Greener jan/2025 reproduzida por Costa et al. (2025), tabela 1 (2, 4, 8 kWp). Padrão 1,0; incerteza 0,85-1,35 é hipótese para orçamento residencial em 2026, não cotação. Inserir orçamento real em R$/kWp prevalece.",
    ),
    "om_pct_investimento": dict(
        padrao=0.010, mc=("tri", 0.005, 0.010, 0.015), tipo="premissa", unidade="% do investimento/ano",
        fonte="CBENS (análise de investimento em GD-FV): O&M de 1% do investimento ao ano. "
              "Faixa de 0,5% a 1,5% é premissa do autor.",
    ),
    "degradacao_anual": dict(
        padrao=0.007, mc=("tri", 0.004, 0.007, 0.008), tipo="fonte", unidade="% a.a.",
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
        padrao=0.079, mc=None, tipo="premissa", unidade="% a.a.",
        fonte="NÃO é sorteada: o financiamento só entra na decisão se o decisor informar a taxa (CET). Fontes discordam muito: BNB FNE Sol, piso de 7,9% a.a. "
              "citado em notícia (jul/2026), não verificado; a cartilha BNB (jun/2022) diz só 'abaixo da média do mercado'. BB Crédito Energia Renovável: "
              "a partir de 1,81% a.m. (~24,0% a.a.), CET de 30,36% a.a., conforme texto do site do BB informado pelo autor (página não verificada pelo desenvolvedor). "
              "Intervalo de referência: 7,9% a 30,4% a.a.; o valor 0,079 é só o padrão técnico usado em testes.",
    ),
    "prazo_financiamento_anos": dict(
        padrao=12, mc=None, tipo="fonte", unidade="anos",
        fonte="Prazo TOTAL do contrato (carência incluída): de até 12 anos no FNE Sol (BNB). É o teto; o prazo efetivo é negociado. Confirmar condições vigentes no site do BNB.",
    ),
    "carencia_meses": dict(
        padrao=6, mc=None, tipo="fonte", unidade="meses",
        fonte="Cartilha BNB, FNE Sol Pessoa Jurídica (jun/2022), item h: carência de até 6 meses (6 = teto da cartilha). Material posterior do BNB pode permitir carência maior; confirmar. Juros capitalizados na carência (premissa do autor).",
    ),
    "entrada_pct": dict(
        padrao=0.10, mc=None, tipo="fonte", unidade="fração do investimento",
        fonte="Cartilha BNB: financia até 100% do investimento; com alienação fiduciária como única garantia, até 90% do valor de placas e inversores (limite de R$ 300 mil). Entrada de 10% é escolha conservadora do autor (a cartilha permite financiar até 100%).",
    ),
    # ---------------- Sistema ----------------
    "m2_por_kwp": dict(
        padrao=7.0, mc=None, tipo="premissa", unidade="m²/kWp",
        fonte="Módulo de ~550 W ocupa ~2,6 m²; com folgas e espaçamento de telhado, ~7 m² por kWp.",
    ),
    "kwp_max": dict(
        padrao=75, mc=None, tipo="fonte", unidade="kW CA (aproximado em kWp)",
        fonte="Lei 14.300/2022: microgeração = potência instalada em CORRENTE ALTERNADA <= 75 kW. O protótipo aplica o limite à potência "
              "dos módulos (kWp) x relacao_dc_ac, sem modelar o inversor.",
    ),
    "relacao_dc_ac": dict(
        padrao=1.0, mc=None, tipo="premissa", unidade="kWp / kW CA",
        fonte="Relação entre potência dos módulos (CC) e do inversor (CA). 1,0 = conservador (limite de 75 kWp). Valores como 1,2 "
              "elevariam o teto de módulos para 90 kWp com inversor de 75 kW.",
    ),
    "ano_inicio": dict(
        padrao=2027, mc=None, tipo="premissa", unidade="ano",
        fonte="Primeiro ano de operação do sistema. Define o percentual do Fio B aplicável.",
    ),
}

# Custos indicativos de sistemas residenciais instalados, R$/kWp.
# Valores de 2, 4 e 8 kWp: Greener jan/2025 reproduzido em Costa et al., RBENS 16(2), 2025, tabela 1.
# O ponto de 1 kWp é EXTRAPOLAÇÃO DIDÁTICA; preço real em 2026 depende de orçamento.
CUSTO_KWP_PONTOS = {1: 4500, 2: 3640, 4: 2880, 8: 2420, 12: 2220, 30: 2020, 50: 2020, 75: 2350}

# Percentual do Fio B (Lei 14.300) por ano calendário
FIO_B_PCT = {2026: 0.60, 2027: 0.75, 2028: 0.90}

# Intervalos para cenários sintéticos de residências (não representam amostra populacional).
UNIVERSO_RESIDENCIAL = dict(
    consumo_mes_kwh=(100, 1200),
    tarifa_kwh=(0.75, 1.30),
    cobertura_alvo=(0.45, 1.45),
    kwp_min=1.24,  # dois módulos ilustrativos de 620 Wp, sujeitos à checagem do inversor real
)
# Alias para scripts do experimento de classificação legado (não usado na recomendação ao usuário).
UNIVERSO_PME = UNIVERSO_RESIDENCIAL


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
                        "Greener jan/2025 (Costa et al., 2025, tabela 1) para 2/4/8 kWp; demais pontos são aproximações"])


if __name__ == "__main__":
    exportar_csv(str(Path(__file__).with_name("parametros_premissas.csv")))
    print("Gerado parametros_premissas.csv")
