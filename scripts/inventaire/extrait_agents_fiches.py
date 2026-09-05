#!/usr/bin/env python3
"""CIRCUIT-0 Lot 7 (7.2) — agents_fiches.csv : le brief de départ d'un agent de veille pour
CHAQUE réservoir NON surveillé de reservoirs.csv (colonne sentinelle=non). Dérivé du CSV du
Lot 1 (jamais retapé). `page_rendue_en_js` : AUCUN appel HTTP n'est autorisé par le mandat →
DOUTE partout sauf connaissance portée par le code/les notes (portails ODS/data.gouv = api
JSON connue → non). `format_du_millesime` : lu des notes/millésimes en base, sinon DOUTE.
"""
from __future__ import annotations

import csv
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"
OUT = INV / "agents_fiches.csv"

#: connaissances PORTÉES PAR LE CODE/LES NOTES (jamais des suppositions réseau).
#: piste = première marche concrète pour un agent ; js = page amont rendue en JS (si su).
K = {
 "gpu_plu_api_carto": dict(fmt="aucun millésime global (gid/insee seulement)", js="non",
    piste="témoin par géométrie commune par commune (sentinelle.py:501 : détecterait un changement de PLU)"),
 "region_ods_hub": dict(fmt="datasets ODS (modified par jeu)", js="non",
    piste="sonder jeu par jeu via l'API explore/v2.1 (le hub n'est pas un jeu)"),
 "peigeo_hub": dict(fmt="aucun (WordPress, plus de CSW)", js="DOUTE",
    piste="abandonner le hub ; suivre les jeux AGORAH individuellement s'ils réapparaissent"),
 "deal_wms_wfs": dict(fmt="aucune URL amont datée", js="DOUTE",
    piste="GetCapabilities Lizmap par projet ; sinon considérer couvert par QPV/PPR"),
 "geoplateforme_hub": dict(fmt="GetCapabilities sans updateSequence", js="non",
    piste="suivre les PRODUITS IGN par leurs jeux data.gouv (déjà fait pour BD TOPO/ORTHO…)"),
 "rpg_proxy_ign": dict(fmt="RPG.LATEST (année non pinnée)", js="non",
    piste="lire l'année du GetCapabilities WFS RPG ou du jeu data.gouv RPG"),
 "osm_overpass": dict(fmt="flux continu (planet)", js="non",
    piste="pas de veille utile : interrogé en direct (sentinelle.py:507)"),
 "recherche_entreprises_dinum": dict(fmt="état courant (agrégat)", js="non",
    piste="déjà couvert par la veille SIRENE data.gouv (sentinelle.py:505)"),
 "inpi_rne": dict(fmt="API authentifiée par SIREN", js="non",
    piste="témoin authentifié sur un SIREN stable si un compte de service existe"),
 "inpn_espaces_proteges": dict(fmt="pas de jeu national à millésime trouvé", js="DOUTE",
    piste="re-chercher un jeu data.gouv « espaces protégés » ; sinon témoin WFS patrinat"),
 "cinquante_pas_deal": dict(fmt="cadastre 1877 géoréférencé (quasi statique)", js="DOUTE",
    piste="considérer statique ; revisite annuelle manuelle"),
 "zfang": dict(fmt="JORFTEXT (nouvel id à chaque texte)", js="DOUTE",
    piste="veille data.gouv « ZFANG » périodique + alerte Légifrance manuelle"),
 "frr_ex_zrr": dict(fmt="JORFTEXT", js="DOUTE", piste="idem ZFANG (textes)"),
 "pvgis": dict(fmt="version d'API dans l'URL (v5_3)", js="non",
    piste="témoin : la version dans l'URL change → nouvelle major (sentinelle.py:526)"),
 "radar_pige": dict(fmt="collecte humaine", js="non", piste="rappel Y4 déjà posé (7 j) — pas d'agent"),
 "spanc_epci": dict(fmt="champ manuel", js="DOUTE", piste="rappel Y4 (365 j) — pas d'agent"),
 "fichiers_fonciers_cerema": dict(fmt="millésime annuel sous convention", js="DOUTE",
    piste="suivre datafoncier.cerema.fr (page publique des millésimes) une fois la convention signée"),
 "mobpro": dict(fmt="millésime RP", js="non", piste="abandonné — pas d'agent (sentinelle.py:523)"),
 "office_eau_chroniques": dict(fmt="chronique numérotée (n°149), nouvelle URL par édition", js="DOUTE",
    piste="page de listing des Chroniques si elle existe ; sinon rappel annuel (posé)"),
 "sudocuh": dict(fmt="état des lieux annuel au 31/12", js="non",
    piste="last_update du jeu data.gouv Sudocuh (API dataset)"),
 "gpu_zonage_assainissement": dict(fmt="idurba par commune", js="non",
    piste="témoin info-surf par commune (même logique que le PLU)"),
 "reunion_express_cndp": dict(fmt="documents du débat public (19/08→26/11/2026)", js="DOUTE",
    piste="entete sur la page projet CNDP (déjà en base : methode entete posée le 05/09)"),
}

DEFAUT = dict(fmt="DOUTE", js="DOUTE", piste="identifier une URL amont datée (aucune connue au code)")

HEADER = ["id", "url_producteur_connue", "format_du_millesime", "raison_non_surveillee",
          "page_rendue_en_js", "piste"]


def main() -> None:
    rows = []
    with (INV / "reservoirs.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["sentinelle"] == "oui":
                continue
            k = K.get(r["id"], DEFAUT)
            rows.append({
                "id": r["id"], "url_producteur_connue": r["url_producteur_connue"],
                "format_du_millesime": k["fmt"],
                "raison_non_surveillee": r["raison_non_surveillee"] or r["absente_motif"] or "DOUTE",
                "page_rendue_en_js": k["js"], "piste": k["piste"],
            })
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    print(f"agents_fiches.csv : {len(rows)} réservoirs non surveillés "
          f"(le mandat en attendait 28 ; l'écart vient des absentes/hors-vitrine comptées ici)")
    print("js=DOUTE :", sum(1 for r in rows if r["page_rendue_en_js"] == "DOUTE"))


if __name__ == "__main__":
    main()
