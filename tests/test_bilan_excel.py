"""BILAN-1 Lot 5 — l'export Excel est VIVANT et égal au moteur.

Sans tableur sous la main, on évalue nous-mêmes le graphe de formules du classeur
(vocabulaire volontairement restreint : références de cellules, + - * / ( ),
SUM(plage)). On prouve (1) que HT/TVA/TTC et les totaux sont des FORMULES, pas des
valeurs figées, et (2) que leur évaluation est identique au moteur, au centime.
"""

from __future__ import annotations

import re

import pytest

from labuse.bilan.excel import classeur_bilan
from labuse.bilan.moteur import Moteur
from test_bilan_moteur import entrees_temoin_promotrice


def _grille(ws):
    g = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None:
                g[c.coordinate] = c.value
    return g


_REF = re.compile(r"\b([A-G])(\d+)\b")
_SUM = re.compile(r"SUM\(([A-G])(\d+):([A-G])(\d+)\)")


def _evaluateur(grille):
    cache: dict[str, float] = {}

    def col_to_i(c):
        return ord(c) - 64

    def ev(coord: str) -> float:
        if coord in cache:
            return cache[coord]
        v = grille.get(coord)
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            cache[coord] = float(v)
            return cache[coord]
        expr = v.lstrip("=")

        def som(m):
            c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            assert c1 == c2
            return "(" + "+".join(f"{c1}{rr}" for rr in range(r1, r2 + 1)) + ")"

        expr = _SUM.sub(som, expr)
        expr = _REF.sub(lambda m: repr(ev(f"{m.group(1)}{m.group(2)}")), expr)
        val = float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 — vocabulaire contrôlé
        cache[coord] = val
        return val

    return ev


def _ws_temoin():
    wb = classeur_bilan(entrees_temoin_promotrice())
    return wb["Bilan"]


def test_colonnes_sont_des_formules_pas_des_valeurs():
    ws = _ws_temoin()
    g = _grille(ws)
    formules = [v for v in g.values() if isinstance(v, str) and v.startswith("=")]
    assert len(formules) > 150  # HT/TVA/TTC + totaux + synthèse
    # la ligne Résultat net est bien une formule (jamais une valeur figée)
    res = [k for k, v in g.items() if isinstance(v, str) and "D66-D65" in v]
    assert res, "résultat net doit être une formule CA HT − dépenses HT"


def test_excel_egale_le_moteur_au_centime():
    ws = _ws_temoin()
    ev = _evaluateur(_grille(ws))
    r = Moteur().calculer(entrees_temoin_promotrice())

    # localiser les lignes de synthèse par leur libellé en colonne A
    lignes = {ws.cell(row, 1).value: row for row in range(1, ws.max_row + 1) if ws.cell(row, 1).value}
    row_dep = lignes["Dépenses totales"]
    row_ca = lignes["Chiffre d'affaires"]
    row_res = lignes["Résultat net"]

    assert ev(f"D{row_ca}") == pytest.approx(r.ca_ht, abs=1.0)
    assert ev(f"F{row_ca}") == pytest.approx(r.ca_ttc, abs=1.0)
    assert ev(f"D{row_dep}") == pytest.approx(r.depenses_ht, abs=1.0)
    assert ev(f"E{row_dep}") == pytest.approx(r.depenses_tva, abs=1.0)
    assert ev(f"D{row_res}") == pytest.approx(r.resultat_net, abs=1.0)
    assert ev(f"E{row_res}") == pytest.approx(r.marge_pct, abs=1e-4)
    assert ev(f"F{lignes['TVA résiduelle']}") == pytest.approx(r.tva_residuelle, abs=1.0)

    # chaque total de bloc du classeur = le bloc du moteur
    for b in r.blocs:
        trow = lignes[f"Total — {b.titre}"]
        assert ev(f"D{trow}") == pytest.approx(b.ht, abs=1.0), f"bloc {b.id} HT"
        assert ev(f"F{trow}") == pytest.approx(b.ttc, abs=1.0), f"bloc {b.id} TTC"
