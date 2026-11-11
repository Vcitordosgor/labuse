"""ESTIMER-2 (fix/estimer-2) — recette des corrections de l'outil « Estimer un bien », montrées sur
des parcelles RÉELLES (base locale servie). Chaque bloc correspond à un point du mandat :

  · D-1  — « dernière vente » lue sur TOUT l'historique DVF (2014 → aujourd'hui), libellé véridique ;
  · D-3  — repère €/m² de terrain à rayon ADAPTATIF (500→1500 m puis commune), n + périmètre servis ;
  · D-4  — surface habitable = emprise bâtie × niveaux MESURÉS (hauteur LiDAR), hypothèse en clair ;
  · D-5  — fourchette + fiabilité MESURÉES par commune/type (quartiles du banc), pas ±30 % fixe.

Nécessite la base réelle (`LABUSE_REEL_DATABASE_URL`, marqueur `reel`) ; sinon SKIP — jamais d'échec
à l'aveugle. Lecture seule, tout est annulé en fin de module."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as _Session

pytestmark = [pytest.mark.reel]


@pytest.fixture(scope="module")
def db():
    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini (recette réelle)")
    eng = create_engine(url)
    conn = eng.connect()
    trans = conn.begin()
    sess = _Session(bind=conn)
    try:
        if sess.execute(text("SELECT to_regclass('dvf_mutations_histo')")).scalar() is None:
            pytest.skip("dvf_mutations_histo absente de la base")
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
        eng.dispose()


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  D-1 — « dernière vente » sur tout l'historique 2014 → aujourd'hui ; libellé véridique
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _histo_only_idus(db, n=50):
    """Parcelles vendues 2014-2020 (historique) et JAMAIS depuis 2021 — celles que l'outil disait à
    tort « aucune depuis 2014 » (ESTIMER-AUDIT-1 §2, ~37 500 parcelles)."""
    return [r[0] for r in db.execute(text(
        "SELECT DISTINCT h.id_parcelle FROM dvf_mutations_histo h "
        "WHERE h.nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "  AND NOT EXISTS (SELECT 1 FROM dvf_mutations_parcelle p "
        "    WHERE p.id_parcelle = h.id_parcelle "
        "      AND p.nature_mutation IN ('Vente','Vente terrain à bâtir')) "
        "  AND EXISTS (SELECT 1 FROM parcels pa WHERE pa.idu = h.id_parcelle) "
        "LIMIT :n"), {"n": n}).all()]


def test_derniere_vente_couvre_lhistorique_2014(db):
    """Les parcelles vendues 2014-2020 et pas depuis reçoivent désormais leur VRAIE date de dernière
    vente (plus de faux « aucune depuis 2014 »)."""
    from labuse.pige.api import derniere_vente_parcelle
    idus = _histo_only_idus(db, 50)
    assert idus, "échantillon historique vide (base sans histo ?)"
    for idu in idus:
        v = derniere_vente_parcelle(db, idu)
        assert v and v["date"], f"{idu} : dernière vente introuvable alors qu'une vente 2014-2020 existe"
        assert 2014 <= int(v["date"][:4]) <= 2020, f"{idu} : {v['date']} hors historique"
        assert v["source"].startswith("historique"), f"{idu} : source {v['source']} inattendue"


def test_derniere_vente_ne_regresse_pas_le_geo_dvf(db):
    """Une parcelle qui a une vente 2021+ garde EXACTEMENT la dernière vente du géo-DVF (le repli
    historique ne la touche jamais : le géo-DVF est toujours plus récent)."""
    from labuse.pige.api import derniere_vente_parcelle
    # scope comparable : ventes de gré à gré (le lecteur narrowe là ; le repli ne touche de toute
    # façon JAMAIS une parcelle dont la vue n'est pas vide — garanti par `if not dvf_last` dans app.py).
    idus = [r[0] for r in db.execute(text(
        "SELECT idu FROM v_parcel_dvf_last WHERE date_mutation >= DATE '2021-01-01' "
        "  AND nature IN ('Vente','Vente terrain à bâtir') LIMIT 40")).all()]
    assert idus
    for idu in idus:
        vue = db.execute(text("SELECT date_mutation, valeur FROM v_parcel_dvf_last WHERE idu=:i"),
                         {"i": idu}).mappings().first()
        v = derniere_vente_parcelle(db, idu)
        assert v["date_mutation"] == vue["date_mutation"], f"{idu} : date divergente"
        assert v["source"] == "geo-DVF 2021+"


def test_derniere_vente_signale_les_ventes_groupees(db):
    """Une vente multi-parcelles (DVF porte la valeur sur la mutation entière) est signalée
    `multi_parcelles` et son prix au m² est SUPPRIMÉ (jamais la valeur du groupe ÷ une seule
    parcelle — ESTIMER-AUDIT-1 §4-g)."""
    from labuse.pige.api import derniere_vente_parcelle
    # une parcelle d'une mutation historique groupée
    idu = db.execute(text(
        "WITH m AS (SELECT id_mutation FROM dvf_mutations_histo "
        "           WHERE nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "           GROUP BY id_mutation HAVING count(DISTINCT id_parcelle) > 1 LIMIT 1) "
        "SELECT h.id_parcelle FROM dvf_mutations_histo h JOIN m USING (id_mutation) "
        "JOIN parcels p ON p.idu = h.id_parcelle "
        "WHERE NOT EXISTS (SELECT 1 FROM dvf_mutations_parcelle d "
        "  WHERE d.id_parcelle = h.id_parcelle AND d.nature_mutation IN ('Vente','Vente terrain à bâtir')) "
        "LIMIT 1")).scalar()
    if not idu:
        pytest.skip("aucune mutation historique groupée exploitable")
    v = derniere_vente_parcelle(db, idu)
    assert v["multi_parcelles"] is True and v["n_parcelles"] > 1
    assert v["prix_m2_bati"] is None and v["prix_m2_terrain"] is None


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  D-3 — repère terrain à rayon ADAPTATIF (500→1500 m puis commune) ; n + périmètre servis
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _terrain_idus(db, n=120):
    return [r[0] for r in db.execute(text(
        "SELECT p.idu FROM parcels p JOIN dvf_mutations_parcelle d ON d.id_parcelle = p.idu "
        "WHERE d.nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "  AND COALESCE(d.surface_reelle_bati,0)=0 AND d.surface_terrain > 0 "
        "GROUP BY p.idu LIMIT :n"), {"n": n}).all()]


def test_terrain_rayon_adaptatif_couvre_quand_la_commune_a_des_ventes(db):
    """Le repère terrain est servi pour CHAQUE parcelle dès que la commune a des ventes de terrain
    (objectif du mandat : plus aucun terrain sans prix). Le périmètre retenu est servi."""
    from labuse.marche_service import comparateur_terrain
    idus = _terrain_idus(db, 120)
    assert idus
    sans = [idu for idu in idus if not comparateur_terrain(db, idu).get("median")]
    assert not sans, f"{len(sans)} terrains sans prix malgré des ventes communales (ex {sans[:3]})"


def test_terrain_perimetre_et_elargissement(db):
    """Le repère porte son PÉRIMÈTRE (rayon réel ou commune), son n et ses quartiles ; les rayons
    retenus appartiennent bien à l'échelle adaptative 500/1000/1500 m ou au repli commune."""
    from labuse.marche_service import comparateur_terrain
    for idu in _terrain_idus(db, 60):
        r = comparateur_terrain(db, idu)
        if not r.get("median"):
            continue
        assert r["n"] >= 1 and r["perimetre"]
        if r["commune_fallback"]:
            assert r["perimetre"] == "commune" and r["radius_m"] is None
        else:
            assert r["radius_m"] in (500, 1000, 1500)
            assert r["perimetre"] == f"{r['radius_m']} m autour de la parcelle"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  D-4 — surface habitable = emprise × niveaux MESURÉS (hauteur LiDAR), hypothèse en clair
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def test_surface_emprise_niveaux_lidar_hypothese_en_clair(db):
    """Sans surface saisie ni vente DVF, la surface habitable est estimée depuis l'emprise au sol ET
    le nombre de niveaux MESURÉ (hauteur LiDAR), et l'hypothèse est servie en clair. Le résultat reste
    CALIBRÉ au bâti habitable réel (emprise × niveaux BRUT surestime ~×2 → jamais servi tel quel)."""
    from labuse.pige.api import _niveaux_lidar_parcelle, _surface_pour_total
    rows = db.execute(text(
        "SELECT p.idu, b.emprise_bati_m2 FROM parcels p "
        "JOIN p_model_bati b ON b.idu = p.idu AND b.emprise_bati_m2 > 40 "
        "JOIN batiment_hauteur_lidar l ON l.idu = p.idu "
        "WHERE labuse_hauteur_lidar_m(l.egout_m) BETWEEN 5 AND 9 LIMIT 15")).all()
    if not rows:
        pytest.skip("aucune parcelle bâtie à ≥2 niveaux LiDAR")
    n_ok = 0
    for idu, emp in rows:
        niveaux = _niveaux_lidar_parcelle(db, idu)
        if not niveaux:
            continue
        s, src = _surface_pour_total(db, idu, float(emp), None, idu[:5], None, bati_mesure=True)
        if src is None or src["source"] != "emprise_niveaux_lidar":
            continue  # commune sans assise de ratio → repli légitime
        n_ok += 1
        assert f"× {niveaux} niveau" in src["ligne"] and "au sol" in src["ligne"]
        # calibré : jamais le produit brut emprise × niveaux (qui surestimerait ~×2)
        assert s < float(emp) * niveaux, f"{idu} : surface {s} ≈ emprise×niveaux brut (non calibré)"
    assert n_ok, "aucune estimation emprise×niveaux produite (assises communales absentes ?)"


def test_surface_sans_lidar_replie_sur_ratio_communal(db):
    """Sans hauteur LiDAR, on replie sur le ratio communal seul (le « à défaut » du mandat),
    source `emprise_ratio`, et l'hypothèse dit « nombre de niveaux non mesuré »."""
    from labuse.pige.api import _niveaux_lidar_parcelle, _surface_pour_total
    idu = db.execute(text(
        "SELECT p.idu FROM parcels p JOIN p_model_bati b ON b.idu = p.idu AND b.emprise_bati_m2 > 40 "
        "WHERE NOT EXISTS (SELECT 1 FROM batiment_hauteur_lidar l WHERE l.idu = p.idu "
        "  AND labuse_hauteur_lidar_m(l.egout_m) > 0) LIMIT 1")).scalar()
    if not idu:
        pytest.skip("toutes les parcelles bâties portent du LiDAR")
    assert _niveaux_lidar_parcelle(db, idu) is None
    emp = db.execute(text("SELECT emprise_bati_m2 FROM p_model_bati WHERE idu=:i"), {"i": idu}).scalar()
    s, src = _surface_pour_total(db, idu, float(emp), None, idu[:5], None, bati_mesure=True)
    if src is not None:
        assert src["source"] == "emprise_ratio"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  D-5 — marge d'erreur MESURÉE par commune/type (quartiles du banc) remplace le ±30 % fixe
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def test_fiabilite_servie_vient_de_la_calibration_mesuree(db):
    """Le ±% servi = l'écart Q3 MESURÉ du (type, commune), la fiabilité découle de l'écart MÉDIAN
    mesuré + n. Nécessite une calibration (le banc a tourné) ; sinon on la calcule ici."""
    from labuse.pige import banc_estimer as be
    from labuse.pige.api import _fiabilite_mesuree
    if db.execute(text("SELECT to_regclass('estimer_precision_calibration')")).scalar() is None:
        be.persiste(db.get_bind(), be.calcule(db.get_bind(), n_sample=120))
    cal = be.charge_calibration(db, "appartement", "*")
    assert cal and cal["ecart_q3"]
    niveau, ecart, extra = _fiabilite_mesuree(db, "appartement", "*", 50, 3000, 2600, 3400, False)
    assert ecart == round(cal["ecart_q3"]), "le ±% servi doit être l'écart Q3 mesuré"
    assert extra["fourchette_source"] in ("mesure_commune", "mesure_ile")
    assert extra["ecart_median_mesure"] == round(cal["ecart_median"])
    # cohérence du mot de fiabilité avec l'écart médian mesuré
    if cal["ecart_median"] < 15 and cal["n"] >= 15:
        assert niveau == "fiable"


def test_fourchette_mesuree_remplace_le_30pct_fixe():
    """`estimation_prix.fourchette` : une demi-largeur MESURÉE remplace le ±30 % fixe et la mention
    dit « mesurée » (pas l'ancien backtest). Sans argument → ±30 % historique (compat)."""
    from labuse.estimation_prix import fourchette, DEMI_LARGEUR_PCT
    fixe = fourchette(400000)
    assert fixe["demi_largeur_pct"] == DEMI_LARGEUR_PCT and fixe["mesuree"] is False
    mes = fourchette(400000, demi_largeur_pct=42, ecart_median=31)
    assert mes["demi_largeur_pct"] == 42 and mes["mesuree"] is True
    assert "MESURÉE" in mes["mention"] and "31 %" in mes["mention"]
    assert mes["bas"] < 400000 < mes["haut"]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  D-2 — médiane PONDÉRÉE servie partout via un lecteur UNIQUE (fiche == Estimer == documents)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def test_mediane_ponderee_est_un_vrai_quantile_pondere():
    """`_mediane_ponderee` tire la médiane vers les comparables qui PÈSENT le plus (poids = distance ×
    surface × ancienneté) ; poids égaux (sujet absent) → médiane ~simple sur un échantillon symétrique."""
    from labuse.faisabilite.bilan import _mediane_ponderee
    base = [{"prix": p, "dist": 100.0, "annee": 2025, "surf": 90.0, "terr": 400.0}
            for p in (2000, 2500, 3000, 3500, 4000)]
    _q1, med_eq, _q3 = _mediane_ponderee(base, None, None, "maison")
    assert abs(med_eq - 3000) <= 1  # poids ~égaux → médiane centrale
    # un sujet de petite surface tire la médiane vers les petits comparables (= moins chers ici)
    petits = [{"prix": 2000, "dist": 50, "annee": 2025, "surf": 50, "terr": 400},
              {"prix": 2200, "dist": 60, "annee": 2025, "surf": 55, "terr": 400},
              {"prix": 5000, "dist": 1400, "annee": 2021, "surf": 300, "terr": 400}]
    _q1, med_w, _q3 = _mediane_ponderee(petits, 52.0, 400.0, "maison")
    assert med_w < 3000, "la pondération doit tirer vers les comparables ressemblants (petits/proches)"


def test_mediane_servie_identique_fiche_et_estimer(db):
    """UN SEUL lecteur : pour une parcelle au secteur fourni, la médiane de `reference_locale` (Estimer/
    Radar) est IDENTIQUE à celle de `sector_price` (fiche/Dossier) — même calcul pondéré, même
    échantillon → 0 écart entre documents."""
    from labuse.faisabilite.bilan import reference_locale, sector_price
    from labuse.faisabilite.engine import Hypotheses
    idus = [r[0] for r in db.execute(text(
        "SELECT p.idu FROM parcels p WHERE left(p.idu,5)='97411' "
        "AND EXISTS (SELECT 1 FROM dvf_mutations d WHERE d.commune=p.commune "
        "  AND d.type_local ILIKE '%MAISON%' AND d.nature_mutation='Vente') LIMIT 25")).all()]
    hyp = Hypotheses.charger("Saint-Denis")
    n_compares = 0
    for idu in idus:
        rl = reference_locale(db, idu, "maison", return_echantillon=True)
        if not rl or rl.get("eur_m2") is None:
            continue  # secteur insuffisant → reference_locale None (chemin pré-existant, hors invariant)
        pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        sp = sector_price(db, pid, hyp, type_prioritaire="maison")
        if sp.get("radius_m") != rl.get("rayon_m") or sp.get("commune_fallback"):
            continue  # rayons résolus différents → échantillons différents (hors invariant strict)
        n_compares += 1
        assert round(rl["eur_m2"]) == sp["median"], f"{idu} : Estimer {round(rl['eur_m2'])} ≠ fiche {sp['median']}"
    assert n_compares, "aucune parcelle au secteur fourni pour comparer les deux lecteurs"
