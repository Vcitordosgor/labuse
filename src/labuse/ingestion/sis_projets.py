"""SOURCES-2 lot 2 — les PROJETS de SIS Nord-Est et Sud (préfecture de La Réunion).

Le producteur : seuls les SIS DÉFINITIFS arrivent sur Géorisques (CSV quotidien, canal SSP
déjà servi — kind='sol_pollue' subtype='sis'). Les secteurs Nord-Est et Sud sont encore À
L'ÉTAT DE PROJET : arrêtés préfectoraux n°2026-215/216/217/218-SG-SCOPP du 19/02/2026
(modifiés 2026-405/406 du 02/04/2026), consultation électronique du 7 avril au 7 mai 2026
(close). Le dossier officiel (ZIP préfecture, `reunion.gouv.fr`) contient 7 fiches de sites
« Plateforme de gestion des données relatives aux risques de pollution des sols » — extraites
le 13/09/2026 (id SSP, commune, centroïde EPSG:2975, superficie, date de génération).

Ces projets sont servis **distincts des SIS définitifs** : subtype='sis_projet', statut
« projet de SIS — non opposable » TOUJOURS affiché. 6 sites sur 7 portent un centroïde
EPSG:2975 exploitable ; la fiche « Pipe line SRE » (Le Port, linéaire) publie des coordonnées
dans un CRS non identifié (10 162 963 / 517 213 — ni 2975, ni 3857, ni 32740) : AUCUN point
n'est inventé pour elle, l'anomalie est dite au rapport SOURCES-2.

La donnée est FIGÉE côté préfecture (consultation close, on attend les arrêtés de création,
qui arriveront par Géorisques) — l'extraction du dossier est gravée ici avec sa provenance ;
la sentinelle `entete` sur le ZIP préfecture détecte toute republication du dossier.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .layers_ingest import _insert_layer

SOURCE_SIS = "Géorisques — secteurs d'information sur les sols (SIS)"
DOSSIER_ZIP = ("https://www.reunion.gouv.fr/contenu/telechargement/51477/389074/file/"
               "dossier%20SIS%20actualis%C3%A9.zip")
STATUT = "projet de SIS — non opposable (consultation close le 7 mai 2026)"

#: extraits VÉRIFIÉS des 7 fiches du dossier préfecture (13/09/2026). x/y en EPSG:2975.
PROJETS: list[dict] = [
    {"id": "SSP6801890101", "nom": "CORETAB", "insee": "97416", "commune": "Saint-Pierre",
     "x": 341654.6, "y": 7641775.5, "superficie_m2": 14770, "genere": "2025-12-10"},
    {"id": "SSP00073310101", "nom": "Décharge Petite Plaine", "insee": "97406",
     "commune": "La Plaine-des-Palmistes", "x": 354534.3, "y": 7660752.2,
     "superficie_m2": 3493, "genere": "2025-12-10"},
    {"id": "SSP6805470101", "nom": "Interlinge", "insee": "97415", "commune": "Saint-Paul",
     "x": 319626.5, "y": 7674009.7, "superficie_m2": 1699, "genere": "2025-12-10"},
    {"id": "SSP00073920102", "nom": "PIPE LINE SRE", "insee": "97407", "commune": "Le Port",
     "x": None, "y": None, "superficie_m2": 2242, "genere": "2025-12-10"},   # CRS inconnu — pas de point
    {"id": "SSP6801940201", "nom": "SCPR", "insee": "97414", "commune": "Saint-Louis",
     "x": 334154.2, "y": 7644285.0, "superficie_m2": 41011, "genere": "2025-12-10"},
    {"id": "SSP00079460401", "nom": "SUCRERIE-DISTILLERIE DE SAVANNA", "insee": "97415",
     "commune": "Saint-Paul", "x": 323169.7, "y": 7678213.2, "superficie_m2": 9476,
     "genere": "2025-12-10"},
    {"id": "SSP42640890101", "nom": "ZAC Triangle de l'Oasis", "insee": "97407",
     "commune": "Le Port", "x": 323097.3, "y": 7683449.9, "superficie_m2": 52970,
     "genere": "2026-03-25"},
]


def ingest_sis_projets(session: Session, source_id: int | None = None,
                       run_id: int | None = None, log=print) -> dict:
    """Projets de SIS → kind='sol_pollue', subtype='sis_projet' (points EPSG:2975 → 4326).

    Idempotent (purge du subtype). Le site sans CRS identifiable n'est PAS posé sur la carte
    (jamais un point inventé) — il reste compté au rapport."""
    session.execute(text(
        "DELETE FROM spatial_layers WHERE kind = 'sol_pollue' AND subtype = 'sis_projet'"))
    n = sans_point = 0
    for pjt in PROJETS:
        if pjt["x"] is None:
            sans_point += 1
            log(f"  ⚠ {pjt['nom']} ({pjt['id']}) : coordonnées du PDF dans un CRS non "
                "identifié — aucun point posé (dit au rapport)")
            continue
        lon, lat = session.execute(text(
            "SELECT ST_X(g), ST_Y(g) FROM (SELECT ST_Transform("
            "ST_SetSRID(ST_Point(:x,:y),2975),4326) AS g) q"),
            {"x": pjt["x"], "y": pjt["y"]}).first()
        geom = {"type": "Point", "coordinates": [lon, lat]}
        _insert_layer(
            session, "sol_pollue", "sis_projet",
            f"Projet de SIS — {pjt['nom']}", geom, source_id, pjt["commune"], run_id,
            attrs={"identifiant_ssp": pjt["id"], "code_insee": pjt["insee"],
                   "statut": STATUT, "superficie_m2": pjt["superficie_m2"],
                   "arretes": "n°2026-215/216/217/218-SG-SCOPP du 19/02/2026, "
                              "modifiés n°2026-405/406 du 02/04/2026",
                   "dossier": DOSSIER_ZIP, "fiche_generee_le": pjt["genere"],
                   "source": "Préfecture de La Réunion — dossier de consultation SIS"})
        n += 1
    session.flush()
    return {"projets": n, "sans_point": sans_point, "total_fiches": len(PROJETS)}
