"""COHERENCE-1 lot B/E — les vérifications COMMUNE : la fiche commune contre ses doubles.

Trois familles de lecteurs par notion :
  · `ctx:<chemin>`      — GET /communes/{commune}/contexte (souvent le CACHE nocturne) ;
  · `sql:<table>`       — la table source relue directement ;
  · `recalc:<formule>`  — recalcul indépendant (même définition, requête réécrite ici).

Les recalculs GÉOMÉTRIQUES (parts d'aléa = intersection sur toutes les parcelles) coûtent
~40 s par commune : ils ne tournent que sur GEO_TEMOINS (3 communes) en mode échantillon,
sur les 24 en mode --ile. C'est CE contrôle qui attrape le cas fondateur Saint-Paul
(fiche 0,1 % / carte 90 % — cache d'avant SOURCES-FIX-2).
"""
from __future__ import annotations

from .lib import RUN, chemin

GEO_TEMOINS = ("Saint-Paul", "Saint-Denis", "Saint-Benoît")


def _c(path):
    return lambda ctx, com: chemin(ctx.commune_ctx(com), path)


def _sql(q):
    return lambda ctx, com: ctx.sql1(q, commune=com, run=RUN)


def _insee(ctx, com):
    return ctx.sql1("SELECT insee FROM communes_referentiel WHERE nom=%(commune)s", commune=com)


def _sql_insee(q):
    def get(ctx, com):
        insee = _insee(ctx, com)
        if not isinstance(insee, str):
            return insee            # ABSENT / Erreur : la table référentiel ne connaît pas la commune
        return ctx.sql1(q, insee=insee)
    return get


def _pct_couche(kind, subtype=None):
    """Recalcul indépendant de pct_parcelles_couche (part des parcelles intersectant)."""
    def get(ctx, com):
        tot = ctx.sql1("SELECT count(*) FROM parcels WHERE commune=%(c)s", c=com)
        if not tot:
            return None
        n = ctx.sql1(
            "SELECT count(DISTINCT p.idu) FROM parcels p JOIN spatial_layers sl "
            "ON sl.kind=%(k)s AND (%(st)s::text IS NULL OR sl.subtype=%(st)s) "
            "AND ST_Intersects(p.geom_2975, sl.geom_2975) WHERE p.commune=%(c)s",
            k=kind, st=subtype, c=com)
        return round(100.0 * n / tot, 1)
    return get


#: (notion, tolérance, [(étiquette, getter)…], cause déclarée, geo_lourd)
CHECKS: list[tuple] = [
    # ── le cas fondateur ──
    ("alea_mvt_commune_pct", "0,5 point", [
        ("ctx:risques.mouvement_terrain_pct", _c("risques.mouvement_terrain_pct")),
        ("recalc:georisque_alea[mouvement_terrain]", _pct_couche("georisque_alea", "mouvement_terrain")),
    ], "cache_perime(definition changee SOURCES-FIX-2)", True),

    ("ppr_commune_pct", "0,5 point", [
        ("ctx:risques.ppr_pct", _c("risques.ppr_pct")),
        ("recalc:ppr", _pct_couche("ppr")),
    ], "cache_perime", True),

    # ── population ──
    ("habitants_n", "0 (entier)", [
        ("ctx:population.habitants", _c("population.habitants")),
        ("sql:sudocuh_procedures.pop_mun",
         _sql("SELECT pop_mun FROM sudocuh_procedures WHERE commune=%(commune)s")),
    ], "source_differente", False),

    ("logements_n", "0 (entier)", [
        ("ctx:population.logements", _c("population.logements")),
        ("ctx:marche.logements", _c("marche.logements")),
    ], "calcul_different", False),

    ("vacants_n", "0 (entier)", [
        ("ctx:population.vacants", _c("population.vacants")),
        ("ctx:marche.vacants", _c("marche.vacants")),
    ], "calcul_different", False),

    ("menages_n", "0 (entier)", [
        ("ctx:population.menages", _c("population.menages")),
        ("ctx:marche.res_principales", _c("marche.res_principales")),
    ], "calcul_different", False),

    # ── SRU ──
    ("taux_lls_pct", "0,5 point", [
        ("ctx:sru.taux_lls", _c("sru.taux_lls")),
        ("sql:commune_contexte_sru.taux_lls",
         _sql_insee("SELECT taux_lls FROM commune_contexte_sru WHERE insee=%(insee)s")),
    ], "cache_perime", False),

    ("deficit_sru_pts", "0,5 point", [
        ("ctx:sru.deficit", _c("sru.deficit")),
        ("recalc:greatest(objectif-taux,0)",
         _sql_insee("SELECT round(greatest(objectif_pct - taux_lls, 0)::numeric, 2) "
                    "FROM commune_contexte_sru WHERE insee=%(insee)s")),
    ], "calcul_different", False),

    # ── fiscalité ──
    ("tfpb_taux_pct(commune)", "0", [
        ("ctx:fiscalite.tfpb_commune_pct", _c("fiscalite.tfpb_commune_pct")),
    ], "", False),   # complété par le croisement parcelle↔commune (banc.py)

    ("taxe_amenagement_taux_communal_pct(commune)", "0", [
        ("ctx:taxe_amenagement.part_communale_pct", _c("taxe_amenagement.part_communale_pct")),
    ], "", False),   # croisé avec la fiche parcelle dans banc.py

    # ── permis (cohérence interne du payload : 3 sections servent le même compte) ──
    ("permis_12m_n", "0 (entier)", [
        ("ctx:permis_bloc.permis_12m", _c("permis_bloc.permis_12m")),
        ("ctx:foncier.permis_12m.n", _c("foncier.permis_12m.n")),
    ], "calcul_different", False),

    ("permis_5a_n", "0 (entier)", [
        ("ctx:permis_bloc.permis_5a", _c("permis_bloc.permis_5a")),
        ("ctx:comparable.permis_5a", _c("comparable.permis_5a")),
    ], "calcul_different", False),

    ("permis_point_mort_n", "0 (entier)", [
        ("ctx:permis_bloc.point_mort", _c("permis_bloc.point_mort")),
        ("ctx:outils.permis_point_mort", _c("outils.permis_point_mort")),
    ], "calcul_different", False),

    # ── parc social ──
    ("parc_social_rpls_logements", "0 (entier)", [
        ("ctx:parc_social.logements", _c("parc_social.logements")),
        ("sql:rpls_commune.nb_logements",
         _sql_insee("SELECT nb_logements FROM rpls_commune WHERE insee=%(insee)s "
                    "ORDER BY millesime DESC LIMIT 1")),
    ], "cache_perime", False),

    # ── risques : compte CatNat ──
    ("catnat_n", "0 (entier)", [
        ("ctx:risques.catnat_arretes", _c("risques.catnat_arretes")),
        ("sql:catnat_arretes.count",
         _sql_insee("SELECT count(*) FROM catnat_arretes WHERE insee=%(insee)s")),
    ], "cache_perime", False),

    # ── classement servi ──
    ("tiers_hauts_n", "0 (entier)", [
        ("ctx:classement.tiers_hauts", _c("classement.tiers_hauts")),
        ("sql:parcel_p_score_v2[brulante+chaude]",
         _sql("SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id "
              "WHERE p.commune=%(commune)s AND s.run_id=%(run)s "
              "AND s.tier IN ('brulante','chaude')")),
    ], "run_different", False),

    ("stock_opportunites_n", "0 (entier)", [
        ("ctx:classement.tiers_hauts", _c("classement.tiers_hauts")),
        ("ctx:foncier.stock_opportunites.n", _c("foncier.stock_opportunites.n")),
        ("ctx:comparable.stock_opportunites_n", _c("comparable.stock_opportunites_n")),
    ], "calcul_different", False),

    # ── foncier ──
    ("n_parcelles_commune", "0 (entier)", [
        ("ctx:foncier.n_parcelles", _c("foncier.n_parcelles")),
        ("sql:parcels.count", _sql("SELECT count(*) FROM parcels WHERE commune=%(commune)s")),
    ], "cache_perime", False),

    ("prix_neuf_eur_m2", "1 %", [
        ("ctx:comparable.neuf_eur_m2", _c("comparable.neuf_eur_m2")),
        ("ctx:prix_neuf_observe.eur_m2", _c("prix_neuf_observe.eur_m2")),
    ], "calcul_different", False),
]

#: croisements parcelle ↔ commune (une parcelle témoin de la commune doit dire pareil)
CROISEMENTS_PARCELLE = [
    ("tfpb_taux_pct", "0",
     "fiche:fiscalite.tfpb_commune_pct", "fiscalite.tfpb_commune_pct",
     "ctx:fiscalite.tfpb_commune_pct", "fiscalite.tfpb_commune_pct"),
    ("taxe_amenagement_taux_communal_pct", "0",
     "fiche:taxe_amenagement.taux_communal_pct", "taxe_amenagement.taux_communal_pct",
     "ctx:taxe_amenagement.part_communale_pct", "taxe_amenagement.part_communale_pct"),
    ("teom_pct", "0",
     "fiche:fiscalite.teom_pct", "fiscalite.teom_pct",
     "ctx:fiscalite.teom_pct", "fiscalite.teom_pct"),
]
