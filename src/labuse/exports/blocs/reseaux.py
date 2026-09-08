"""Bloc « 6. Réseaux, desserte, terrain ». Verdict de viabilisation (faisceau d'indices), desserte
par distance (Q A6 : accès par distance seulement), assainissement, ensoleillement."""
from __future__ import annotations

from ..lignes import a, pied, val
from ..nature import chip
from ..registre_fmt import groupe
from ..rendu import chip_span, esc, ligne_kv, section, table_kv
from ..verdicts import rendu_verdict, verdict_reseaux

IDS = ("viabilisation_verdict", "distance_arret_m", "part_logements_egout_pct", "fibre_parcelle")


def rendu(valeurs) -> str:
    corps = rendu_verdict(verdict_reseaux(valeurs))
    lignes = []
    viab = val(valeurs, "viabilisation_verdict") or {}
    indices = [c.get("libelle") for c in (viab.get("contributions") or []) if c.get("signe") == "+"]
    if indices:
        lignes.append(ligne_kv("Les indices concordants", esc(" · ".join(indices)),
                               chip(valeurs["viabilisation_verdict"])))
    prox = val(valeurs, "distance_arret_m") or {}
    if isinstance(prox, dict):
        arret, pole, axe = prox.get("arret"), prox.get("pole"), prox.get("axe")
        if isinstance(arret, dict) and arret.get("distance_m") is not None:
            lignes.append(ligne_kv("Transports",
                          esc(f"Arrêt {arret.get('nom', '')} ({arret.get('reseau', '')}) à "
                              f"{arret['distance_m']} m"
                              + (f" · {pole.get('nom')} à {pole.get('distance_m')} m" if isinstance(pole, dict) and pole.get('distance_m') else "")),
                          chip_span("s", "sourcé")))
        if isinstance(axe, dict) and axe.get("distance_m") is not None:
            lignes.append(ligne_kv("Axe structurant",
                          esc(f"{axe.get('nom', '')} à {axe['distance_m']} m — desserte rapide et "
                              "nuisances ; recul le long des axes classés à vérifier (L.111-6)"),
                          chip_span("s", "sourcé")))
    anc = val(valeurs, "part_logements_egout_pct")
    if isinstance(anc, dict) and anc.get("libelle"):
        lignes.append(ligne_kv("Assainissement", esc(anc["libelle"]), chip_span("s", "sourcé")))
    sol = (viab.get("solaire") or {}) if isinstance(viab, dict) else {}
    if sol.get("prod_kwh_kwc"):
        lignes.append(ligne_kv("Ensoleillement",
                      esc(f"Productible solaire ~{groupe(sol['prod_kwh_kwc'])} kWh par kWc et par an"),
                      chip_span("e", "estimé")))
    fibre = val(valeurs, "fibre_parcelle")
    if isinstance(fibre, dict) and fibre.get("etat"):
        lignes.append(ligne_kv("Fibre", esc(str(fibre["etat"])), chip_span("s", "sourcé")))
    if not lignes and not corps.strip():
        return ""      # ni verdict ni ligne → section omise
    if lignes:
        corps += table_kv(lignes)
    return section("6. Réseaux, desserte, terrain", corps + pied(valeurs, IDS))
