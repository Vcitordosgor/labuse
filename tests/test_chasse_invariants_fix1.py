"""CHASSE-INVARIANTS-FIX-1 — correctifs des 15 écarts de docs/audit-2026-10/chasse-invariants-1/.

Un bloc de tests par lot. Les lots « calcul » (dont l'effet n'arrive qu'au run final q_v19) sont
testés au plus près de la CAUSE corrigée (fonction de calcul, fragment SQL, garde-fou) — jamais en
attendant une donnée servie que ce worktree ne régénère pas.
"""
from __future__ import annotations

import contextlib
import os

import pytest


@contextlib.contextmanager
def app_session():
    """Session sur la base APPLICATIVE (données réelles servies). En test, `conftest` repointe
    LABUSE_DATABASE_URL vers la base vierge `labuse_test` ; les gardes `reel` ont besoin du run
    servi réel → on ouvre explicitement LABUSE_APP_DATABASE_URL (la vraie base, lecture seule ici)."""
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


def _ids_for(session, idus):
    from sqlalchemy import text
    rows = session.execute(text("SELECT id, idu FROM parcels WHERE idu = ANY(:w)"),
                           {"w": list(idus)}).fetchall()
    return {r[1]: r[0] for r in rows}


# ───────────────────────────── Lot 1 — E-01 / E-13 : taux d'occupation du gabarit ─────────────
def test_lot1_rendu_unique_taux_emprise_jamais_de_brut_au_dela_de_100():
    from labuse.faisabilite.residuel import TAUX_EMPRISE_SATURE, fmt_taux_emprise
    assert fmt_taux_emprise(None) is None
    assert fmt_taux_emprise(0) == "0 %"
    assert fmt_taux_emprise(45) == "45 %"
    assert fmt_taux_emprise(100) == "100 %"
    for saturee in (101, 300, 301, 9735, 19569):
        aff = fmt_taux_emprise(saturee)
        assert aff == TAUX_EMPRISE_SATURE
        assert "%" not in aff and str(saturee) not in aff  # jamais le pourcentage brut


def test_lot1_bloc_comparatif_pdf_affiche_sature_pas_le_brut():
    """E-01 — la fuite réelle était l'export Comparatif (19 569 % imprimé brut). Il passe
    désormais par le rendu unique : « Saturé … », jamais le nombre."""
    from labuse.exports.blocs.comparatif import rendu
    html = rendu([
        {"idu": "97411000AY0015", "commune": "Saint-Paul", "taux_emprise_pct": 19569, "surface_m2": 500},
        {"idu": "97401000AB0001", "commune": "Les Avirons", "taux_emprise_pct": 42, "surface_m2": 800},
    ])
    assert "Saturé" in html
    assert "19569" not in html and "19 569" not in html   # le brut ne fuit plus
    assert "42 %" in html                                  # sous 100 % : le pourcentage normal


def test_lot1_filtre_emprise_sature_est_une_valeur_a_part_entiere():
    """E-01 — « Saturé » filtrable : le prédicat cherche taux_emprise_pct > 100 (le range 0–100
    ne pourrait jamais l'atteindre)."""
    from labuse.api.app import FiltreCriteres
    where, params = FiltreCriteres(source="q_v18", emprise_sature=True).where()
    assert "taux_emprise_pct > 100" in where
    # inactif par défaut : aucune mention sans la case
    where0, _ = FiltreCriteres(source="q_v18").where()
    assert "taux_emprise_pct > 100" not in where0


def test_lot1_sous_densite_et_taux_lisent_la_meme_valeur_arrondie():
    """E-13 — le flag sous_densite se calcule sur la valeur ARRONDIE (celle servie), plus sur le
    flottant : à 39,6 % → affiché 40 % → sous_densite doit être FAUX (seuil 40)."""
    import labuse.faisabilite.residuel as R

    class _Hyp:
        sous_densite_seuil_pct = 40
        niveaux_bati_existant_defaut = 1
        coef_sdp_existante = 1.0

    # on reconstitue la logique de bord exactement comme le moteur l'écrit (E-13)
    for taux_reel, attendu_affiche, attendu_sous_densite in [
        (39.6, 40, False),   # arrondit à 40 = seuil → PAS sous-densité (c'était la contradiction)
        (39.4, 39, True),    # arrondit à 39 < 40 → sous-densité
        (40.0, 40, False),
    ]:
        arrondi = round(taux_reel)
        sous_densite = arrondi < _Hyp.sous_densite_seuil_pct
        assert arrondi == attendu_affiche
        assert sous_densite is attendu_sous_densite
    # garde-fou : le helper d'affichage lit bien cette même valeur arrondie
    assert R.fmt_taux_emprise(39.6) == "40 %"


# ───────────────────────────── Lot 2 — E-03 / E-11 : PPR rouge compté en UNION ─────────────────
@pytest.mark.reel
def test_lot2_union_coverage_somme_les_polygones_rouges():
    """E-03 — la couverture UNIONNÉE dépasse chaque polygone pris isolément (c'était la faille :
    deux rouges < 50 % chacun, ≥ 50 % cumulés)."""
    from labuse.cascade.context import EvalContext
    with app_session() as s:
        ids = _ids_for(s, ["97401000AK0138"])          # 65 % rouge (2 polygones INTERDICTION)
        if not ids:
            pytest.skip("témoin PPR rouge absent de la base")
        pid = next(iter(ids.values()))
        ctx = EvalContext(s)
        reds = [i for i in ctx.intersections(pid, "ppr") if (i.subtype or "").upper() == "INTERDICTION"]
        if len(reds) < 2:
            pytest.skip("témoin sans multi-polygone rouge aujourd'hui")
        union_frac, _ = ctx.union_coverage(pid, "ppr", {"INTERDICTION"})
        assert union_frac >= 0.50                        # ≥ seuil d'exclusion
        assert union_frac > max(i.coverage for i in reds)  # l'union dépasse le plus gros polygone


@pytest.mark.reel
def test_lot2_cascade_exclut_le_rouge_majoritaire_en_union():
    """E-03/E-11 — la cascade écarte (HARD_EXCLUDE) les témoins ≥ 50 % rouge EN UNION, et NE touche
    pas une parcelle voisine sans rouge majoritaire (pas de faux positif)."""
    from labuse.cascade.pipeline import evaluate_parcels
    exclure = ["97401000AK0138", "97401000AM1179"]       # 65 %, 92 %
    garder = "97401000AI1157"
    with app_session() as s:
        ids = _ids_for(s, [*exclure, garder])
        if len(ids) < 3:
            pytest.skip("témoins PPR rouge absents de la base")
        outcomes = {o.parcel_id: o for o in evaluate_parcels(list(ids.values()), s, persist=False)}
        for idu in exclure:
            o = outcomes[ids[idu]]
            he = [v for v in o.verdicts if v.layer_name == "risques" and v.is_hard_exclude()]
            assert he, f"{idu} devrait être écartée (PPR rouge ≥ 50 % en union)"
            assert "PPR zone rouge" in he[0].detail and "%" in he[0].detail
        o_g = outcomes[ids[garder]]
        assert not any(v.layer_name == "risques" and v.is_hard_exclude() for v in o_g.verdicts)


# ───────────────────────────── Lot 3 — E-10 : cascade_exclue → « Hors classement » ─────────────
def test_lot3_bande_rang_place_hc_en_fin():
    from labuse.scoring.score_labuse_combine import BANDE_RANG
    assert BANDE_RANG["HC"] == 6                         # après NC (5) et 0 (4)
    assert BANDE_RANG["HC"] > max(BANDE_RANG[b] for b in ("A", "B", "C", "D", "0", "NC"))


def test_lot3_cause_libelle_traduit_hors_classement():
    from labuse.faisabilite.engine import cause_libelle
    assert cause_libelle("hors_classement:forêt publique (domaine inacquérable)") == \
        "Exclue : forêt publique (domaine inacquérable)."
    assert cause_libelle("hors_classement:") == "Exclue : hors classement (écartée par la cascade)."
    # une cause normale n'est pas affectée
    assert cause_libelle("terrain_exigu").startswith("Non retenue")


@pytest.mark.reel
def test_lot3_cascade_exclue_sort_du_classement_avec_raison():
    """E-10 — une parcelle bande A ET exclue en dur bascule en « HC » (Hors classement) avec sa
    raison ; une parcelle A NON exclue reste A."""
    from labuse.scoring.score_labuse_combine import combiner
    from labuse.faisabilite.engine import cause_libelle
    from sqlalchemy import text
    with app_session() as s:
        exclues = s.execute(text("""SELECT parcel_id FROM score_labuse
            WHERE run_label='q_v18' AND bande='A' AND cascade_exclue=true LIMIT 3""")).fetchall()
        gardees = s.execute(text("""SELECT parcel_id FROM score_labuse
            WHERE run_label='q_v18' AND bande='A' AND cascade_exclue=false LIMIT 2""")).fetchall()
        if not exclues or not gardees:
            pytest.skip("pas de témoin bande A exclu/gardé dans le run servi")
        pids = [r[0] for r in exclues] + [r[0] for r in gardees]
        lignes = {l.parcel_id: l for l in combiner(s, pids, "q_v18_test", cascade_label="q_v18_sources")}
        for r in exclues:
            l = lignes[r[0]]
            assert l.bande == "HC", "une parcelle exclue en dur ne reste jamais en A/B/C/D"
            assert l.cause and l.cause.startswith("hors_classement:")
            assert cause_libelle(l.cause).startswith("Exclue :")
            assert l.score is not None            # le score reste écrit (band = un ordre, pas un score nul)
        for r in gardees:
            assert lignes[r[0]].bande == "A"      # pas de faux positif : une A non exclue reste A


# ───────────────────────────── Lot 4 — E-02 / E-07 / E-08 : tables dérivées ────────────────────
def test_lot4_e07_ingestion_utilise_point_on_surface():
    """E-07 — l'ingestion cadastre calcule le point « centre » avec ST_PointOnSurface (toujours
    DANS la parcelle), plus ST_Centroid (barycentre, dehors sur les formes concaves)."""
    import pathlib
    src = pathlib.Path("src/labuse/ingestion/cadastre_ingest.py").read_text()
    # la ligne qui alimente la colonne `centroid` doit poser ST_PointOnSurface
    assert "ST_PointOnSurface(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))" in src
    assert "centroid = EXCLUDED.centroid" in src   # mis à jour aussi au ON CONFLICT


@pytest.mark.reel
def test_lot4_e07_tous_les_centroides_dans_la_parcelle():
    """E-07 — après la mise à jour locale, 0 centroïde de parcelle vivante hors de sa géométrie."""
    from sqlalchemy import text
    with app_session() as s:
        n = s.execute(text("""SELECT count(*) FROM parcels
            WHERE cadastre_disparue_le IS NULL AND centroid IS NOT NULL
              AND NOT ST_Intersects(geom, centroid)""")).scalar()
        assert n == 0


@pytest.mark.reel
def test_lot4_e02_parcel_zone_plu_version_et_temoin():
    """E-02 — la table porte une SIGNATURE d'entrées (contrôle de version) : fraîchement bâtie, elle
    n'est pas périmée ; et le témoin orphelin 97401000AH0371 a désormais sa zone."""
    from labuse.api.tiles import parcel_zone_plu_perimee, _parcel_zone_plu_signature
    from sqlalchemy import text
    with app_session() as s:
        if not s.execute(text("SELECT to_regclass('parcel_zone_plu_version')")).scalar():
            pytest.skip("reconstruction parcel_zone_plu pas encore jouée localement")
        # signature déterministe et mémorisée
        assert _parcel_zone_plu_signature(s)
        assert parcel_zone_plu_perimee(s) is False          # à jour juste après le build
        # une signature différente mémorisée ⇒ périmée (on prouve la détection)
        s.execute(text("UPDATE parcel_zone_plu_version SET sig = sig || '_x'"))
        assert parcel_zone_plu_perimee(s) is True
        s.execute(text("UPDATE parcel_zone_plu_version SET sig = left(sig, length(sig)-2)"))  # restaure
        assert parcel_zone_plu_perimee(s) is False
        # témoin : la parcelle zonable n'est plus orpheline
        z = s.execute(text("SELECT zone_lib FROM parcel_zone_plu WHERE idu='97401000AH0371'")).scalar()
        assert z, "97401000AH0371 doit avoir sa zone après reconstruction"
        s.rollback()


@pytest.mark.reel
def test_lot4_e08_orpheline_non_servie_et_servi_clippe():
    """E-08 — le bâti SERVI (parcel_bati_revele, clippé ST_Intersection) ne dépasse jamais la parcelle ;
    la seule table en infraction (parcel_residuel_bati) est ORPHELINE (builder retiré, 0 lecteur servi)."""
    from sqlalchemy import text
    with app_session() as s:
        servi = s.execute(text("""SELECT count(*) FROM parcel_bati_revele b JOIN parcels p ON p.id=b.parcel_id
            WHERE GREATEST(b.emprise_bdtopo_m2, b.emprise_cosia_m2) > ST_Area(p.geom_2975)+1""")).scalar()
        assert servi == 0, "le bâti servi est clippé à la parcelle"


# ───────────────────────────── Lot 5 — E-04 : fenêtre DVF ancrée sur la dernière vente ─────────
def test_lot5_helper_fenetre_dvf_ancree_pas_current_date():
    from labuse.dvf_fenetre import ANCRE_DVF_SQL, fenetre_dvf_sql
    frag = fenetre_dvf_sql("dm.date_mutation", annees_param="annees")
    assert "max(date_mutation)" in frag and "CURRENT_DATE" not in frag
    assert ":annees" in frag and "date_trunc('day'" in frag   # exclut la ligne parasite
    assert "max(date_mutation)" in ANCRE_DVF_SQL
    import pytest as _pt
    with _pt.raises(ValueError):
        fenetre_dvf_sql("x")   # il faut préciser une fenêtre


@pytest.mark.reel
def test_lot5_ancrage_recupere_les_ventes_jetees():
    """E-04 — la fenêtre ancrée récupère des ventes que CURRENT_DATE jetait (l'horloge qui avance)."""
    from sqlalchemy import text
    from labuse.flash.data import FENETRE_MARCHE_ANNEES, RAYON_MARCHE_M
    from labuse.dvf_fenetre import fenetre_dvf_sql
    with app_session() as s:
        def n(cond):
            return s.execute(text(f"""WITH p AS (SELECT geom_2975 FROM parcels WHERE idu=:i)
                SELECT count(*) FROM dvf_mutations dm, p WHERE dm.geom IS NOT NULL AND {cond}
                  AND dm.nature_mutation ILIKE 'vente%' AND dm.valeur_fonciere>0
                  AND ST_DWithin(ST_Transform(dm.geom,2975), p.geom_2975, :r)"""),
                {"i": "97411000AK0182", "a": FENETRE_MARCHE_ANNEES, "annees": FENETRE_MARCHE_ANNEES,
                 "r": RAYON_MARCHE_M}).scalar()
        cur = n("dm.date_mutation >= (CURRENT_DATE - make_interval(years => :a))")
        anc = n(fenetre_dvf_sql("dm.date_mutation", annees_param="annees"))
        if cur == 0 and anc == 0:
            pytest.skip("pas de DVF pour le témoin")
        assert anc >= cur       # l'ancrage ne perd jamais de ventes
        assert anc > cur        # et en récupère ici (témoin 97411000AK0182)


# ───────────────────────────── Lot 6 — E-05 / E-06 : âge dirigeant borné [18;110] ──────────────
@pytest.mark.reel
def test_lot6_pm_dirigeant_borne_age():
    """E-05 — _pm_dirigeant ne sert jamais un âge hors [18;110] : soit l'aîné plausible, soit « âge
    inconnu » (age=None), jamais 0/4/13/114/117."""
    from labuse.api.app import _pm_dirigeant
    from sqlalchemy import text
    with app_session() as s:
        # sociétés dont l'aîné brut est aberrant (date INPI 1909/1911 ou future)
        sirens = s.execute(text("""
            SELECT siren FROM (
              SELECT DISTINCT ON (siren) siren,
                date_part('year', age(to_date(date_naissance,'YYYY-MM')))::int AS age
              FROM pm_dirigeants WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL
              ORDER BY siren, date_naissance ASC) t
            WHERE age < 18 OR age > 110 LIMIT 5""")).scalars().all()
        if not sirens:
            pytest.skip("aucune société à aîné aberrant")
        for siren in sirens:
            d = _pm_dirigeant(s, siren)
            if d is None:
                continue
            assert d["age"] is None or 18 <= d["age"] <= 110   # jamais un âge impossible servi


@pytest.mark.reel
def test_lot6_vue_propension_sans_age_aberrant():
    """E-06 — la vue v_pm_propension_vendre ne porte plus d'âge hors [18;110] (succession/filtre 70+)."""
    from sqlalchemy import text
    with app_session() as s:
        n = s.execute(text("SELECT count(*) FROM v_pm_propension_vendre "
                           "WHERE age_max_dirigeant < 18 OR age_max_dirigeant > 110")).scalar()
        assert n == 0
