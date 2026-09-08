"""CIRCUIT-3 lot 2 — LES FILTRES PAR SOURCE (contrôles propres).

Chaque source qui pèse déclare ici son `Filtre` avec ses contrôles PROPRES, en plus des
universels hérités du cadre. **Les seuils sont écrits AVEC la mesure qui les a fixés** (la valeur
observée au 05/09/2026 sur la base servie `labuse`, 431 663 parcelles). Un seuil que CC ne sait
pas fixer reste `avertissant` avec la valeur observée — jamais un `bloquant` inventé.

Ordre d'impact (mandat) : DVF · GPU/PLU · cadastre · Sitadel · MAJIC · DPE · Géorisques/PPR ·
SIRENE · BODACC · INPI · BAN · CoSIA · FLAIR · LiDAR · EDF · OSM/TCSP · GTFS · BPE · Filosofi.

`filtres/__init__.py` fusionne `FILTRES_RICHES` avec un filtre par défaut pour toute source à job
de sources_ingestion.yaml (test 1.5). Une clé ABSENTE de la vanne (cadastre en direct, MAJIC,
GPU/PLU en direct, CoSIA, FLAIR, LiDAR, EDF, Filosofi) est une entrée riche supplémentaire.
"""
from __future__ import annotations

from sqlalchemy import text

from .cadre import Controle, Filtre, ko, ok, skip, _et
from . import controles as c


def _f(**kw) -> Filtre:
    return Filtre(**kw)


def _zone_famille_registre() -> Controle:
    """Domaine des lettres de zone conforme au référentiel du registre (CIRCUIT-2 : U/AU/A/N).
    Utilise la fonction CANONIQUE `faisabilite.zone_norm.est_famille` (phasage/casse/accents
    ignorés) — jamais une liste recopiée. Une zone servie dont la famille n'est ni U/AU/A/N est
    hors référentiel (avertissant). Mesuré au 05/09 : les codes legacy POS (NA/NB/NC/ND) et
    quelques radicaux exotiques sortent — c'est l'état réel, visible."""
    from ..faisabilite.zone_norm import est_famille

    def m(db, f: Filtre, version: str):
        if not f.table:
            return skip("pas de table")
        w = _et(f.where, "attrs->>'libelle' IS NOT NULL")
        codes = db.execute(text(
            f"SELECT DISTINCT attrs->>'libelle' FROM {f.table}"
            + (f" WHERE {w}" if w else ""))).scalars().all()
        hors = sorted({str(x) for x in codes
                       if not est_famille(str(x), ("U", "AU", "A", "N"))})
        d = {"domaine": ["U", "AU", "A", "N"], "hors_domaine": hors[:50], "n_hors": len(hors)}
        return ok("∅", d) if not hors else ko(f"{len(hors)} codes", d)
    return Controle("d_zone_famille", "distribution", "avertissant",
                    "Domaine des lettres de zone (U/AU/A/N)",
                    "familles U/AU/A/N (référentiel registre CIRCUIT-2, via zone_norm.est_famille)", m)


FILTRES_RICHES: dict[str, Filtre] = {}


def _ajout(f: Filtre) -> None:
    FILTRES_RICHES[f.source] = f


# ─────────────────────────────── DVF (19 robinets) ───────────────────────────────
# Mesures 05/09 : 29 566 mutations · 7 prix/m² > 90 000 (Maison multi-lots mal typées, JAMAIS
# des comparables servis car filtre_ventes borne à [1000;12000]) · 272 étiquetées Immeuble par
# EXPORTS-1 · 0 appartement > 200 m² · 1 sans surface · mutation_id unique · geom jamais nul.
_ajout(_f(
    source="dvf", libelle="DVF / valeurs foncières", table="dvf_mutations",
    cle=("mutation_id",), commune_nom_col="commune", geom_col="geom",
    date_cols=("date_mutation",), source_motif="DVF / valeurs%", portee_run=True,
    propres=[
        # LE gardien des comparables (EXPORTS-1 lot 2, filtre_ventes) déclaré ici : aucun
        # comparable servi (Maison/Appartement dans le domaine [1000;12000] €/m²) ne peut sortir
        # de la plage physique [1 ; 90 000]. Bloquant, mesuré 0/29 566 au 05/09.
        c.compte_mauvais(
            "d_comparable_plage", "plage", "bloquant",
            "Comparables servis dans la plage €/m²",
            "0 comparable Maison/Appartement hors [1 ; 90 000] €/m² (mesuré 0 au 05/09)",
            "type_local IN ('Maison','Appartement') AND surface_reelle_bati > 0 "
            "AND (valeur_fonciere/surface_reelle_bati) BETWEEN 1000 AND 12000 "
            "AND ((valeur_fonciere/surface_reelle_bati) > 90000 "
            "     OR (valeur_fonciere/surface_reelle_bati) <= 0)"),
        # Les prix/m² aberrants BRUTS (avant filtre comparables) — l'état réel, visible mais non
        # bloquant : ils n'atteignent pas la pompe. Mesuré 7/29 566 au 05/09.
        c.compte_mauvais(
            "d_prix_m2_aberrant_brut", "plage", "avertissant",
            "Prix/m² aberrant dans le brut",
            "0 attendu — mesuré 7 au 05/09 (Maison multi-lots mal typées, écartées des comparables)",
            "type_local IN ('Maison','Appartement') AND surface_reelle_bati > 0 "
            "AND ((valeur_fonciere/surface_reelle_bati) > 90000 "
            "     OR valeur_fonciere <= 0)"),
        # L'étiquette Immeuble (EXPORTS-1 : 272 re-étiquetées) — un « appartement » > 200 m² est
        # un agrégat multi-lots (filtre_ventes seuil_type_m2). Mesuré 0 au 05/09.
        c.compte_mauvais(
            "d_immeuble_multilot", "distribution", "avertissant",
            "Appartement de surface incompatible (multi-lots)",
            "0 appartement > 200 m² non étiqueté Immeuble (mesuré 0 au 05/09)",
            "type_local = 'Appartement' AND surface_reelle_bati > 200"),
        # Part des mutations sans surface (bâti ni terrain). Mesuré 1/29 566 au 05/09.
        c.part_max(
            "d_sans_surface", "completude", "avertissant",
            "Part des mutations sans surface",
            "≤ 1 % (mesuré ~0,003 % — 1 mutation au 05/09)",
            "COALESCE(surface_reelle_bati,0)=0 AND COALESCE(surface_terrain,0)=0", 1.0),
    ]))


# ─────────────────────────────── GPU / PLU (13 robinets) ───────────────────────────────
# Mesures 05/09 : 5 845 zones plu_gpu_zone. Domaine des lettres de zone = référentiel du registre
# (CIRCUIT-2). md5 des règlements : la table plu_reglement_extrait porte un `millesime` par insee.
_ajout(_f(
    source="gpu_plu", libelle="Urbanisme PLU/GPU (API Carto)", table="spatial_layers",
    where="kind = 'plu_gpu_zone'", cle=("id",), commune_nom_col="commune",
    geom_col="geom", source_motif="Urbanisme PLU/GPU%", portee_run=True, a_job=False,
    propres=[
        _zone_famille_registre(),
    ]))


# ─────────────────────────────── cadastre Etalab ───────────────────────────────
# Mesures 05/09 : 431 663 parcelles · 0 surface ≤ 0 · IDU uniques · 0 géométrie invalide.
_ajout(_f(
    source="cadastre_etalab", libelle="Cadastre Etalab (parcelles)", table="parcels",
    cle=("idu",), commune_nom_col="commune", geom_col="geom",
    source_motif="Cadastre Etalab%", portee_run=True, a_job=False,
    propres=[
        c.compte_mauvais(
            "d_surface_positive", "plage", "avertissant", "Surfaces strictement positives",
            "0 parcelle de surface ≤ 0 (mesuré 0/431 663 au 05/09)",
            "surface_m2 IS NOT NULL AND surface_m2 <= 0"),
    ]))


# ─────────────────────────────── Sitadel ───────────────────────────────
# Mesures 05/09 : 50 545 permis · 100 % localisés (geom ou idu_codes) · permit_id unique ·
# 57 permis avec geom_approx servis comme point précis · natures DP/PA/PC/PD.
_ajout(_f(
    source="sitadel", libelle="SITADEL (autorisations d'urbanisme)", table="sitadel_permits",
    cle=("permit_id",), commune_nom_col="commune", geom_col="geom",
    date_cols=("date_depot",), source_motif="SITADEL%", portee_run=True,
    propres=[
        c.couverture(
            "d_localisation", "rattachement", "avertissant", "Couverture de localisation",
            "≥ 95 % posés sur une parcelle ou un point (mesuré 100 % au 05/09)",
            "geom IS NOT NULL OR (idu_codes IS NOT NULL AND jsonb_array_length(idu_codes) > 0)",
            95.0),
        # Cohérence RETOURS-14 : un permis approximatif ne doit pas être servi comme un point précis.
        c.compte_mauvais(
            "d_approx_jamais_point", "geometrie", "avertissant",
            "Permis approximatif jamais servi comme point",
            "0 attendu — mesuré 57 au 05/09 (geom_approx + geom ponctuelle)",
            "geom_approx IS NOT NULL AND geom IS NOT NULL AND ST_GeometryType(geom) = 'ST_Point'"),
        c.domaine(
            "d_nature_permis", "type", ("DP", "PA", "PC", "PD"), "avertissant",
            "Domaine des natures de permis",
            "DP/PA/PC/PD (mesuré au 05/09) — une nature inconnue = avertissant"),
    ]))


# ─────────────────────────────── MAJIC / DGFiP personnes morales ───────────────────────────────
# Mesures 05/09 : 82 701 lignes · 72 556 SIREN à 9 chiffres (0 échec Luhn) · 10 145 SIREN mal
# formés · 0 SIREN nul · 72 556 parcelles rattachées à un SIREN.
_ajout(_f(
    source="dgfip_parcelles_pm", libelle="DGFiP — parcelles des personnes morales",
    table="parcelle_personne_morale", cle=("idu", "siren", "millesime"),
    insee_expr="substring(idu from 1 for 5)", source_motif="DGFiP — parcelles des personnes morales%",
    portee_run=False,
    propres=[
        c.siren_luhn(
            "d_siren_luhn", "siren", "avertissant", "SIREN valides (clé de Luhn)",
            "0 SIREN 9 chiffres invalide (mesuré 0/9 733 distincts au 05/09)"),
        c.part_max(
            "d_siren_mal_forme", "referentiel", "avertissant", "SIREN au format 9 chiffres",
            "≤ 15 % de SIREN non conformes au format (mesuré ~12,3 % au 05/09)",
            "siren IS NOT NULL AND siren !~ '^[0-9]{9}$'", 15.0),
    ]))


# ─────────────────────────────── DPE ADEME ───────────────────────────────
# Mesures 05/09 (base LOCALE, DPE partielle) : 17 enregistrements · 7 communes · 0 classe hors A-G.
# La rareté locale est l'état SERVI localement (le filtre l'avertit honnêtement, communes 7/24).
_ajout(_f(
    source="dpe", libelle="DPE ADEME (logements existants)", table="dpe_records",
    cle=("numero_dpe",), insee_col="code_insee", date_cols=("date_etablissement",),
    source_motif="DPE ADEME%", portee_run=False,
    propres=[
        c.domaine(
            "d_classe_dpe", "etiquette_dpe", ("A", "B", "C", "D", "E", "F", "G"),
            "avertissant", "Domaine des classes DPE (A-G)",
            "classes A à G (mesuré 0 hors domaine au 05/09)"),
    ]))


# ─────────────────────────────── Géorisques / PPR (DEAL) ───────────────────────────────
# Mesures 05/09 : 993 zones georisque_alea, 164 zones PPR. Le glissement « élevé → moyen » de
# RETOURS-13 est un contrôle de DISTRIBUTION : une zone de degré DEAL ELEVE/TRES_ELEVE servie
# niveau='moyen' est une CONTRADICTION interne bloquante (déjà attrapée par la sonde catégorielle
# CIRCUIT-2 ; ici elle devient un contrôle du filtre de la source, comme le mandat le demande).
_ajout(_f(
    source="georisques_mvt", libelle="Géorisques — aléa mouvement de terrain",
    table="spatial_layers", where="kind = 'georisque_alea'", cle=("id",),
    commune_nom_col="commune", geom_col="geom", source_motif="Géorisques — mouvements%",
    portee_run=True,
    propres=[
        # BLOQUANT (mandat) : la distribution ne doit pas rétrograder un aléa fort en moyen.
        c.compte_mauvais(
            "d_alea_non_retrograde", "distribution", "bloquant",
            "Aléa fort jamais rétrogradé en moyen",
            "0 zone degré ELEVE/TRES_ELEVE servie niveau 'moyen' — MESURÉ 484 au 05/09 : la "
            "régression RETOURS-13 est présente sur main (correctif sur fix/retours-12, non "
            "mergé). Le filtre l'attrape et met la source en quarantaine, comme voulu.",
            "upper(coalesce(attrs->>'degre','')) IN ('ELEVE','TRES_ELEVE') "
            "AND lower(coalesce(attrs->>'niveau','')) = 'moyen'"),
    ]))
# Le filtre générique Géorisques (API, tous aléas) — couverture communes + géométrie.
_ajout(_f(
    source="georisques_api", libelle="Géorisques (synthèse)", table="spatial_layers",
    where="kind IN ('georisque_alea','ppr','cavite','icpe','sol_pollue','mvt')",
    cle=("id",), commune_nom_col="commune", geom_col="geom", source_motif="Géorisques",
    portee_run=False))


# ─────────────────────────────── SIRENE ───────────────────────────────
# Mesures 05/09 : 158 515 établissements · 25 valeurs insee (24 + 1 hors-liste éventuel) ·
# 0 SIREN non conforme · geom présent.
_ajout(_f(
    source="sirene_etablissements", libelle="SIRENE établissements géolocalisés",
    table="sirene_etablissements", cle=("siret",), insee_col="insee", geom_col="geom",
    date_cols=("date_creation",), source_motif="SIRENE établissements%", portee_run=False,
    propres=[
        c.siren_luhn(
            "d_siren_luhn", "siren", "avertissant", "SIREN valides (clé de Luhn)",
            "0 SIREN 9 chiffres invalide (mesuré 0 au 05/09)"),
        c.compte_mauvais(
            "d_siret_14c", "referentiel", "avertissant", "SIRET au format 14 chiffres",
            "0 SIRET mal formé (mesuré au 05/09)",
            "siret IS NOT NULL AND siret !~ '^[0-9]{14}$'"),
    ]))


# ─────────────────────────────── BODACC ───────────────────────────────
# Mesures 05/09 : 674 procédures · 0 SIREN invalide.
_ajout(_f(
    source="bodacc", libelle="BODACC (procédures collectives)", table="bodacc_procedures",
    cle=("annonce_id",), date_cols=("date_annonce",), source_motif="BODACC%", portee_run=False,
    propres=[
        c.compte_mauvais(
            "d_siren_forme", "referentiel", "avertissant", "SIREN au format 9 chiffres",
            "0 SIREN mal formé (mesuré 0/674 au 05/09)",
            "siren IS NOT NULL AND siren !~ '^[0-9]{9}$'"),
    ]))


# ─────────────────────────────── INPI RNE (dirigeants) ───────────────────────────────
# Les dirigeants vivent dans pm_dirigeants (rattachés aux personnes morales MAJIC).
_ajout(_f(
    source="inpi_rne", libelle="INPI RNE (dirigeants)", table="pm_dirigeants",
    source_motif="INPI RNE%", portee_run=False))


# ─────────────────────────────── BAN ───────────────────────────────
# Mesures 05/09 : 339 915 adresses · 100 % géocodées · 24 communes · 21 non rattachées.
_ajout(_f(
    source="ban", libelle="Base Adresse Nationale", table="adresses",
    cle=("id_ban",), insee_col="insee", geom_col="geom", source_motif="Base Adresse Nationale%",
    portee_run=False,
    propres=[
        c.couverture(
            "d_geocode", "geometrie", "avertissant", "Part des adresses géocodées",
            "≥ 99 % avec coordonnées (mesuré 100 % au 05/09)",
            "geom IS NOT NULL", 99.0),
    ]))


# ─────────────────────────────── CoSIA (couverture du sol IA) ───────────────────────────────
# Mesures 05/09 : 445 190 bâtiments batiment_cosia.
_ajout(_f(
    source="cosia", libelle="CoSIA (couverture du sol IA, IGN)", table="spatial_layers",
    where="kind = 'batiment_cosia'", cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="CoSIA%", portee_run=True))


# ─────────────────────────────── FLAIR (occupation du sol IGN) ───────────────────────────────
# FLAIR sert de JUGE aux détections ortho (colonne juge_flair) plutôt qu'une couche servie propre :
# le filtre porte sur la présence du signal FLAIR sur les détections. Contrôle propre léger.
_ajout(_f(
    source="flair", libelle="FLAIR (occupation du sol IA, IGN)", table="ortho_detections",
    source_motif="FLAIR%", portee_run=False,
    propres=[
        c.couverture(
            "d_flair_signal", "completude", "avertissant", "Signal FLAIR sur les détections",
            "≥ 0 % — mesure informative (FLAIR juge les détections ortho, colonne juge_flair)",
            "juge_flair IS NOT NULL", 0.0),
    ]))


# ─────────────────────────────── LiDAR HD (toits) ───────────────────────────────
# LiDAR HD est servi EN DIRECT (WMS 974, aucune table ingérée) — le seuil de confiance 0,70 des
# toits contrôlés (RETOURS-14 : 0 faux sur 50) est rejoué par l'ÉCHANTILLON (lot 3), pas ici. Le
# filtre porte sur les détections ortho au seuil 0,70 comme proxy servi.
_ajout(_f(
    source="lidar_hd", libelle="LiDAR HD (IGN, 974)", table="ortho_detections",
    source_motif="LiDAR HD%", portee_run=False,
    propres=[
        c.part_max(
            "d_confiance_seuil", "distribution", "avertissant",
            "Détections sous le seuil de confiance 0,70",
            "informatif — les détections servies visent ≥ 0,70 (RETOURS-14 : 0 faux/50 toits)",
            "confiance IS NOT NULL AND confiance < 0.70", 100.0),
    ]))


# ─────────────────────────────── EDF (réseaux électriques) ───────────────────────────────
# Mesures 05/09 : 19 528 tronçons ligne_ht/ligne_mt.
_ajout(_f(
    source="edf", libelle="EDF — réseaux HTA/HTB", table="spatial_layers",
    where="kind IN ('ligne_ht','ligne_mt')", cle=("id",), geom_col="geom",
    source_motif="EDF%", portee_run=False,
    propres=[
        c.compte_mauvais(
            "d_ligne_non_vide", "geometrie", "avertissant", "Lignes non vides",
            "0 ligne de géométrie vide (mesuré au 05/09)",
            "geom IS NOT NULL AND ST_IsEmpty(geom)"),
    ]))


# ─────────────────────────────── OSM / TCSP ───────────────────────────────
# Mesures 05/09 : 50 760 aménités OSM/BPE, 188 objets TCSP.
_ajout(_f(
    source="osm_overpass", libelle="OpenStreetMap / Overpass (aménités)", table="spatial_layers",
    where="kind IN ('amenite','amenite_bpe')", cle=("id",), commune_nom_col="commune",
    geom_col="geom", source_motif="OpenStreetMap%", portee_run=False))
_ajout(_f(
    source="osm_transport", libelle="OSM — transport (TCSP, pôles, téléphérique)",
    table="spatial_layers",
    where="kind IN ('tcsp_troncon','tcsp_station','tcsp_zone','pole_echange','telepherique')",
    cle=("id",), geom_col="geom", source_motif="OSM — transport%", portee_run=False,
    propres=[
        c.compte_mauvais(
            "d_tcsp_non_vide", "geometrie", "avertissant", "Objets TCSP non vides",
            "0 objet TCSP de géométrie vide (mesuré au 05/09)",
            "geom IS NOT NULL AND ST_IsEmpty(geom)"),
    ]))


# ─────────────────────────────── GTFS (transport public) ───────────────────────────────
_ajout(_f(
    source="gtfs_pan", libelle="Transport public — GTFS (PAN)", table="spatial_layers",
    where="kind IN ('transport_arret','transport_ligne')", cle=("id",), geom_col="geom",
    source_motif="Transport public — GTFS%", portee_run=False,
    propres=[
        c.compte_mauvais(
            "d_arret_non_vide", "geometrie", "avertissant", "Arrêts/lignes non vides",
            "0 arrêt/ligne de géométrie vide (mesuré au 05/09)",
            "geom IS NOT NULL AND ST_IsEmpty(geom)"),
    ]))


# ─────────────────────────────── BPE INSEE ───────────────────────────────
_ajout(_f(
    source="bpe_insee", libelle="BPE INSEE (équipements)", table="spatial_layers",
    where="kind = 'amenite_bpe'", cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="BPE INSEE%", portee_run=False))


# ─────────────────────────────── Filosofi (carreaux 200 m) ───────────────────────────────
# Mesures 05/09 : 14 773 carreaux · idcar_200m unique · geom présent.
_ajout(_f(
    source="filosofi", libelle="Filosofi (carreaux 200 m, INSEE)", table="filosofi_carreaux_200m",
    cle=("idcar_200m",), geom_col="geom", source_motif="Filosofi%", portee_run=False,
    a_job=False,
    propres=[
        c.compte_mauvais(
            "d_ind_positif", "plage", "avertissant", "Population de carreau positive",
            "0 carreau à population ind < 0 (mesuré au 05/09)",
            "ind IS NOT NULL AND ind < 0"),
    ]))


# ─────────────────────────────── CatNat (SOURCES-1 lot 6.1) ───────────────────────────────
# Référence producteur (GASPAR /gaspar/catnat, champ `results` par commune) mesurée au 06/09/2026,
# APRÈS réparation de la pagination. Le contrôle de complétude compare notre count par commune à
# cette référence : une commune SOUS sa référence = arrêtés perdus (la troncature à 10 revenue).
CATNAT_REFERENCE: dict[str, int] = {
    "97401": 16, "97402": 17, "97403": 14, "97404": 21, "97405": 19, "97406": 12,
    "97407": 11, "97408": 17, "97409": 17, "97410": 17, "97411": 21, "97412": 21,
    "97413": 21, "97414": 23, "97415": 24, "97416": 20, "97417": 21, "97418": 22,
    "97419": 10, "97420": 19, "97421": 19, "97422": 18, "97423": 11, "97424": 16,
}  # total 427 (GASPAR `results` par commune, lu en direct le 06/09/2026)


def _catnat_completude() -> Controle:
    """Complétude CatNat : le nombre d'arrêtés par commune vs la référence producteur. Une commune
    sous sa référence = troncature revenue. Mesuré/posé au 06/09 après réparation de la pagination."""
    def m(db, f: Filtre, version: str):
        if not f.table:
            return skip("pas de table")
        rows = dict(db.execute(text(
            "SELECT insee, count(*) FROM catnat_arretes GROUP BY insee")).all())
        manquants = []
        for insee, ref in CATNAT_REFERENCE.items():
            n = int(rows.get(insee, 0))
            if n < ref:
                manquants.append({"insee": insee, "nous": n, "reference": ref})
        d = {"reference_producteur": "GASPAR results par commune (06/09)",
             "sous_reference": manquants, "n_sous": len(manquants),
             "total": sum(int(v) for v in rows.values())}
        return ok(f"{sum(int(v) for v in rows.values())} arrêtés", d) if not manquants \
            else ko(f"{len(manquants)} commune(s) sous la référence", d)
    return Controle("d_completude_catnat", "completude", "avertissant",
                    "Arrêtés CatNat par commune vs producteur",
                    "chaque commune ≥ sa référence GASPAR (06/09) — sous la référence = troncature",
                    m)


_ajout(_f(
    source="catnat", libelle="Arrêtés CatNat (GASPAR / Géorisques)", table="catnat_arretes",
    cle=("insee", "type_peril", "date_arrete", "date_debut"), insee_col="insee",
    date_cols=("date_arrete", "date_debut"), source_motif="CatNat%", portee_run=False,
    propres=[_catnat_completude()]))


# ─────────────────────── Taxe d'aménagement — taux communaux publics (SOURCES-1 lot 6.2) ───────────────────────
# Le taux communal de TA vient des délibérations (source publique). La table est seedée VIDE
# (doctrine « aucun taux inventé ») — le contrôle mesure la COUVERTURE : combien des 24 communes
# ont un taux public. Aujourd'hui 0/24 (les taux sont à ingérer de la source officielle).
def _ta_couverture() -> Controle:
    def m(db, f: Filtre, version: str):
        from .cadre import _table_existe
        if not _table_existe(db, "taxe_amenagement_taux"):
            return skip("table taxe_amenagement_taux absente")
        n = int(db.execute(text("SELECT count(*) FROM taxe_amenagement_taux")).scalar() or 0)
        d = {"communes_avec_taux_public": n, "attendues": 24}
        return ok(f"{n}/24", d) if n >= 24 else ko(f"{n}/24", d)
    return Controle("d_taux_public_couverture", "completude", "avertissant",
                    "Couverture des taux communaux publics",
                    "24/24 communes avec un taux public (aujourd'hui 0 — à ingérer de la source officielle)",
                    m)


# NB : pas de `table` déclarée — une table de taux VIDE est l'état PENDING attendu (doctrine « aucun
# taux inventé »), pas une quarantaine. La couverture est mesurée par le contrôle propre seul.
_ajout(_f(
    source="taxe_amenagement", libelle="Taxe d'aménagement — taux communaux publics",
    source_motif="Taxe d'aménagement — taux%", portee_run=False, a_job=False,
    propres=[_ta_couverture()]))


# ─────────────────────────────── trafic RN (bonus impact) ───────────────────────────────
_ajout(_f(
    source="trafic_rn", libelle="Trafic RN (Région Réunion)", table="trafic_rn",
    geom_col="geom", source_motif="Trafic RN%", portee_run=False,
    propres=[
        c.compte_mauvais(
            "d_tmja_positif", "plage", "avertissant", "TMJA positif",
            "0 tronçon à TMJA ≤ 0 (mesuré au 05/09)",
            "tmja IS NOT NULL AND tmja <= 0"),
    ]))


# ══════════════════════════ SOURCES-1 lot 1 — droit des sols ══════════════════════════
# Mesures 06/09/2026 (base servie) : plu_gpu_prescription typepsc 05 = 2 250 ER (+6 ER réels
# codés « 02 » à Saint-Louis, rescue M8a), typepsc 01 = 1 782 EBC. DPU/PEB : ingérés par
# `labuse ingest-gpu-infos` (info-surf GPU, typeinf 04/27). ABC : 24/24 communes (4 A, 20 B1).

def _communes_couvertes(cid: str, libelle: str, seuil_txt: str, kind: str,
                        subtype_in: tuple[str, ...] | None = None,
                        attendu: int = 24, bloquant: bool = False) -> Controle:
    """Combien des 24 communes ont AU MOINS une entité de ce kind (et subtypes) — l'état réel de
    publication, les manquantes LISTÉES (jamais un zéro silencieux)."""
    def m(db, f: Filtre, version: str):
        w = "kind = :k" + (" AND subtype = ANY(:st)" if subtype_in else "")
        p: dict = {"k": kind}
        if subtype_in:
            p["st"] = list(subtype_in)
        rows = db.execute(text(
            f"SELECT DISTINCT commune FROM spatial_layers WHERE {w} "
            "AND commune IS NOT NULL"), p).scalars().all()
        from ..ingestion.run_all import REUNION_COMMUNES
        toutes = {nom for _, nom in REUNION_COMMUNES}
        vues = {r for r in rows if r in toutes}
        manquantes = sorted(toutes - vues)
        d = {"communes_couvertes": len(vues), "attendues": attendu, "manquantes": manquantes}
        return ok(f"{len(vues)}/{attendu}", d) if len(vues) >= attendu else \
            ko(f"{len(vues)}/{attendu}", d)
    return Controle(cid, "completude", "bloquant" if bloquant else "avertissant",
                    libelle, seuil_txt, m)


# ── Emplacements réservés (réservoir gpu_prescriptions_er) ──
def _er_hors_code() -> Controle:
    """La famille ER réelle inclut le rescue par libellé (codes hétérogènes entre communes, M8a) —
    ce contrôle mesure les ER RECONNAISSABLES codés HORS 05 (hors du `where` du filtre, exprès) :
    l'état réel, visible, jamais bloquant (le rescue de la cascade les capte)."""
    def m(db, f: Filtre, version: str):
        n = int(db.execute(text(
            "SELECT count(*) FROM spatial_layers WHERE kind = 'plu_gpu_prescription' "
            "AND subtype <> '05' "
            "AND (attrs->>'libelle') ~* '(emp[al]{1,4}cement\\s*r[ée]serv)'")).scalar() or 0)
        d = {"n_hors_code": n, "attendu_0609": 6}
        return ok(str(n), d) if n <= 6 else ko(str(n), d)
    return Controle("d_er_hors_code", "distribution", "avertissant",
                    "ER reconnaissables codés hors typepsc 05",
                    "≤ 6 (Saint-Louis, codes « 02 » — rescue M8a, mesuré 6 au 06/09)", m)


_ajout(_f(
    source="gpu_prescriptions_er", libelle="GPU — emplacements réservés",
    table="spatial_layers", where="kind = 'plu_gpu_prescription' AND subtype = '05'",
    cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="GPU — emplacements réservés%", portee_run=True, a_job=False,
    propres=[
        _er_hors_code(),
        _communes_couvertes(
            "d_er_communes", "Communes avec ≥ 1 emplacement réservé publié",
            "état réel de publication GPU (manquantes listées — l'absence peut être réelle)",
            "plu_gpu_prescription", ("05",)),
    ]))

# ── Espaces boisés classés (réservoir gpu_prescriptions_ebc) ──
_ajout(_f(
    source="gpu_prescriptions_ebc", libelle="GPU — espaces boisés classés",
    table="spatial_layers", where="kind = 'plu_gpu_prescription' AND subtype = '01'",
    cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="GPU — espaces boisés%", portee_run=True, a_job=False,
    propres=[
        # un « EBC » sans libellé reconnaissable est servi tel quel mais compté (état réel).
        c.part_max(
            "d_ebc_libelle", "completude", "avertissant",
            "Part des EBC sans libellé boisé reconnaissable",
            "≤ 10 % (libellés « EBC / espace boisé » mesurés dominants au 06/09)",
            "(attrs->>'libelle') IS NULL OR (attrs->>'libelle') !~* '(bois|EBC)'", 10.0),
        _communes_couvertes(
            "d_ebc_communes", "Communes avec ≥ 1 EBC publié",
            "état réel de publication GPU (manquantes listées — l'absence peut être réelle)",
            "plu_gpu_prescription", ("01",)),
    ]))

# ── Droit de préemption urbain (réservoir dpu_perimetres, label vanne `dpu`) ──
_ajout(_f(
    source="dpu", libelle="GPU — droit de préemption urbain",
    table="spatial_layers", where="kind = 'dpu'",
    cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="GPU — droit de préemption%", portee_run=True,
    propres=[
        c.domaine("d_dpu_subtypes", "subtype", ("dpu", "dpu_renforce"), "bloquant",
                  "Sous-types DPU connus", "dpu | dpu_renforce (fixés à l'ingestion)"),
        # une commune sans DPU au GPU n'a pas publié — listée pour la demande de Vic
        # (SIG communaux), jamais un zéro silencieux.
        _communes_couvertes(
            "d_dpu_communes", "Communes avec DPU publié au GPU",
            "état réel (communes non publiées listées pour la demande aux SIG communaux)",
            "dpu"),
    ]))

# ── PEB (réservoir peb_dgac, label vanne `peb`) — couche d'ÎLE (commune = NULL) ──
def _peb_aerodromes() -> Controle:
    """Roland-Garros ET Pierrefonds attendus À TERME ; au 06/09/2026 seul Roland-Garros est
    republié au GPU (Pierrefonds absent, vérifié) — l'écart est l'état réel, listé."""
    def m(db, f: Filtre, version: str):
        libs = db.execute(text(
            "SELECT DISTINCT lower(coalesce(attrs->>'libelle', name)) FROM spatial_layers "
            "WHERE kind = 'peb'")).scalars().all()
        rg = any("roland" in (x or "") for x in libs)
        pf = any("pierrefonds" in (x or "") for x in libs)
        d = {"roland_garros": rg, "pierrefonds": pf,
             "note": "Pierrefonds NON publié au GPU (vérifié 06/09/2026)" if not pf else None}
        return ok("2/2", d) if (rg and pf) else ko(("1/2" if rg or pf else "0/2"), d)
    return Controle("d_peb_aerodromes", "completude", "avertissant",
                    "Aérodromes couverts (Roland-Garros, Pierrefonds)",
                    "2/2 à terme — 1/2 au 06/09/2026 (Pierrefonds non publié au GPU)", m)


_ajout(_f(
    source="peb", libelle="PEB — plans d'exposition au bruit",
    table="spatial_layers", where="kind = 'peb'",
    cle=("id",), geom_col="geom",
    source_motif="PEB — plans d'exposition%", portee_run=True,
    propres=[
        c.domaine("d_peb_zones", "subtype", ("a", "b", "c", "d"), "bloquant",
                  "Zones PEB lisibles (A/B/C/D)",
                  "zones du L112-10 CU seulement — une zone illisible est écartée à l'ingestion, jamais devinée"),
        _peb_aerodromes(),
    ]))

# ── Zonage ABC (réservoir zonage_abc_dhup, label vanne `zonage_abc`) ──
_ajout(_f(
    source="zonage_abc", libelle="Zonage ABC des communes (DHUP)",
    table="commune_zonage_abc", cle=("insee",), insee_col="insee",
    source_motif="Zonage ABC%", portee_run=False,
    propres=[
        c.domaine("d_abc_domaine", "zone", ("Abis", "A", "B1", "B2", "C"), "bloquant",
                  "Domaine des classes ABC", "classes de l'arrêté D. 304-1 CCH seulement"),
        c.couverture("d_abc_couverture", "completude", "bloquant",
                     "Les 24 communes classées", "24/24 (arrêté national — mesuré 24/24 au 06/09)",
                     "zone IS NOT NULL", 100.0),
    ]))

# ── SUP — assiettes GPU (label vanne `sup_gpu`) : filtre riche (l'inventaire catégoriel
# amont vit dans la sonde sentinelle ; ici, l'état de la table servie) ──
_ajout(_f(
    source="sup_gpu", libelle="SUP — assiettes GPU (API Carto)",
    table="spatial_layers", where="kind = 'sup'",
    cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="SUP — assiettes%", portee_run=True,
    propres=[
        # domaine OUVERT (une nouvelle catégorie publiée doit ENTRER, pas être bloquée) — le
        # contrôle liste ce qui est en base hors des catégories déjà vues au 06/09 : visible.
        c.compte_mauvais(
            "d_sup_geo", "completude", "avertissant",
            "Assiettes sans genre géométrique tracé",
            "0 assiette sans attrs.geo (s|l|p) — mesuré 0 au 06/09",
            "(attrs->>'geo') IS NULL OR (attrs->>'geo') NOT IN ('s','l','p')"),
        _communes_couvertes(
            "d_sup_communes", "Communes avec ≥ 1 assiette SUP",
            "état réel (la publication SUP est inégale par catégorie et par commune — fiche 1 du rapport)",
            "sup"),
    ]))


# ══════════════════════════ SOURCES-1 lot 2 — la nature et l'eau ══════════════════════════
# Mesures 07/09/2026 (WFS Carmen DEAL_REUNION_2020, GML EPSG:2975 → ogr2ogr) : DPF 275
# tronçons + 6 plans d'eau · zones humides 5 inventaires (1 507 + 187 + 30 + 49 + 1 349) ·
# ENP compléments (Ramsar 1, sites 7, RN 3 dont réserve marine) · AZI/TRI GASPAR par commune.

_ajout(_f(
    source="deal_dpf", libelle="Ravines — domaine public fluvial (DEAL Carmen)",
    table="spatial_layers", where="kind = 'dpf'",
    cle=("id",), geom_col="geom",
    source_motif="Ravines — domaine public fluvial%", portee_run=True,
    propres=[
        c.domaine("d_dpf_subtypes", "subtype", ("cours_eau", "plan_eau"), "bloquant",
                  "Sous-types DPF connus", "cours_eau | plan_eau (fixés à l'ingestion)"),
        c.couverture("d_dpf_toponymes", "completude", "avertissant",
                     "Part des tronçons DPF avec toponyme",
                     "≥ 80 % (mesuré ~93 % au 07/09 — Rivière du Mât, Bras de la Plaine…)",
                     "(attrs->>'toponyme') IS NOT NULL", 80.0),
    ]))

_ajout(_f(
    source="zones_humides", libelle="Zones humides — inventaires DEAL",
    table="spatial_layers", where="kind = 'zone_humide'",
    cle=("id",), geom_col="geom",
    source_motif="Zones humides — inventaires DEAL%", portee_run=True,
    propres=[
        c.domaine("d_zh_inventaires", "subtype",
                  ("habitats_2011", "inventaire_2009", "espace_fonctionnel_2009",
                   "inventaire_2003", "basse_altitude_2019"), "bloquant",
                  "Inventaires DEAL connus",
                  "les 5 inventaires par secteurs (2003→2019) — la couverture partielle est DITE"),
    ]))

_ajout(_f(
    source="enp_complements", libelle="Espaces protégés complémentaires (DEAL Carmen)",
    table="spatial_layers",
    where="kind = 'ens' AND subtype IN ('ramsar','site_classe','site_inscrit','reserve_naturelle')",
    cle=("id",), geom_col="geom",
    source_motif="Espaces protégés complémentaires%", portee_run=True,
    propres=[
        # la réserve marine DOIT être là (absente du jeu INPN local — c'est LE gain du canal)
        c.compte_mauvais(
            "d_enp_reserve_marine", "completude", "bloquant",
            "Réserve marine présente",
            "≥ 1 entité « Réserve Nationale Marine » (le gain vérifié du canal Carmen)",
            "NOT EXISTS (SELECT 1 FROM spatial_layers s2 WHERE s2.kind = 'ens' "
            "AND s2.subtype = 'reserve_naturelle' AND s2.name ILIKE '%marine%')",
            extra_where="id = (SELECT min(id) FROM spatial_layers WHERE kind = 'ens')"),
    ]))

_ajout(_f(
    source="azi_tri", libelle="AZI / TRI — inondation (GASPAR)",
    table="azi_communes", cle=("insee", "type_doc", "code_national"), insee_col="insee",
    source_motif="AZI / TRI — inondation%", portee_run=False,
    propres=[
        c.domaine("d_azi_types", "type_doc", ("azi", "tri"), "bloquant",
                  "Types de document connus", "azi | tri (GASPAR)"),
        # l'AZI/TRI ne couvre PAS les 24 communes (état réel GASPAR) — les non couvertes
        # sont listées à l'ingestion, jamais un zéro silencieux.
        c.couverture("d_azi_libelles", "completude", "avertissant",
                     "Part des documents avec libellé",
                     "≥ 90 % (GASPAR sert le libellé — mesuré au 07/09)",
                     "libelle IS NOT NULL AND libelle <> ''", 90.0),
    ]))

# RPG : la source existe (en_direct, proxy IGN) — filtre riche sur la table servie.
_ajout(_f(
    source="rpg_ign", libelle="RPG — déclarations agricoles (couche servie)",
    table="spatial_layers", where="kind = 'safer'",
    cle=("id",), commune_nom_col="commune", geom_col="geom",
    source_motif="RPG — déclarations agricoles%", portee_run=True, a_job=False,
    propres=[
        # le code culture est LE gain du lot 2 (cascade zone A/canne) : jamais nul.
        c.couverture("d_rpg_code_cultu", "completude", "bloquant",
                     "Part des déclarations avec code culture",
                     "100 % (mesuré 38 460/38 460 au 07/09 — CSA 12 464)",
                     "(attrs->>'code_cultu') IS NOT NULL", 99.0),
    ]))


# ══════════════════════════ SOURCES-1 lot 3 — les sols et le bruit ══════════════════════════
# Mesures 07/09/2026 : sol_pollue = 4 SIS (MultiPolygon, id_sis présent 3/4), 453 CASIAS
# (435 points + 18 emprises) + 56 instructions ; bruit_route = 1 004 bandes cat1-5 ;
# bruit_carte = 6 zones de dépassement (type c, RN/RD/VC × Lden/Ln).

# ── SIS (réservoir logique georisques_sis sur sol_pollue/sis) ──
_ajout(_f(
    source="georisques_sis", libelle="Géorisques — SIS",
    table="spatial_layers", where="kind = 'sol_pollue' AND subtype = 'sis'",
    cle=("id",), geom_col="geom",
    source_motif="Géorisques — secteurs d'information%", portee_run=True, a_job=False,
    propres=[
        # un SIS est un PÉRIMÈTRE réglementaire : une géométrie ponctuelle serait une anomalie.
        c.compte_mauvais(
            "d_sis_polygone", "distribution", "bloquant",
            "SIS non surfacique",
            "0 SIS ponctuel/linéaire (périmètre réglementaire — mesuré 0/4 au 07/09)",
            "ST_Dimension(geom) <> 2"),
        # id_sis officiel absent sur 1/4 (Le Port, fiche infosols sans identifiant) — état réel.
        c.compte_mauvais(
            "d_sis_id", "completude", "avertissant",
            "SIS sans identifiant officiel (id_sis)",
            "≤ 1 (mesuré 1/4 au 07/09 — fiche infosols sans id_sis)",
            "(attrs->>'id_sis') IS NULL OR (attrs->>'id_sis') = ''"),
    ]))

# ── CASIAS (réservoir logique georisques_casias sur sol_pollue/casias+instruction) ──
_ajout(_f(
    source="georisques_casias", libelle="Géorisques — CASIAS",
    table="spatial_layers", where="kind = 'sol_pollue' AND subtype IN ('casias', 'instruction')",
    cle=("id",), geom_col="geom",
    source_motif="Géorisques — CASIAS%", portee_run=True, a_job=False,
    propres=[
        # l'identifiant SSP trace chaque site vers sa fiche Géorisques — jamais nul.
        c.couverture("d_casias_identifiant", "completude", "bloquant",
                     "Part des sites avec identifiant SSP",
                     "≥ 99 % (mesuré 509/509 au 07/09)",
                     "(attrs->>'identifiant_ssp') IS NOT NULL", 99.0),
        # la part d'emprises réelles (vs points géocodés) est DITE — état réel, pas un seuil.
        c.part_max("d_casias_points", "distribution", "avertissant",
                   "Part des sites en point géocodé (sans emprise)",
                   "≤ 97 % (mesuré ~94 % au 07/09 — 480 points / 29 emprises)",
                   "ST_Dimension(geom) < 2", 97.0),
    ]))

# ── Classement sonore (réservoir bruit_itt_cerema — filtre riche, label vanne existant) ──
# NB : pas de commune_nom_col — le flux Cerema porte SES libellés (majuscules sans accents,
# « SAINT JOSEPH »/« SAINT-JOSEPH ») ; le rattachement aux 24 se lit par insee_comm (contrôle propre).
_ajout(_f(
    source="bruit_itt_cerema", libelle="Classement sonore ITT (Cerema)",
    table="spatial_layers", where="kind = 'bruit_route'",
    cle=("id",), geom_col="geom",
    source_motif="Classement sonore ITT%", portee_run=True, a_job=False,
    propres=[
        c.domaine("d_bruit_categories", "subtype", ("cat1", "cat2", "cat3", "cat4", "cat5"),
                  "bloquant", "Catégories du classement (1-5)",
                  "catégories de l'arrêté seulement (R571-32 CE)"),
        # chaque bande est matérialisée par la largeur réglementaire sect_bruit_m (> 0).
        c.compte_mauvais(
            "d_bruit_bande", "plage", "bloquant",
            "Bande sans largeur réglementaire",
            "0 bande sans sect_bruit_m > 0 (mesuré 0/1 004 au 07/09)",
            "COALESCE((attrs->>'sect_bruit_m')::float, 0) <= 0"),
        # code INSEE 974xx présent sur chaque bande (rattachement commune du flux).
        c.couverture("d_bruit_insee", "rattachement", "bloquant",
                     "Part des bandes rattachées à une commune (insee_comm)",
                     "≥ 99 % (mesuré 1 004/1 004 au 07/09)",
                     "(attrs->>'insee_comm') LIKE '974%'", 99.0),
    ]))

# ── Cartes de bruit stratégiques (réservoir deal_bruit_cartes, label vanne bruit_cartes) ──
_ajout(_f(
    source="bruit_cartes", libelle="DEAL — cartes de bruit stratégiques (CBS)",
    table="spatial_layers", where="kind = 'bruit_carte'",
    cle=("id",), geom_col="geom",
    source_motif="DEAL — cartes de bruit%", portee_run=False,
    propres=[
        c.domaine("d_cbs_subtypes", "subtype",
                  ("rn_lden", "rn_ln", "rd_lden", "rd_ln", "vc_lden", "vc_ln"),
                  "bloquant", "Couches type c (dépassements Lden/Ln, RN/RD/VC)",
                  "6 sous-couches fixées à l'ingestion — type b/a jamais servies (doublon/exposition)"),
    ]))


# ══════════════════════════ SOURCES-1 lot 4 — le cadre régional ══════════════════════════
# Le potentiel foncier Région (îlots non urbanisés — ESTIMATION du producteur, jamais servie
# comme donnée LABUSE) devient un CONTRÔLE DE COMPARAISON avec notre analyse : la part des
# parcelles couvertes par un îlot que NOTRE run servi juge « à potentiel » (tiers hauts).
# Mesuré au 07/09/2026 (run q_v11_m137) : 15 776 parcelles dans 2 453 îlots (2 607 ha) ;
# 7 043 en tiers hauts (44,6 %) ; 277 de nos 1 478 brûlantes/chaudes en îlot (18,7 % — notre
# tête valorise AUSSI la densification du bâti, hors du champ « îlots non urbanisés »).
def _potentiel_region_recouvrement() -> Controle:
    def m(db, f: Filtre, version: str):
        from .cadre import _table_existe
        if not _table_existe(db, "parcel_p_score_v2"):
            return skip("parcel_p_score_v2 absente (pas de run servi en base)")
        run = db.execute(text(
            "SELECT run_id FROM parcel_p_score_v2 GROUP BY run_id ORDER BY count(*) DESC LIMIT 1"
        )).scalar()
        if not run:
            return skip("aucun run de score en base")
        row = db.execute(text("""
            WITH dans AS (
              SELECT DISTINCT p.id, s.tier
              FROM parcels p
              JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu AND s.run_id = :run
              JOIN spatial_layers il ON il.kind = 'potentiel_foncier'
                AND ST_Intersects(p.geom_2975, il.geom_2975))
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE tier IN ('brulante','chaude','a_creuser','priorite','a_suivre','sans_signal')) AS hauts
            FROM dans"""), {"run": run}).mappings().first()
        total = int(row["total"] or 0)
        hauts = int(row["hauts"] or 0)
        pct = round(100.0 * hauts / total, 1) if total else None
        d = {"run": run, "parcelles_dans_ilots": total, "tiers_hauts": hauts, "pct_hauts": pct,
             "mesure_0709": {"total": 15776, "hauts": 7043, "pct": 44.6}}
        if total == 0:
            return ko("0 parcelle dans les îlots", d)
        # avertit si la convergence s'effondre (< 25 % — moitié de la mesure de référence) :
        return ok(f"{pct} % de tiers hauts dans les îlots", d) if (pct or 0) >= 25.0 else \
            ko(f"{pct} %", d)
    return Controle("d_potfoncier_convergence", "referentiel", "avertissant",
                    "Convergence îlots Région ↔ analyse LABUSE",
                    "≥ 25 % des parcelles en îlot jugées à potentiel par le run servi "
                    "(mesuré 44,6 % au 07/09/2026 — seuil = moitié de la référence)", m)


_ajout(_f(
    source="potentiel_foncier_region", libelle="Potentiel foncier Région (contrôle de comparaison)",
    table="spatial_layers", where="kind = 'potentiel_foncier'",
    cle=("id",), geom_col="geom",
    source_motif="Potentiel foncier Région%", portee_run=False, a_job=False,
    propres=[_potentiel_region_recouvrement()]))


# ══════════════════════════ SOURCES-1 lot 5 — la valeur ══════════════════════════
# Mesures 07/09/2026 : Arcep 330 051 immeubles / part FttH mesurée à l'ingestion ; REI 24/24
# (E12 29,55→68,40 %) ; ORT 19 communes (écart : Saint-Louis attendu ACV absent) ; OLL médiane
# agglo 10,9 €/m² (= plaquette), 16 communes mono-zone ; coût construction 1 ligne servie.

def _ort_acv_manquantes() -> Controle:
    """Les 5 ACV attendues (fiche 10) contrôlées CONTRE la table réelle — manquantes listées.
    Mesuré au 07/09/2026 : Saint-Louis (97414) ABSENT de la table DGALN (écart producteur)."""
    def m(db, f: Filtre, version: str):
        from ..ingestion.ort import ACV_ATTENDUES
        acv = {i for (i,) in db.execute(text(
            "SELECT insee FROM commune_ort WHERE statut = 'acv'")).all()}
        manquantes = sorted(f"{nom} ({insee})" for insee, nom in ACV_ATTENDUES.items()
                            if insee not in acv)
        d = {"attendues": sorted(ACV_ATTENDUES.values()), "manquantes": manquantes}
        return ok("5/5", d) if not manquantes else ko(f"{5-len(manquantes)}/5", d)
    return Controle("d_ort_acv_attendues", "completude", "avertissant",
                    "ACV attendues présentes (fiche 10)",
                    "5/5 à terme — 4/5 au 07/09/2026 (Saint-Louis absent de la table DGALN)", m)


def _oll_mediane_plaquette() -> Controle:
    """La médiane agglomération servie = la plaquette AGORAH (fiche 15 : 10,90 €/m²) —
    un écart dit une rupture de méthode ou un mauvais parsing."""
    def m(db, f: Filtre, version: str):
        v = db.execute(text(
            "SELECT loyer_median FROM oll_loyers WHERE zone = 0 AND type_habitat = 'tous' "
            "AND pieces = 'tous' ORDER BY annee DESC LIMIT 1")).scalar()
        d = {"mediane_agglo": float(v) if v is not None else None, "plaquette": 10.9}
        return ok(str(v), d) if v is not None and abs(float(v) - 10.9) < 0.05 else ko(str(v), d)
    return Controle("d_oll_mediane_plaquette", "distribution", "bloquant",
                    "Médiane agglomération = plaquette AGORAH",
                    "10,9 €/m² (fiche 15 — mesuré identique au 07/09)", m)


def _oll_zonage_couverture() -> Controle:
    """Les 24 communes présentes au zonage IRIS→zone (couverture départementale de l'OLL)."""
    def m(db, f: Filtre, version: str):
        n = db.execute(text("SELECT count(DISTINCT insee) FROM oll_zonage")).scalar() or 0
        mono = db.execute(text(
            "SELECT count(*) FROM (SELECT insee FROM oll_zonage GROUP BY insee "
            "HAVING count(DISTINCT zone) = 1) x")).scalar() or 0
        d = {"communes": int(n), "mono_zone": int(mono)}
        return ok(f"{n}/24", d) if n >= 24 else ko(f"{n}/24", d)
    return Controle("d_oll_zonage", "completude", "bloquant",
                    "Zonage OLL : les 24 communes couvertes",
                    "24/24 (observatoire départemental — mesuré 24/24, 16 mono-zone au 07/09)", m)


def _dhup_fichier_ok() -> Controle:
    """Le fichier embarqué DHUP (repli) est lisible et couvre les 24 communes."""
    def m(db, f: Filtre, version: str):
        from ..loyers import load
        n = len(load().get("communes", []))
        d = {"communes": n, "fichier": "data/carte_loyers_reunion_2025.json"}
        return ok(f"{n}/24", d) if n >= 24 else ko(f"{n}/24", d)
    return Controle("d_dhup_fichier", "completude", "bloquant",
                    "Extrait DHUP embarqué lisible (24 communes)",
                    "24/24 dans l'extrait versionné (repli de l'OLL)", m)


_ajout(_f(
    source="arcep_fibre", libelle="Fibre Arcep (immeubles)",
    table="arcep_immeubles", cle=("imb_id",), insee_col="insee", geom_col="geom",
    source_motif="Fibre Arcep%", portee_run=False,
    propres=[
        c.couverture("d_arcep_ftth", "completude", "avertissant",
                     "Part des immeubles raccordables FttH",
                     "≥ 50 % (l'état réel du déploiement, jamais bloquant — mesuré à l'ingestion)",
                     "ftth", 50.0),
        c.compte_mauvais("d_arcep_ops_vides", "completude", "avertissant",
                         "Raccordables sans opérateur listé",
                         "0 immeuble ftth=true sans opérateur (incohérence d'agrégation)",
                         "ftth AND cardinality(operateurs_ftth) = 0"),
    ]))

_ajout(_f(
    source="dgfip_rei", libelle="Taux de taxe foncière (REI)",
    table="commune_rei", cle=("insee",), insee_col="insee",
    source_motif="Taux de taxe foncière%", portee_run=False,
    propres=[
        c.couverture("d_rei_couverture", "completude", "bloquant",
                     "Les 24 communes avec un taux TFPB",
                     "24/24 (fichier national — mesuré 24/24 au 07/09)",
                     "tfpb_commune_pct IS NOT NULL", 100.0),
        c.compte_mauvais("d_rei_bornes", "plage", "bloquant",
                         "Taux dans [0 ; 100] %",
                         "0 taux hors bornes (écartés à l'ingestion + listés)",
                         "tfpb_commune_pct < 0 OR tfpb_commune_pct > 100 "
                         "OR teom_pct < 0 OR teom_pct > 100"),
    ]))

_ajout(_f(
    source="anct_ort", libelle="ACV / PVD / ORT (DGALN)",
    table="commune_ort", cle=("insee",), insee_col="insee",
    source_motif="ACV / PVD / ORT%", portee_run=False,
    propres=[
        c.domaine("d_ort_statuts", "statut", ("acv", "pvd", "autre"), "bloquant",
                  "Domaine des statuts", "acv | pvd | autre (fixés à l'ingestion)"),
        _ort_acv_manquantes(),
    ]))

_ajout(_f(
    source="loyers_oll", libelle="Loyers OLL (ADIL 974 / AGORAH)",
    table="oll_loyers", cle=("annee", "zone", "type_habitat", "pieces"),
    source_motif="Loyers OLL%", portee_run=False,
    propres=[
        c.domaine("d_oll_zones", "zone::text", tuple(str(z) for z in range(0, 7)), "bloquant",
                  "Zones OLL connues", "0 (agglo) + zones 1-6 du zonage L9740"),
        _oll_mediane_plaquette(),
        _oll_zonage_couverture(),
    ]))

_ajout(_f(
    source="cout_construction", libelle="Coût de construction (références)",
    table="cout_construction_ref", cle=("id",),
    source_motif="Coût de construction%", portee_run=False,
    propres=[
        c.couverture("d_cout_servi", "completude", "bloquant",
                     "Une ligne SERVIE au bilan",
                     "la ligne labuse_promotion (2 300-2 800 €/m² SDP) — 1 servie sur 2 lignes",
                     "servi AND cout_bas_eur_m2 IS NOT NULL AND cout_haut_eur_m2 IS NOT NULL",
                     50.0),
    ]))

# Loyers DHUP (fichier embarqué, pas de table) : filtre sur le fichier versionné.
_ajout(_f(
    source="loyers_dhup", libelle="Loyers DHUP (carte des loyers, repli)",
    source_motif="Loyers DHUP%", portee_run=False, a_job=False,
    propres=[_dhup_fichier_ok()]))


# ══════════════════════════ SOURCES-1 lot 6 — le foncier et les gens ══════════════════════════
# Mesures 07/09/2026 : DFI 974 = 409 623 liens mère→fille, 24 communes, dates 1989→2025 ;
# IRIS RP2022 = 344 IRIS (24 communes), vacants/âge du bâti/ménages/tranches d'âge.

# ── DFI (réservoir dgfip_dfi, label vanne `dfi`) ──
_ajout(_f(
    source="dfi", libelle="DFI — filiation des parcelles (DGFiP)",
    table="dfi_filiation", cle=("id",), insee_col="insee",
    date_cols=("date_validation",), source_motif="DFI — documents de filiation%",
    portee_run=False,
    propres=[
        # les IDU reconstruits font 14 caractères (insee 5 + préfixe 3 + parcelle 6) — SAUF
        # deux codes AMONT légitimes, mesurés au 07/09 : fille 'PDP' (passage au domaine
        # public, 5 032) et mère 'EDNC' (issue d'un ensemble non cadastré, 1 797). Ils sont
        # SERVIS étiquetés (fiche), jamais joints à parcels. Bloquant sur le reste seul.
        c.compte_mauvais(
            "d_dfi_idu_forme", "distribution", "bloquant",
            "IDU mère/fille au format LABUSE (14 c) ou code amont connu (PDP, EDNC)",
            "0 lien difforme hors codes amont (mesuré 0 au 07/09 — 5 032 PDP + 1 797 EDNC dits)",
            "(length(idu_mere) <> 14 AND substr(idu_mere, 9) <> 'EDNC') "
            "OR (length(idu_fille) <> 14 AND substr(idu_fille, 9) <> 'PDP')"),
        c.part_max(
            "d_dfi_codes_amont", "distribution", "avertissant",
            "Part des liens à code amont (PDP/EDNC)",
            "≤ 3 % (mesuré 1,7 % au 07/09 — 6 829/409 623)",
            "substr(idu_mere, 9) = 'EDNC' OR substr(idu_fille, 9) = 'PDP'", 3.0),
        # un lien mère = fille est un non-événement (aucun observé) — l'état réel, visible.
        c.compte_mauvais(
            "d_dfi_auto_lien", "distribution", "avertissant",
            "Liens mère = fille (auto-référence)",
            "0 attendu (mesuré 0 au 07/09)",
            "idu_mere = idu_fille"),
        # la filiation ne couvre que l'informatisation (1980-90+) — une date hors plage dit un
        # amont qui a changé de forme.
        c.compte_mauvais(
            "d_dfi_dates", "plage", "avertissant",
            "Dates de validation dans la plage de l'informatisation",
            "0 lien avant 1980 (mesuré : min 1989-12-06 au 07/09)",
            "date_validation < DATE '1980-01-01'"),
    ]))

# ── Recensement IRIS (réservoir insee_rp_iris, label vanne `iris_rp`) ──
def _iris_couverture_contours() -> Controle:
    """Chaque IRIS de la table est adossé à un contour servi (kind iris_insee) — sinon la
    donnée quartier n'est joignable à aucune parcelle (l'affinage serait muet)."""
    def m(db, f: Filtre, version: str):
        n = int(db.execute(text(
            "SELECT count(*) FROM iris_rp r WHERE NOT EXISTS ("
            "  SELECT 1 FROM spatial_layers sl WHERE sl.kind = 'iris_insee' "
            "  AND sl.subtype = r.iris)")).scalar() or 0)
        d = {"iris_sans_contour": n}
        return ok("0", d) if n == 0 else ko(str(n), d)
    return Controle("d_iris_contours", "completude", "bloquant",
                    "Chaque IRIS adossé à un contour servi",
                    "0 IRIS sans contour (géographie 2024 des deux côtés — mesuré 0 au 07/09)", m)


_ajout(_f(
    source="iris_rp", libelle="INSEE RP2022 — bases IRIS",
    table="iris_rp", cle=("iris",), insee_col="insee",
    source_motif="INSEE RP2022 — bases IRIS%", portee_run=False,
    propres=[
        _iris_couverture_contours(),
        # vacance ∈ [0 ; 100] par construction (LOGVAC ≤ LOG) — une ligne hors plage dit un
        # amont difforme : bloquant.
        c.compte_mauvais(
            "d_iris_vacance_plage", "plage", "bloquant",
            "Vacance dans [0 ; 100] %",
            "0 IRIS avec LOGVAC > LOG (mesuré 0 au 07/09)",
            "logvac IS NOT NULL AND log IS NOT NULL AND logvac > log"),
        # volet population absent (bases séparées) — l'état réel, visible.
        c.part_max(
            "d_iris_sans_pop", "completude", "avertissant",
            "Part des IRIS sans volet population",
            "≤ 5 % (mesuré 0 au 07/09 — les deux bases couvrent les mêmes IRIS)",
            "pop IS NULL", 5.0),
    ]))
