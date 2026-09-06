"""CIRCUIT-5 lot 4.4 — L'ÉCHANTILLON PRODUCTEUR DE LA FICHE COMMUNE.

Pour chacune des 15 cartes de la fiche commune et chacune des 24 communes, la valeur
ATTENDUE lue chez le producteur est stockée dans `filtres/echantillons/communes/<carte>.json`
avec son origine (URL + champ), et rejouée à chaque version comme contrôle AVERTISSANT
(jamais bloquant). Ce que CC n'a pas pu lire chez le producteur porte `a_valider: true`
avec une proposition — listé dans docs/CIRCUIT/ECHANTILLONS-A-VALIDER.md.

Le verrou V4d (structurel, sans réseau) exige que CHAQUE carte × commune ait sa ligne :
un attendu, ou un a_valider motivé — jamais un trou silencieux.
"""
from __future__ import annotations

import json
from pathlib import Path

DOSSIER = Path(__file__).parent / "echantillons" / "communes"

#: les 15 cartes de la fiche commune (robinets fiche_commune_*) → le champ du payload
#: `/communes/{commune}/contexte` qui porte la valeur comparée, et la tolérance (%).
CARTES: dict[str, dict] = {
    "population": {"champ": "population.habitants", "tolerance_pct": 15,
                   "producteur": "INSEE (population légale, geo.api.gouv.fr)",
                   "note": "servi = agrégat Filosofi carreaux 200 m (définition ≠ population "
                           "légale) — tolérance large, l'écart de définition est connu"},
    "sru": {"champ": "sru.taux_lls", "tolerance_pct": 0.5,
            "producteur": "DHUP — inventaire SRU (transparence-logement-social.gouv.fr)"},
    "qpv": {"champ": "qpv[].len", "tolerance_pct": 0,
            "producteur": "ANCT — liste des QPV génération 2024 (sig.ville.gouv.fr)"},
    "regles_urbanisme": {"champ": "plu_statut.statut", "tolerance_pct": 0,
                         "producteur": "Sudocuh (état des procédures au 31/12/2024)"},
    "zan": {"champ": "foncier.zan_reste_ha", "tolerance_pct": 5,
            "producteur": "portail artificialisation (Cerema, conso ENAF 2021-2024)"},
    "permis": {"champ": "permis_bloc.permis_12m", "tolerance_pct": 10,
               "producteur": "SDES Sitadel (autorisations d'urbanisme, data.gouv.fr)"},
    "plh": {"champ": "plh.objectif_logements_an", "tolerance_pct": 0,
            "producteur": "PLH des 5 EPCI (documents publiés)"},
    "prix": {"champ": "marche.prix_ancien_eur_m2", "tolerance_pct": 10,
             "producteur": "DVF (app.dvf.etalab.gouv.fr, médianes par commune)"},
    "terrain_nu": {"champ": "marche.prix_terrain_eur_m2", "tolerance_pct": 15,
                   "producteur": "DVF (mutations terrain nu par commune)"},
    "annonces": {"champ": "marche_annonces.n", "tolerance_pct": 0,
                 "producteur": "Radar (pige manuelle) — producteur = notre collecte, "
                               "validation par recomptage humain"},
    "loyers": {"champ": "loyer.median_eur_m2", "tolerance_pct": 5,
               "producteur": "DHUP — carte des loyers (data.gouv.fr)"},
    "foncier": {"champ": "n_parcelles", "tolerance_pct": 2,
                "producteur": "DGFiP PCI (compte de parcelles par commune)"},
    "zonage": {"champ": "repartition_zonage.familles.U.pct", "tolerance_pct": 5,
               "producteur": "GPU (zones d'urbanisme par commune, geoportail-urbanisme.gouv.fr)"},
    "risques": {"champ": "risques.catnat_arretes", "tolerance_pct": 0,
                "producteur": "GASPAR — arrêtés CatNat par commune (georisques.gouv.fr)"},
    "mairie": {"champ": "mairie.telephone", "tolerance_pct": 0,
               "producteur": "service-public.fr (annuaire de l'administration)"},
}


def charger(carte: str) -> dict:
    p = DOSSIER / f"{carte}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def problemes_structure() -> list[str]:
    """V4d — chaque carte × 24 communes a sa ligne (attendu OU a_valider motivé)."""
    from .cadre import INSEE_24
    pbs: list[str] = []
    for carte in CARTES:
        doc = charger(carte)
        lignes = {l.get("insee"): l for l in doc.get("lignes", [])}
        if not doc:
            pbs.append(f"carte {carte} : fichier absent ({DOSSIER}/{carte}.json)")
            continue
        for insee in INSEE_24:
            l = lignes.get(insee)
            if l is None:
                pbs.append(f"carte {carte} : commune {insee} sans ligne")
            elif l.get("attendu") is None and not l.get("a_valider"):
                pbs.append(f"carte {carte} : commune {insee} sans attendu ni a_valider")
    return pbs


def _lire_champ(payload: dict, chemin: str):
    """`population.habitants` · `qpv[].len` (longueur de liste) — accès pointé simple."""
    if chemin.endswith("[].len"):
        v = payload.get(chemin[: -len("[].len")])
        return len(v) if isinstance(v, list) else None
    cur = payload
    for part in chemin.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def rejouer(payload_par_insee: dict[str, dict]) -> list[dict]:
    """Le contrôle AVERTISSANT : compare chaque attendu (non nul) à la valeur servie.
    `payload_par_insee` : insee → payload de `/communes/{commune}/contexte`.
    Rend les lignes {carte, insee, attendu, servi, verdict} (verdict ok|ecart|non_servi)."""
    sorties: list[dict] = []
    for carte, spec in CARTES.items():
        doc = charger(carte)
        for l in doc.get("lignes", []):
            attendu = l.get("attendu")
            if attendu is None:
                continue
            payload = payload_par_insee.get(l["insee"])
            if payload is None:
                continue
            servi = _lire_champ(payload, spec["champ"])
            if servi is None:
                verdict = "non_servi"
            elif isinstance(attendu, (int, float)) and isinstance(servi, (int, float)):
                tol = float(spec.get("tolerance_pct") or 0)
                ecart = abs(float(servi) - float(attendu))
                verdict = "ok" if ecart <= abs(float(attendu)) * tol / 100 + 1e-9 else "ecart"
            else:
                verdict = "ok" if str(servi).strip() == str(attendu).strip() else "ecart"
            if verdict == "ecart" and l.get("ecart_assume"):
                verdict = "assume"      # écart de définition CONNU et motivé (note de la ligne)
            sorties.append({"carte": carte, "insee": l["insee"], "attendu": attendu,
                            "servi": servi, "verdict": verdict, "note": l.get("note")})
    return sorties
