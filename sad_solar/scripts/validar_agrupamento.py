"""Reproduz um empate técnico no SAD ou busca grupos em uma grade residencial."""
import argparse
from collections import defaultdict
from itertools import product
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import financeiro as f
import saw


CASO = ("Salvador", 250, 30, 1.20, "cautela")


def simular(municipio, consumo, area, tarifa, prioridade):
    return saw.decisao(
        dict(
            cod_ibge=f.buscar_municipio(municipio),
            consumo_mes_kwh=consumo,
            area_m2=area,
            tarifa_kwh=tarifa,
            consumo_diurno_fracao=0.45,
            tipo_ligacao="bifasica",
            custo_disponibilidade_kwh_mes=50,
            prioridade=prioridade,
        ),
        n_mc=1000,
    )


def mostrar(caso, resultado):
    municipio, consumo, area, tarifa, prioridade = caso
    rec = resultado["recomendacao"]
    print(f"{municipio} | {consumo} kWh/mês | {area} m² | R$ {tarifa:.5f}/kWh | {prioridade}")
    print(f"  delta={resultado['delta']:.9f} | recomendação: {rec['nome']} | frequência de liderança: {rec['prob_lider']:.1%}")
    grupos = defaultdict(list)
    for alt in resultado["ranking"]:
        if alt["indice"] is not None:
            grupos[alt["grupo"]].append(f"{alt['nome']} ({alt['indice']:.9f})")
    for grupo, alternativas in grupos.items():
        print(f"  Grupo {grupo}: " + " | ".join(alternativas))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grade", action="store_true", help="lista os casos com grupos de duas ou mais alternativas")
    args = parser.parse_args()
    if not args.grade:
        mostrar(CASO, simular(*CASO))
        return

    grade = product(
        ("Salvador", "Feira de Santana", "Barreiras"),
        (100, 250, 1000),
        (10, 30, 60),
        (0.50, 0.87773, 1.20),
        ("padrao", "retorno", "cautela"),
    )
    total = encontrados = 0
    for caso in grade:
        resultado = simular(*caso)
        total += 1
        grupos = [alt["grupo"] for alt in resultado["ranking"] if alt["indice"] is not None]
        if len(grupos) > len(set(grupos)):
            encontrados += 1
            mostrar(caso, resultado)
    print(f"Cenários com ao menos um grupo compartilhado: {encontrados}/{total}")


if __name__ == "__main__":
    main()
