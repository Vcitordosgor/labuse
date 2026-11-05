"""COHERENCE-1 lot B — les vérifications PARCELLE : pour chaque notion, tous ses lecteurs.

Chaque vérification déclare : la notion (id du registre quand elle y est), la tolérance,
et les LECTEURS = (étiquette, callable(ctx, idu) → valeur | None | ABSENT | Erreur).
Étiquettes : `fiche:<chemin>` (GET /parcels/{idu}), `sql:<table>` (la table qui double le
lecteur), `tuile:<attr>` (MVT z14 servi), `api:<route>` (outil).

Le banc compare tous les couples de lecteurs qui rendent une valeur. None = « pas de
donnée » affiché ; ABSENT = le lecteur ne porte pas la notion ici (pas comparé).
"""
from __future__ import annotations

from .lib import ABSENT, RUN, chemin


def _f(path):
    return lambda ctx, idu: chemin(ctx.fiche(idu), path)


def _sql(q):
    return lambda ctx, idu: ctx.sql1(q, idu=idu, run=RUN)


def _tuile(attr):
    def get(ctx, idu):
        props = ctx.tuile_props(idu)
        if props is ABSENT or not isinstance(props, dict):
            return props
        return props.get(attr, ABSENT)
    return get


def _api(route_fmt, path):
    return lambda ctx, idu: chemin(ctx.http_json(route_fmt.format(idu=idu)), path)


def _fiche_flag(layer):
    """La fiche porte-t-elle la vigilance `layer` ? — MÊME DÉFINITION que la carte (parcel_flags /
    tuile) : une ligne cascade SOFT_FLAG (quel que soit le poids), ou abf/UNKNOWN. ECARTS-ZERO-1 :
    l'ancien lecteur regardait le sous-ensemble `flags[]` de la fiche (poids 0 seulement), plus étroit
    que la carte — une vigilance PONDÉRÉE (ex. cinquante_pas, SOFT_FLAG poids -5) y manquait alors
    qu'elle est présente des deux côtés (dans `lines`, section scoring). On lit donc `lines` (toutes
    les lignes cascade servies, après arbitrage) avec le MÊME crible que tiles.py (SOFT_FLAG | abf/UNKNOWN)."""
    def get(ctx, idu):
        lines = chemin(ctx.fiche(idu), "lines")
        if lines is ABSENT or lines is None or not isinstance(lines, list):
            return lines
        return any(l.get("layer") == layer
                   and (l.get("result") == "SOFT_FLAG"
                        or (layer == "abf" and l.get("result") == "UNKNOWN"))
                   for l in lines)
    return get


def _tuile_flag(layer):
    def get(ctx, idu):
        props = ctx.tuile_props(idu)
        if not isinstance(props, dict):
            return props
        if "flags" not in props:
            return ABSENT       # la tuile z14 ne porte pas l'attribut → rien à comparer
        return layer in [x for x in (props["flags"] or "").split(",") if x]
    return get


def _sql_flag(layer):
    def get(ctx, idu):
        return bool(ctx.sql1(
            "SELECT count(*) FROM parcel_flags f JOIN parcels p ON p.id=f.parcel_id "
            "WHERE p.idu=%(idu)s AND f.run_label=%(run)s AND f.layer_name=%(layer)s",
            idu=idu, run=RUN, layer=layer))
    return get


def _prix_maison_fiche(ctx, idu):
    sect = chemin(ctx.fiche(idu), "dvf_parcelle.secteur")
    if not isinstance(sect, list):
        return sect if sect is None or sect is ABSENT else ABSENT
    return next((s.get("mediane_prix_m2") for s in sect
                 if isinstance(s, dict) and s.get("type_bien") == "maison"), ABSENT)


def _copro_fiche(ctx, idu):
    v = chemin(ctx.fiche(idu), "coproprietes")
    if isinstance(v, list):
        return bool(v)          # [] = pas de copropriété connue (état servi, pas une absence)
    return v                    # None / ABSENT / Erreur


#: (notion, tolérance, [(étiquette, getter)…], cause déclarée si écart)
CHECKS: list[tuple] = [
    # ECARTS-ZERO-1 — DEUX surfaces DISTINCTES, longtemps confondues sous un même mot (NU-A-014) :
    #  · la CONTENANCE cadastrale (acte) = la surface de terrain AFFICHÉE partout (surface_terrain_m2,
    #    CONTENANCE-1 : contenance si présente, sinon dessin), servie par la fiche, la carte (la tuile
    #    `surface_m2` = round(COALESCE(contenance_m2, surface_m2))) et le SQL ;
    #  · le DESSIN géométrique (`surface_m2` « (compat) » de la fiche, ligne discrète « Dessin du plan »).
    # L'ancien check comparait le DESSIN de la fiche à la CONTENANCE de la tuile → 109 faux écarts
    # (ex. 4097 dessin vs 4141 contenance). Chacune est désormais un fait à UNE valeur, vérifié chez
    # TOUS ses lecteurs, à la précision affichée (le m²).
    ("surface_terrain_m2(contenance servie)", "0", [
        ("fiche:surface_terrain_m2", _f("surface_terrain_m2")),
        ("sql:COALESCE(contenance_m2,surface_m2)",
         _sql("SELECT COALESCE(contenance_m2, surface_m2) FROM parcels WHERE idu=%(idu)s")),
        ("tuile:surface_m2", _tuile("surface_m2")),
    ], "source_differente"),

    ("surface_dessin_m2", "0", [
        ("fiche:surface_m2", _f("surface_m2")),
        ("sql:parcels.surface_m2", _sql("SELECT surface_m2 FROM parcels WHERE idu=%(idu)s")),
        ("sql:ST_Area(geom_2975)", _sql("SELECT ST_Area(geom_2975) FROM parcels WHERE idu=%(idu)s")),
    ], "geometrie_ou_projection"),

    ("zone_plu_lib", "0", [
        ("fiche:reglement_plu.zones.0.zone", _f("reglement_plu.zones.0.zone")),
        ("sql:parcel_zone_plu.zone_lib", _sql("SELECT zone_lib FROM parcel_zone_plu WHERE idu=%(idu)s")),
        ("tuile:zone_lib", _tuile("zone_lib")),
    ], "source_differente"),

    ("zone_plu_famille", "0", [
        ("sql:parcel_zone_plu.zone_fam", _sql("SELECT zone_fam FROM parcel_zone_plu WHERE idu=%(idu)s")),
        ("tuile:zone_fam", _tuile("zone_fam")),
    ], "source_differente"),

    ("sdp_residuelle_m2", "0", [
        ("fiche:potentiel_transformation.sdp_residuelle_m2",
         _f("potentiel_transformation.sdp_residuelle_m2")),
        # CHASSE-FIX-2 (D03, arbitrage Vic) — le bloc Potentiel sert la SDP du run pour une cause
        # CERTAINE (0 nommé : terrain_exigu/zone_non_constructible/habitat_interdit/redhibitoire/
        # capacite_nulle) et ∅ pour une cause d'IGNORANCE (zone_non_resolue/hors_plu/
        # regle_plu_non_validee/hauteur_indispo…) — cohérent C26/NC. Le lecteur SQL applique la MÊME
        # partition : raw sdp si cause NULL ou certaine, ∅ sinon (miroir de faisabilite.engine.cause_certaine).
        # ECARTS-ZERO-1 — le jumeau reproduit MAINTENANT les DEUX portes de la fiche
        # (_potentiel_transformation_block) : (1) cause résiduelle d'IGNORANCE → ∅ (cause présente
        # non certaine) ; (2) PRÉCÉDENCE DU SCORING — si score_labuse porte une cause (hors_classement :
        # forêt publique, DPF, domaine inacquérable…) ET que la cause résiduelle est nulle ET sdp>0,
        # la fiche sert ∅ (« une seule notion, une seule valeur : le scoring prime »). L'ancien jumeau
        # n'appliquait que la porte (1) → il servait 77 là où la fiche sert ∅ (parcelle inacquérable).
        # CLASSEMENT-USAGE-1 — 3e porte : ZONE FERMÉE au verdict (constructibilité declasse_zone_fermee/
        # non_constructible OU statut AU différé) → ∅, comme la fiche (_potentiel_transformation_block
        # défère à potentiel_batir) et la tuile (tiles.py). Cas 97422000AX1253 (2AUe) + pareilles.
        ("sql:parcel_residuel.sdp_residuelle_m2 (portes fiche : cause + scoring + zone fermée)",
         _sql("SELECT CASE "
              "WHEN r.cause IS NOT NULL AND NOT (r.cause = 'terrain_exigu' "
              "  OR r.cause LIKE 'zone_non_constructible%%' OR r.cause LIKE 'habitat_interdit%%' "
              "  OR r.cause = 'redhibitoire' OR r.cause = 'capacite_nulle') THEN NULL "
              "WHEN r.cause IS NULL AND sl.cause IS NOT NULL AND r.sdp_residuelle_m2 > 0 THEN NULL "
              "WHEN r.cause IS NULL AND COALESCE(pc.label IN ('declasse_zone_fermee','declasse_non_constructible'), false) "
              "  AND NOT COALESCE(au.classe IN ('declasse_au_fermee','declasse_au_statut_inconnu','générique'), false) THEN NULL "
              "ELSE r.sdp_residuelle_m2 END "
              "FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id "
              "LEFT JOIN score_labuse sl ON sl.parcel_id=p.id AND sl.run_label=%(run)s "
              "LEFT JOIN parcel_constructibilite pc ON pc.parcel_id=p.id "
              "LEFT JOIN parcel_au_statut au ON au.parcel_id=p.id "
              "WHERE p.idu=%(idu)s")),
        ("tuile:sdp_residuelle_m2", _tuile("sdp_residuelle_m2")),
    ], "run_different"),

    ("classe_residuel(sous_densite)", "0", [
        ("fiche:potentiel_transformation.sous_densite", _f("potentiel_transformation.sous_densite")),
        ("sql:parcel_residuel.sous_densite",
         _sql("SELECT CASE WHEN r.cause IS NULL THEN r.sous_densite END "
              "FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id WHERE p.idu=%(idu)s")),
        ("tuile:sous_densite", _tuile("sous_densite")),
    ], "run_different"),

    ("tier_opportunite", "0", [
        ("fiche:score_v2.tier", _f("score_v2.tier")),
        ("sql:parcel_p_score_v2.tier",
         _sql("SELECT s.tier FROM parcel_p_score_v2 s WHERE s.parcelle_id=%(idu)s AND s.run_id=%(run)s")),
        ("tuile:tier_v2", _tuile("tier_v2")),
    ], "run_different"),

    ("rang_score", "0", [
        ("fiche:score_v2.rang", _f("score_v2.rang")),
        ("sql:parcel_p_score_v2.rang",
         _sql("SELECT s.rang FROM parcel_p_score_v2 s WHERE s.parcelle_id=%(idu)s AND s.run_id=%(run)s")),
        ("tuile:rang_v2", _tuile("rang_v2")),
    ], "run_different"),

    ("pente_deg", "0", [
        ("fiche:terrain.pente_moy_deg", _f("terrain.pente_moy_deg")),
        ("sql:parcel_terrain.pente_moy_deg",
         _sql("SELECT pente_moy_deg FROM parcel_terrain WHERE idu=%(idu)s")),
    ], "cache_perime"),

    ("pente_max_deg", "0", [
        ("fiche:terrain.pente_max_deg", _f("terrain.pente_max_deg")),
        ("sql:parcel_terrain.pente_max_deg",
         _sql("SELECT pente_max_deg FROM parcel_terrain WHERE idu=%(idu)s")),
    ], "cache_perime"),

    # COHERENCE-FIX-2 (lot A) — le jumeau SQL reproduit la DÉFINITION SERVIE de l'emprise bâtie :
    # BD TOPO clippé à la parcelle, ST_Union AVANT ST_Area (pas de double-compte des empreintes
    # mitoyennes), CoSIA servi À PART (jamais fondu). C'est exactement bati.emprise_bati_bdtopo_m2,
    # le producteur unique lu par la fiche. On NE compare PLUS à p_model_bati.emprise_bati_m2 =
    # MAX(BD TOPO, CoSIA) : c'est une NOTION DISTINCTE (entrée scoring `emprise_bati_scoring_m2`),
    # jamais l'emprise bâtie client — les comparer confondait deux notions sous un même mot.
    ("emprise_batie_m2", "0", [
        ("fiche:le_bien.emprise_batie_m2", _f("le_bien.emprise_batie_m2")),
        ("sql:BD TOPO clippé ST_Union (emprise servie)",
         _sql("SELECT round(COALESCE(ST_Area(ST_Union(ST_Intersection(b.geom_2975, p.geom_2975))), 0)) "
              "FROM spatial_layers b JOIN parcels p ON p.idu=%(idu)s "
              "WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)")),
    ], "source_differente"),

    # ECARTS-ZERO-1 — le FAIT « hauteur faîtage » est produit UNE fois par hauteur_lidar.py
    # (hauteur_lidar_servie), arrondi au décimètre (round(faitage_m, 1)). Le jumeau SQL reproduit
    # EXACTEMENT cet arrondi unique (plus de tolérance 1 % qui masquait le décimètre) : même valeur
    # servie, même arrondi, au point de calcul.
    # ECARTS-ZERO-1 — le FAIT « hauteur faîtage » (le_bien.hauteur_faitage_m) n'est servi QUE si la
    # parcelle porte un bâti SIGNIFICATIF (nb_batiments > 0 = au moins une empreinte BD TOPO ≥ 10 m²) ;
    # sinon la fiche sert ∅ (FAISA-REGLES-1 A-005 : jamais de hauteur « mesurée » là où nb_batiments=0).
    # Le jumeau reproduit CE filtre (sinon il lisait le faîtage d'un abri < 10 m² → faux écart ∅ vs 5,6).
    # Précision servie : le décimètre ("1"), arrondi unique dans hauteur_lidar_servie.
    ("hauteur_faitage_m", "1", [
        ("fiche:le_bien.hauteur_faitage_m", _f("le_bien.hauteur_faitage_m")),
        ("sql:faitage LiDAR si bâti significatif (≥10 m²)",
         _sql("SELECT round(labuse_hauteur_lidar_m(h.faitage_m)::numeric, 1) "
              "FROM batiment_hauteur_lidar h JOIN parcels p ON p.idu=%(idu)s "
              "WHERE h.idu=%(idu)s AND EXISTS ("
              "  SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' "
              "  AND ST_Intersects(b.geom_2975, p.geom_2975) "
              "  AND ST_Area(ST_Intersection(b.geom_2975, p.geom_2975)) >= 10)")),
    ], "calcul_different"),

    # ECARTS-ZERO-1 — le FAIT « copropriété présente » affiché au client est la copropriété RNIC
    # rattachée à la parcelle (la fiche sert `coproprietes` = SELECT … FROM rnic_coproprietes WHERE
    # parcelle_idu). On compare donc le MÊME producteur : présence d'une immatriculation RNIC pour
    # cette parcelle. L'ancien jumeau lisait `p_model_ext_copro.(copro_rnic OR copro_dvf)` = une
    # NOTION DISTINCTE (signal de SCORING, copro inférée par mutations DVF appartement) qui n'est
    # jamais servie comme « copropriété » au client — les confondre sous un même mot créait un faux
    # écart (absence RNIC honnête, cf. COH-copro_presente). Le signal DVF reste interne au scoring.
    ("copro_presente", "0", [
        ("fiche:coproprietes(non vide)", _copro_fiche),
        ("sql:rnic_coproprietes(parcelle_idu)",
         lambda ctx, idu: bool(ctx.sql1(
             "SELECT count(*) FROM rnic_coproprietes WHERE parcelle_idu=%(idu)s", idu=idu))),
    ], "source_differente"),

    ("taxe_amenagement_taux_communal_pct", "0", [
        ("fiche:taxe_amenagement.taux_communal_pct", _f("taxe_amenagement.taux_communal_pct")),
        ("api:/outils/taxe-amenagement/prefill.taux_communal_pct",
         _api("/outils/taxe-amenagement/prefill?idu={idu}", "taux_communal_pct")),
    ], "source_differente"),

    ("vigilance_ppr", "0", [
        ("fiche:flags[ppr]", _fiche_flag("ppr")),
        ("sql:parcel_flags[ppr]", _sql_flag("ppr")),
        ("tuile:flags[ppr]", _tuile_flag("ppr")),
    ], "run_different"),

    ("vigilance_ravine", "0", [
        ("fiche:flags[ravine]", _fiche_flag("ravine")),
        ("sql:parcel_flags[ravine]", _sql_flag("ravine")),
        ("tuile:flags[ravine]", _tuile_flag("ravine")),
    ], "run_different"),

    ("vigilance_cinquante_pas", "0", [
        ("fiche:flags[cinquante_pas]", _fiche_flag("cinquante_pas")),
        ("sql:parcel_flags[cinquante_pas]", _sql_flag("cinquante_pas")),
        ("tuile:flags[cinquante_pas]", _tuile_flag("cinquante_pas")),
    ], "run_different"),

    # COHERENCE-FIX-2 (lot B) — « secteur » DIT SON PÉRIMÈTRE. L'ancien check comparait deux
    # NOTIONS DISTINCTES sous un même mot : la fiche `dvf_parcelle.secteur[maison]` = médiane de
    # la SECTION CADASTRALE (table dvf_secteur_medianes, fenêtre 2021-2025), et mon-secteur
    # `par_type.maison` = médiane au RAYON ADAPTATIF 500→1500 m (reference_locale). Deux périmètres,
    # deux ids — on ne les compare plus. Ici, la cohérence VÉRIFIABLE : la fiche sert FIDÈLEMENT la
    # table de section cadastrale qu'elle lit. Le rayon adaptatif est une valeur mono-productrice
    # (reference_locale), servie avec son périmètre — nommée, pas recalculée.
    ("prix_maison_secteur_section_cadastrale", "0", [
        ("fiche:dvf_parcelle.secteur[maison].mediane_prix_m2", _prix_maison_fiche),
        ("sql:dvf_secteur_medianes[maison] (section cadastrale)",
         _sql("SELECT mediane_prix_m2 FROM dvf_secteur_medianes "
              "WHERE secteur=substring(%(idu)s FROM 1 FOR 10) AND type_bien='maison' "
              "ORDER BY n_ventes DESC NULLS LAST LIMIT 1")),
    ], "source_differente"),

    ("filiation_mere", "0", [
        ("fiche:filiation.meres.0.idu", _f("filiation.meres.0.idu")),
        ("sql:dfi_filiation.idu_mere",
         _sql("SELECT idu_mere FROM dfi_filiation WHERE idu_fille=%(idu)s "
              "ORDER BY date_validation DESC NULLS LAST, id DESC LIMIT 1")),
    ], "source_differente"),

    ("proprietaire_moral_denomination", "0", [
        ("fiche:proprietaire_moral.denomination", _f("proprietaire_moral.denomination")),
        ("sql:pm_proprietaires_millesimes.denomination",
         _sql("SELECT denomination FROM pm_proprietaires_millesimes WHERE idu=%(idu)s "
              "AND millesime=(SELECT max(millesime) FROM pm_proprietaires_millesimes) LIMIT 1")),
    ], "source_differente"),
]
