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
    """La fiche porte-t-elle la vigilance `layer` ? (liste flags de la fiche)"""
    def get(ctx, idu):
        flags = chemin(ctx.fiche(idu), "flags")
        if flags is ABSENT or flags is None or not isinstance(flags, list):
            return flags
        return any(f.get("layer") == layer and f.get("result") in ("SOFT_FLAG", "HARD_EXCLUDE")
                   for f in flags)
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
    ("surface_parcelle_m2", "1 %", [
        ("fiche:surface_m2", _f("surface_m2")),
        ("sql:parcels.surface_m2", _sql("SELECT surface_m2 FROM parcels WHERE idu=%(idu)s")),
        ("sql:ST_Area(geom_2975)", _sql("SELECT ST_Area(geom_2975) FROM parcels WHERE idu=%(idu)s")),
        ("tuile:surface_m2", _tuile("surface_m2")),
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

    ("sdp_residuelle_m2", "1 %", [
        ("fiche:potentiel_transformation.sdp_residuelle_m2",
         _f("potentiel_transformation.sdp_residuelle_m2")),
        # COHERENCE-FIX-1 — le lecteur SQL applique la règle M125 des lecteurs VIVANTS (cause IS
        # NULL) : une ligne à cause (terrain_exigu…) porte un « 0 écrit » de dataset, pas une
        # valeur servie — fiche et tuile la rendent ∅, le SQL doit lire pareil.
        ("sql:parcel_residuel.sdp_residuelle_m2",
         _sql("SELECT CASE WHEN r.cause IS NULL THEN r.sdp_residuelle_m2 END "
              "FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id WHERE p.idu=%(idu)s")),
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

    ("pente_deg", "0,5 point", [
        ("fiche:terrain.pente_moy_deg", _f("terrain.pente_moy_deg")),
        ("sql:parcel_terrain.pente_moy_deg",
         _sql("SELECT pente_moy_deg FROM parcel_terrain WHERE idu=%(idu)s")),
    ], "cache_perime"),

    ("pente_max_deg", "0,5 point", [
        ("fiche:terrain.pente_max_deg", _f("terrain.pente_max_deg")),
        ("sql:parcel_terrain.pente_max_deg",
         _sql("SELECT pente_max_deg FROM parcel_terrain WHERE idu=%(idu)s")),
    ], "cache_perime"),

    ("emprise_batie_m2", "1 %", [
        ("fiche:le_bien.emprise_batie_m2", _f("le_bien.emprise_batie_m2")),
        ("sql:p_model_bati.emprise_bati_m2",
         _sql("SELECT emprise_bati_m2 FROM p_model_bati WHERE idu=%(idu)s")),
    ], "source_differente"),

    ("hauteur_faitage_m", "1 %", [
        ("fiche:le_bien.hauteur_faitage_m", _f("le_bien.hauteur_faitage_m")),
        ("sql:batiment_hauteur_lidar.max(faitage_m)",
         _sql("SELECT max(faitage_m) FROM batiment_hauteur_lidar WHERE idu=%(idu)s")),
    ], "calcul_different"),

    ("copro_presente", "0", [
        ("fiche:coproprietes(non vide)", _copro_fiche),
        ("sql:p_model_ext_copro",
         lambda ctx, idu: bool(ctx.sql1(
             "SELECT (copro_rnic OR copro_dvf) FROM p_model_ext_copro WHERE idu=%(idu)s",
             idu=idu) or False)),
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

    # prix médian du secteur — la fiche (dvf_parcelle.secteur, fenêtre 2021-2025) et
    # l'outil Mon secteur (rayon 500/1000 m) doivent dire le même chiffre quand ils
    # parlent du même périmètre ; l'écart mesuré instruit le lot H (« secteur » nommé).
    ("prix_median_maison_secteur", "1 %", [
        ("fiche:dvf_parcelle.secteur[maison].mediane_prix_m2", _prix_maison_fiche),
        ("api:/outils/mon-secteur.par_type.maison.eur_m2",
         _api("/outils/mon-secteur?idu={idu}", "par_type.maison.eur_m2")),
    ], "calcul_different(rayon/fenetre)"),

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
