"""DONNEES-4 — L'ORACLE INDÉPENDANT du Dossier.

`preuve_ecran_pdf.py` comparait les extracteurs (`robinet_fiche.py`) au PDF rendu DEPUIS ces
mêmes extracteurs : un extracteur qui lit une mauvaise clé renvoie None, et « absent au Dossier =
absent à l'écran » passait pour conforme (c'est ce qui a caché le bug OCS GE `artif_pct`).

Cet oracle lit la valeur **là où la fiche React la lit** (le chemin du COMPOSANT, relevé du code
front, PAS celui de l'extracteur). Règle : si le payload porte une valeur au chemin du composant et
que l'extracteur renvoie None → **écart « extracteur muet »**.

`ORACLE` : donnée → chemin(s) `f` du composant React (le premier présent gagne). Un chemin pointe
la FEUILLE affichée (scalaire) ou le CONTENEUR de liste (présent = liste/objet non vide). Trois
cas hors oracle, déclarés (`HORS_PAYLOAD`), car la fiche React les rend depuis une AUTRE requête
(pas le payload `/parcels/{idu}`) : l'oracle ne peut pas les confronter au `f` du Dossier.
"""
from __future__ import annotations

from typing import Any

#: donnée → chemins `f` (dotted) où le COMPOSANT React lit la valeur (relevé DONNEES-4, deux
#: traçages front indépendants). Plusieurs chemins = repli (a ?? b). Liste → présence = non-vide.
ORACLE: dict[str, tuple[str, ...]] = {
    "surface_parcelle_m2": ("surface_m2",),
    "adresse_ban": ("adresse",),
    "pente_deg": ("terrain.pente_moy_deg",),
    "emprise_batie_m2": ("le_bien.emprise_batie_m2",),
    "hauteur_bati_m": ("le_bien.hauteur_faitage_m", "le_bien.hauteur_bati_m"),
    "n_batiments": ("le_bien.nb_batiments",),
    "surface_libre_sol_m2": ("le_bien.surface_libre_m2",),
    "cosia_detecte_m2": ("le_bien.cosia_detecte_m2",),
    "part_artificialisee_pct": ("le_bien.ocsge.part_artif_pct",),
    "usage_sol_dominant": ("le_bien.ocsge.us_dominant",),
    "part_impermeabilisee_cosia_pct": ("le_bien.cosia_couverture.part_impermeabilisee_pct",),
    "part_vegetalisee_cosia_pct": ("le_bien.cosia_couverture.part_vegetalisee_boisee_pct",),
    "part_sol_nu_cosia_pct": ("le_bien.cosia_couverture.part_sol_nu_pct",),
    "pente_toit_deg": ("le_bien.toit.pente_mediane_deg",),
    "nature_toit": ("le_bien.toit.libelle",),
    "dpe_connu": ("dpe_connu.etiquette",),
    "rnb_batiments_liste": ("le_bien.rnb",),
    "ban_plus_adresses_bati": ("le_bien.adresses_bati.adresses", "le_bien.adresses_bati.liens"),
    "potentiel_verdict": ("potentiel_transformation.niveau", "potentiel_transformation.libelle"),
    "sdp_residuelle_m2": ("potentiel_transformation.sdp_residuelle_m2",),
    "surface_plancher_m2": ("potentiel_transformation.surface_plancher_m2",),
    "surface_vendable_m2": ("potentiel_transformation.surface_vendable_m2",),
    "marge_surelevation_m": ("potentiel_transformation.hauteur_marge_m",),
    "zone_plu_famille": ("reglement_plu.zones",),
    "reglement_plu_bloc": ("reglement_plu.zones",),
    "statut_plu": ("plu_fraicheur.statut", "plu_fraicheur.libelle"),
    "er_emplacement_reserve": ("dispositifs.er",),
    "ebc_classe": ("dispositifs.ebc",),
    "dispositifs_parcelle": ("dispositifs.sup",),
    "mixite_clause": ("mixite_clause",),
    "aleas_parcelle_liste": ("aleas.liste",),
    "sis_classe": ("sols.sis",),
    "casias_statut": ("sols.casias",),
    "sols_parcelle": ("sols.sis", "sols.casias"),
    "viabilisation_verdict": ("viabilisation.band", "viabilisation.libelle"),
    "type_proprietaire": ("proprietaire_moral",),
    "proprietaire_timeline_liste": ("proprietaire_historique.millesimes",),
    "prix_achat_historique_eur": ("dvf_parcelle.derniere_mutation.valeur",),
    "coproprietes_liste": ("coproprietes",),
    "filiation_parcelle": ("filiation.meres", "filiation.filles"),
    "historique_permis_liste": ("historique_site.permis",),
    "distance_arret_m": ("proximites.arret.distance_m",),
    "tcsp_stationnement_allege": ("proximites.tcsp.sous_800m",),
    "part_logements_egout_pct": ("anc.part_egout_pct", "anc.statut"),
    "fibre_parcelle": ("fibre.ftth",),
    "perimetres_dispositifs_liste": ("territoire_fiscal.perimetres",),
    "taxe_amenagement_estimee_eur": ("taxe_amenagement.taux_communal_pct",),
    "tfpb_taux_pct": ("fiscalite.tfpb_commune_pct",),
    "prix_sortie_bati_eur_m2": ("prix_ancien.median",),
    "prix_terrain_secteur_eur_m2": ("mode_b.terrain_nu.prix_m2",),
    "ventes_retenues_n": ("prix_ancien.n",),
    "ventes_ecartees_n": ("prix_ancien.n_exclus",),
    "dvf_parcelle_liste": ("dvf_parcelle.secteur",),
    "prix_neuf_vefa_acte_eur_m2": ("dvf_parcelle.neuf_vefa.mediane_prix_m2_bati",),
    "radar_annonces_liste": ("radar_annonces.liste",),
    "ventes_100m_n": ("voisinage_proche.ventes_dvf",),
    "voisinage_100m_liste": ("voisinage_proche.ventes_dvf",),
    "iris_quartier": ("iris_quartier.logements",),
    "equipements_proximite_liste": ("proximites_equipements.items",),
    "tier_opportunite": ("score_v2.label", "score_v2.tier"),
    "rang_tier": ("score_v2.rang",),
}

#: rendues par la fiche React depuis une AUTRE requête que `/parcels/{idu}` (getFaisabilite,
#: getParcelExposition, getOrthoEquipements, /v2/score, modParcellePermis) ou via `f.lines`
#: (couche générique) : l'oracle du payload `f` ne peut pas les confronter à l'écran — DÉCLARÉ.
HORS_PAYLOAD: dict[str, str] = {
    "exposition_versant": "React getParcelExposition(idu) — hors payload /parcels",
    "piscine_m2": "React getOrthoEquipements(idu) — hors payload /parcels",
    "capacite_logements": "React getFaisabilite(idu).logements_au_sol — hors payload /parcels "
                          "(f.potentiel_transformation.capacite_estimee n'est qu'un drapeau)",
    "prod_spec_kwh_kwc": "non rendu en fiche (outil Prospection solaire, autre payload)",
    "n_permis_proximite": "React modParcellePermis(idu) + extracteur = requête DB live, hors payload",
    "sar_divergence": "rendu via f.lines (couche générique), pas de feuille dédiée",
    "endiguement_zone_protegee": "rendu via f.lines (couche générique), pas de feuille dédiée",
    "n_vigilances": "compté de f.lines (onglet risques) côté React ; extracteur = f.flags",
    "run_label_servi": "non rendu en fiche (annexe sources / admin)",
    "rtaa_exigences": "React getFaisabilite(idu).rtaa — hors payload /parcels",
}


def _dpu_affiche(f: Any) -> Any:
    """React (constructibilite.tsx) n'affiche une LIGNE DPU que si etat=='servi' ; 'hors' /
    'non_determinee' ne sont qu'une note contextuelle (pas une valeur) — l'extracteur fait pareil."""
    d = (f.get("dispositifs") or {}).get("dpu") if isinstance(f, dict) else None
    return d.get("statut") or "servi" if isinstance(d, dict) and d.get("etat") == "servi" else None


def _peb_affiche(f: Any) -> Any:
    """React n'affiche une LIGNE PEB que pour une zone A/B/C/D ; 'hors' / non déterminée = note."""
    d = (f.get("dispositifs") or {}).get("peb") if isinstance(f, dict) else None
    z = d.get("zone") if isinstance(d, dict) else None
    return z if z in ("A", "B", "C", "D") else None


#: données dont l'affichage React est CONDITIONNEL (une note ≠ une valeur) : l'oracle réplique la
#: condition d'affichage pour ne pas confondre un sentinel (non_determinee/hors) avec une valeur.
ORACLE_FN = {"dpu_perimetre": _dpu_affiche, "peb_zone": _peb_affiche}


def lire(payload: Any, chemin: str) -> Any:
    """Résout un chemin dotté dans le payload. Traverse les dicts ; sur une liste, rend la liste
    (présence = non-vide). Rend None si un maillon manque."""
    cur = payload
    for k in chemin.split("."):
        if isinstance(cur, list):
            return cur or None            # liste atteinte avant la fin du chemin : présence brute
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def present(v: Any) -> bool:
    """Une valeur « présente » (que l'écran afficherait) : non None, liste/dict/str non vide."""
    if v is None:
        return False
    if isinstance(v, (list, dict, str)):
        return len(v) > 0
    return True


def valeur_oracle(payload: Any, cid: str) -> Any:
    """La valeur au chemin/condition du composant React (premier chemin présent), ou None."""
    if cid in ORACLE_FN:
        v = ORACLE_FN[cid](payload)
        return v if present(v) else None
    for chemin in ORACLE.get(cid, ()):
        v = lire(payload, chemin)
        if present(v):
            return v
    return None
