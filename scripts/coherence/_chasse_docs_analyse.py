#!/usr/bin/env python3
"""CHASSE-DOCS-1 — extracteur NOTION × LECTEUR (angle A), hors banc.

Charge les artefacts collectés et, pour chaque notion servie par >=2 lecteurs,
tabule la valeur de chaque lecteur. Imprime les divergences candidates.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RACINE = Path("docs/audit-2026-10/chasse-docs")


def load(idu: str, name: str):
    p = RACINE / idu / f"{name}.json"
    if not p.exists():
        return None
    try:
        return json.load(open(p))["data"]
    except Exception:  # noqa: BLE001
        return None


def txt(idu: str, name: str) -> str:
    p = RACINE / idu / f"{name}.pdf.txt"
    return p.read_text(errors="replace") if p.exists() else ""


def g(d, *path, default=None):
    cur = d
    for k in path:
        if cur is None:
            return default
        if isinstance(k, int):
            cur = cur[k] if isinstance(cur, list) and len(cur) > k else None
        else:
            cur = cur.get(k) if isinstance(cur, dict) else None
    return cur if cur is not None else default


def regles_valeur(fiche, cle):
    z = g(fiche, "reglement_plu", "zones", 0, "regles_valeurs", default=[]) or []
    for rv in z:
        if rv.get("cle") == cle:
            return rv.get("valeur")
    return None


def extraire(idu: str) -> dict:
    fiche = load(idu, "fiche") or {}
    compare = (load(idu, "compare_seule") or {}).get("parcels") or [{}]
    cmp0 = compare[0] if compare else {}
    gab = load(idu, "gabarit_outil") or {}
    taxe = load(idu, "taxe_prefill") or {}
    fai = load(idu, "faisabilite") or {}
    cap = g(fai, "capacite", default={}) or {}
    four = g(cap, "fourchette", default={}) or {}
    dossier = txt(idu, "dossier")

    N = {}
    # surface terrain (contenance)
    N["surface_terrain_m2"] = {
        "fiche.contenance_m2": g(fiche, "contenance_m2"),
        "fiche.surface_terrain_m2": g(fiche, "surface_terrain_m2"),
        "compare.surface_m2": cmp0.get("surface_m2"),
        "gabarit.surfaceParcelleM2": gab.get("surfaceParcelleM2"),
        "taxe.surface_terrain_m2": taxe.get("surface_terrain_m2"),
    }
    # zone dominante
    N["zone"] = {
        "fiche.reglement_plu.zones[0]": g(fiche, "reglement_plu", "zones", 0, "zone"),
        "compare.zone": cmp0.get("zone"),
        "taxe.zone_plu": taxe.get("zone_plu"),
        "faisa.capacite.zone": cap.get("zone"),
    }
    # hauteur max (règle)
    N["hauteur_max"] = {
        "fiche.regles_valeurs.hauteur": regles_valeur(fiche, "hauteur"),
        "gabarit.hauteurReglementaireM": gab.get("hauteurReglementaireM"),
        "faisa.fourchette.hauteur_m": four.get("hauteur_m"),
    }
    # emprise / CES
    N["emprise_ces"] = {
        "fiche.regles_valeurs.emprise": regles_valeur(fiche, "emprise"),
        "gabarit.plafondEmpriseM2": gab.get("plafondEmpriseM2"),
        "compare.emprise_ces_pct": cmp0.get("emprise_ces_pct"),
    }
    # reculs
    N["recul_limites"] = {
        "fiche.regles_valeurs.recul_limites": regles_valeur(fiche, "recul_limites"),
    }
    N["recul_voirie"] = {
        "fiche.regles_valeurs.recul_voirie": regles_valeur(fiche, "recul_voirie"),
    }
    # SDP
    N["sdp_max_m2"] = {
        "faisa.fourchette.surface_plancher_m2": four.get("surface_plancher_m2"),
        "compare.sdp_max_m2": cmp0.get("sdp_max_m2"),
        "taxe.sdp_gabarit_m2": taxe.get("sdp_gabarit_m2"),
        "gabarit.zoneImplantationM2": gab.get("zoneImplantationM2"),
    }
    # niveaux max
    N["niveaux_max"] = {
        "faisa.fourchette.niveaux_max": four.get("niveaux_max"),
        "compare.gabarit_niveaux_max": cmp0.get("gabarit_niveaux_max"),
    }
    # prix median
    N["prix_median_eur_m2"] = {
        "fiche.prix_ancien.median": g(fiche, "prix_ancien", "median"),
        "faisa.marche.median": g(fai, "marche", "median"),
        "compare.prix_secteur_bati_m2": cmp0.get("prix_secteur_bati_m2"),
    }
    # nb ventes + rayon
    N["prix_n_ventes"] = {
        "fiche.prix_ancien.n": g(fiche, "prix_ancien", "n"),
        "faisa.marche.n": g(fai, "marche", "n"),
    }
    N["prix_rayon_m"] = {
        "fiche.prix_ancien.radius_m": g(fiche, "prix_ancien", "radius_m"),
        "faisa.marche.radius_m": g(fai, "marche", "radius_m"),
    }
    # TA taux communal
    N["ta_taux_communal_pct"] = {
        "fiche.taxe_amenagement.taux_communal_pct": g(fiche, "taxe_amenagement", "taux_communal_pct"),
        "taxe.taux_communal_pct": taxe.get("taux_communal_pct"),
    }
    # propriétaire (type)
    N["proprietaire_type"] = {
        "compare.proprietaire": cmp0.get("proprietaire"),
        "courrier.destinataire": g(load(idu, "courrier_apercu") or {}, "destinataire"),
    }
    # aléas: nb + %PPR interdiction
    aleas = g(fiche, "aleas", "liste", default=[]) or []
    ppr_rouge = [a for a in aleas if "rouge" in (a.get("nature", "") + a.get("libelle", "")).lower()
                 or "interdiction" in (a.get("libelle", "")).lower()]
    N["aleas_n"] = {
        "fiche.aleas.n": g(fiche, "aleas", "n"),
        "fiche.aleas.liste_len": len(aleas),
        "pieges.n": g(load(idu, "pieges_risques") or {}, "n"),
    }
    N["ppr_rouge_part_pct"] = {
        "fiche.aleas(rouge).part_pct": ppr_rouge[0].get("part_pct") if ppr_rouge else None,
        "fiche.aleas(rouge).redhibitoire": ppr_rouge[0].get("redhibitoire") if ppr_rouge else None,
    }
    return N


def divergents(N: dict) -> list[str]:
    out = []
    for notion, readers in N.items():
        vals = {k: v for k, v in readers.items() if v is not None}
        if len(vals) < 2:
            continue
        uniq = set()
        for v in vals.values():
            uniq.add(round(v, 1) if isinstance(v, float) else v)
        if len(uniq) > 1:
            out.append(f"  ⚠ {notion}: " + " | ".join(f"{k}={v}" for k, v in vals.items()))
    return out


if __name__ == "__main__":
    idus = sys.argv[1:] or sorted(p.name for p in RACINE.iterdir() if p.is_dir())
    for idu in idus:
        N = extraire(idu)
        div = divergents(N)
        print(f"\n===== {idu} ({len(div)} divergences candidates) =====")
        for line in div:
            print(line)
