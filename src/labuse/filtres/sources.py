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
