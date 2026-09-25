"""DONNEES-FIX-1 lot C — GOLDEN avant/après de la SDP existante / restante sur 55 parcelles.

Isole EXACTEMENT le changement du lot C (niveaux existants depuis l'égout LiDAR + coefficient de
plancher) : l'emprise bâtie et la capacité max (`sdp_max`) sont INCHANGÉES par le lot ; seuls les
niveaux (source) et le coefficient changent. On calcule donc, sur les MÊMES parcelles :
  - APRÈS = compute_residuel actuel (LiDAR égout, coef 0,95) ;
  - AVANT = même moteur avec l'ancienne règle de niveaux (BD TOPO seul) et coef 1,0.
Chaque écart est expliqué par la hauteur mesurée. BZ1065 est forcée dans l'échantillon.

Lecture seule (aucune écriture de run). Sortie : CSV + tableau Markdown.
"""
from __future__ import annotations

import csv
import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite import residuel
import labuse.faisabilite.engine as eng

COMMUNE = "97411"   # Saint-Denis
BZ1065_ID = 336319
N = 55


def _select_ids(s) -> list[int]:
    """55 parcelles bâties de Saint-Denis avec égout LiDAR, échantillonnées sur toute la plage de
    hauteur (pour voir les niveaux qui changent ET ceux qui ne changent pas) ; BZ1065 incluse."""
    rows = s.execute(text("""
        SELECT p.id, l.egout_m
        FROM parcels p JOIN batiment_hauteur_lidar l ON l.idu = p.idu
        WHERE left(p.idu,5) = :insee AND l.egout_m > 0
        ORDER BY l.egout_m DESC
    """), {"insee": COMMUNE}).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    # échantillonnage régulier sur la plage (du plus haut au plus bas)
    step = max(1, len(ids) // (N - 1))
    sample = ids[::step][: N - 1]
    if BZ1065_ID not in sample:
        sample.append(BZ1065_ID)
    return sample[:N]


def _old_niveaux(session, pid, defaut):
    """Ancienne règle (avant lot C) : BD TOPO nombre_d_etages → hauteur/3 → placeholder."""
    row = session.execute(text(
        """SELECT max((b.attrs->>'nombre_d_etages')::int) AS etages,
                  max(NULLIF(b.attrs->>'hauteur','')::float) AS hauteur
           FROM spatial_layers b JOIN parcels p ON p.id = :pid
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"""),
        {"pid": pid}).first()
    if row and row.etages:
        return float(row.etages), True, "bdtopo"
    if row and row.hauteur:
        return max(1.0, round(float(row.hauteur) / 3.0)), True, "bdtopo"
    return float(defaut), False, "sans"


def main() -> None:
    with session_scope() as s:
        ids = _select_ids(s)
        if not ids:
            print("Aucune parcelle Saint-Denis avec égout LiDAR — abandon.")
            sys.exit(1)
        # égout par parcelle (affichage)
        egouts = dict(s.execute(text(
            "SELECT p.id, l.egout_m FROM parcels p JOIN batiment_hauteur_lidar l ON l.idu=p.idu "
            "WHERE p.id = ANY(:ids)"), {"ids": ids}).fetchall())
        idus = dict(s.execute(text("SELECT id, idu FROM parcels WHERE id = ANY(:ids)"),
                              {"ids": ids}).fetchall())

        # APRÈS (moteur actuel)
        apres = {}
        for pid in ids:
            try:
                apres[pid] = residuel.compute_residuel(s, pid, assiette_clippee=True)
            except Exception as e:  # noqa: BLE001
                apres[pid] = {"disponible": False, "raison": str(e)[:80]}

        # AVANT : même moteur, ancienne règle de niveaux + coef 1,0
        orig_niv = residuel._niveaux_existants
        orig_charger = eng.Hypotheses.charger.__func__

        def old_charger(cls, commune=None):
            h = orig_charger(cls, commune)
            h.coef_sdp_existante = 1.0
            return h

        residuel._niveaux_existants = _old_niveaux
        eng.Hypotheses.charger = classmethod(old_charger)
        avant = {}
        try:
            for pid in ids:
                try:
                    avant[pid] = residuel.compute_residuel(s, pid, assiette_clippee=True)
                except Exception as e:  # noqa: BLE001
                    avant[pid] = {"disponible": False, "raison": str(e)[:80]}
        finally:
            residuel._niveaux_existants = orig_niv
            eng.Hypotheses.charger = classmethod(orig_charger)

    # table
    hdr = ["idu", "egout_m", "niv_avant", "niv_apres", "source",
           "sdp_exist_avant", "sdp_exist_apres", "sdp_rest_avant", "sdp_rest_apres",
           "delta_rest", "explication"]
    lignes = []
    for pid in ids:
        a, ap = avant.get(pid, {}), apres.get(pid, {})
        if not (a.get("disponible") and ap.get("disponible")):
            lignes.append([idus.get(pid, pid), round(egouts.get(pid, 0), 1), "", "", "",
                           "", "", "", "", "", a.get("raison") or ap.get("raison") or "non disponible"])
            continue
        dr = ap["sdp_residuelle_m2"] - a["sdp_residuelle_m2"]
        niv_a, niv_ap = a["niveaux_existants"], ap["niveaux_existants"]
        if niv_ap > niv_a:
            expl = f"égout {egouts.get(pid,0):.1f} m → {niv_ap:g} niveaux (vs {niv_a:g}) : existant relevé → restant baisse"
        elif niv_ap < niv_a:
            expl = f"égout {egouts.get(pid,0):.1f} m → {niv_ap:g} niveaux (vs {niv_a:g}) : existant abaissé → restant monte"
        else:
            expl = f"niveaux inchangés ({niv_ap:g}) ; seul le coef de plancher 0,95 joue (restant +{dr})"
        lignes.append([idus.get(pid, pid), round(egouts.get(pid, 0), 1), f"{niv_a:g}", f"{niv_ap:g}",
                       ap.get("hauteur_source"), a["sdp_existante_m2"], ap["sdp_existante_m2"],
                       a["sdp_residuelle_m2"], ap["sdp_residuelle_m2"], dr, expl])

    out = "docs/audit-2026-09/donnees-fix-1/golden-55.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(lignes)
    print(f"écrit {out} ({len(lignes)} lignes)")

    # résumé
    ok = [l for l in lignes if l[9] != ""]
    baisses = [l for l in ok if isinstance(l[9], int) and l[9] < 0]
    hausses = [l for l in ok if isinstance(l[9], int) and l[9] > 0]
    inch = [l for l in ok if l[9] == 0]
    print(f"disponibles {len(ok)}/{len(lignes)} · restant baisse {len(baisses)} · "
          f"monte {len(hausses)} · inchangé {len(inch)}")
    # BZ1065
    for l in lignes:
        if str(l[0]).endswith("BZ1065"):
            print("BZ1065 :", l)


if __name__ == "__main__":
    main()
