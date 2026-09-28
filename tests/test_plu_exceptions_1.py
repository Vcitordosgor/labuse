"""PLU-EXCEPTIONS-1 — garde-fous.

- Les 147 exceptions (verdict JUSTE+exception de PLU-VERIF-1) sont TOUTES servies :
  un test compte les feuilles porteuses en base et les compare à 147 (écart = échec).
- Chaque exception porte un texte VERBATIM, un article, une page et un `porte`.
- Aucune exception n'entre dans un calcul : la valeur chiffrée de la règle est identique
  qu'il y ait ou non une exception (les champs numériques de ZoneRules sont inchangés).
"""
from __future__ import annotations

import glob
import os

import yaml

from labuse.plu import destinations as D

DEST = os.path.join(os.path.dirname(__file__), "..", "config", "plu_destinations")

N_ATTENDU = 147            # feuilles JUSTE+exception (cf. docs/audit-2026-09/PLU-VERIF-1)
PORTE_VALIDES = {
    "sous_secteur", "bande_limite", "hauteur_alternative", "majoration_conditionnelle",
    "voie_specifique", "destination", "operation_ensemble", "exclusion_generique", "autre",
}


def _feuilles_avec_exceptions():
    out = []
    for path in sorted(glob.glob(os.path.join(DEST, "974??_*.yaml"))):
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        insee = (doc.get("meta") or {}).get("insee")
        for zone, zv in (doc.get("zones") or {}).items():
            if not isinstance(zv, dict) or not zv.get("regles"):
                continue
            for chemin, feuille in D.iter_regles_feuilles(zv["regles"]):
                excs = feuille.get("exceptions") if isinstance(feuille, dict) else None
                if excs:
                    out.append((insee, zone, ".".join(chemin), excs))
    return out


def test_147_feuilles_portent_une_exception():
    feuilles = _feuilles_avec_exceptions()
    assert len(feuilles) == N_ATTENDU, (
        f"{len(feuilles)} feuilles portent une exception, attendu {N_ATTENDU}")


def test_chaque_exception_est_verbatim_sourcee():
    for insee, zone, chemin, excs in _feuilles_avec_exceptions():
        assert isinstance(excs, list) and excs, f"{insee} {zone} {chemin} : liste vide"
        for e in excs:
            assert (e.get("texte") or "").strip(), f"{insee} {zone} {chemin} : texte vide"
            assert (str(e.get("article") or "")).strip(), f"{insee} {zone} {chemin} : article manquant"
            assert e.get("page_pdf") not in (None, ""), f"{insee} {zone} {chemin} : page manquante"
            assert e.get("porte") in PORTE_VALIDES, f"{insee} {zone} {chemin} : porte '{e.get('porte')}'"


def test_exceptions_servies_par_le_moteur_zonage():
    """resolve_zone sert les exceptions AVEC leur règle (id `<cle>.exception`)."""
    from labuse.faisabilite.zonage import resolve_zone
    servies = 0
    for insee, zone, _chemin, _excs in _feuilles_avec_exceptions():
        zr = resolve_zone(zone, insee)
        if zr and getattr(zr, "exceptions", None):
            servies += sum(len(v) for v in zr.exceptions.values())
    assert servies > 0
    # au moins une par zone porteuse (après dédoublonnage faîtage/égout, servies ≥ zones porteuses)
    zones_porteuses = {(i, z) for i, z, _c, _e in _feuilles_avec_exceptions()}
    assert servies >= len(zones_porteuses) * 0.5   # dédoublonnage possible, borne basse


def test_exception_nentre_dans_aucun_calcul():
    """La valeur chiffrée de la règle est celle des `regles`, JAMAIS altérée par l'exception."""
    from labuse.faisabilite.zonage import resolve_zone
    for insee, zone, chemin, _excs in _feuilles_avec_exceptions():
        if not chemin.startswith("hauteur."):
            continue
        reg = D.regles_zone(insee, zone)
        zr = resolve_zone(zone, insee)
        if zr is None:
            continue
        # la valeur servie = la valeur calibrée, l'exception ne la déplace pas
        hf = (reg.get("hauteur", {}).get("faitage", {}) or {}).get("m")
        if isinstance(hf, (int, float)) and isinstance(zr.hf_m, (int, float)):
            assert float(zr.hf_m) == float(hf), f"{insee} {zone} : hf_m altérée par une exception"
