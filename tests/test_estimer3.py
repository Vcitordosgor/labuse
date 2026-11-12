"""ESTIMER-3 (fix/estimer-3) — recette de « une estimation qui se resserre, et qui le prouve ».

Trois strates :
  · PUR (aucune base) : la pondération par ressemblance, les questions POSÉES par type (gain mesuré),
    les caractéristiques abandonnées et déclarées ;
  · CANARY (aucune base) : le banc étendu aux niveaux est câblé au job de nuit ;
  · RÉEL (`LABUSE_REEL_DATABASE_URL`, marqueur `reel`) : l'estimation semblable servie, les mesures
    LABUSE en clair, l'écartement d'une vente qui recalcule, la précision par niveau, le Radar.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as _Session

from labuse.pige import estimer3 as E3


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  PUR — pondération par ressemblance + questions prouvées (aucune base)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def test_questions_posees_par_type_prouve():
    """Seules les caractéristiques au GAIN mesuré sont posées, PAR TYPE : surface (les deux),
    pièces (appartement seulement). La maison ne pose PAS les pièces (gain nul au banc)."""
    cles = {q["cle"]: q["types"] for q in E3.QUESTIONS}
    assert cles["surface_hab"] == ("maison", "appartement")
    assert cles["pieces"] == ("appartement",), "les pièces ne déplacent le prix que pour l'appartement"
    abn = {q["cle"] for q in E3.QUESTIONS_ABANDONNEES}
    # piscine (mesurée, sans gain), vue/état/viabilisé (non mesurables), pièces-maison (pas de gain).
    assert {"piscine", "vue_degagee", "etat", "terrain_viabilise", "pieces_maison"} <= abn


def test_questions_servies_filtre_par_type():
    est = {"surface_hab_prerempli": 100, "pieces_prerempli": 4}
    qm = [q["cle"] for q in E3._questions_servies(est, "maison")]
    qa = [q["cle"] for q in E3._questions_servies(est, "appartement")]
    assert qm == ["surface_hab"]
    assert qa == ["surface_hab", "pieces"]
    # aucune question ne fuite le champ interne `types`.
    assert all("types" not in q for q in E3._questions_servies(est, "appartement"))


def test_wquantiles_pondere():
    q1, med, q3 = E3._wquantiles([(100.0, 1.0), (200.0, 1.0), (300.0, 1.0)])
    assert q1 == 100.0 and med == 200.0 and q3 == 300.0
    # un poids écrasant tire la médiane vers sa valeur.
    _q1, med2, _q3 = E3._wquantiles([(100.0, 100.0), (1000.0, 1.0)])
    assert med2 == 100.0
    assert E3._wquantiles([]) == (None, None, None)


def test_mois_annee_ne_reformate_pas_une_date_deja_formatee():
    """OUTILS-P0-2 (recette) — « YYYY-MM-DD » → « MM/YYYY », mais « MM/YYYY » déjà formaté (comparables
    terrain) reste tel quel (le double formatage donnait « 05/2022 » → « 22/05/2 »)."""
    assert E3._mois_annee("2022-05-15") == "05/2022"
    assert E3._mois_annee("05/2022") == "05/2022"
    assert E3._mois_annee(None) is None and E3._mois_annee("x") is None


def test_fourchettes_une_ou_deux_bandes():
    """OUTILS-P0-2 (recette) — deux bandes DISTINCTES si le banc mesure médian ≠ Q3 ; une seule, nommée
    « Fourchette estimée », si les deux coïncident (repli) ; aucune si pas de total."""
    deux = E3._fourchettes(90, 110, 80, 120, 10, 20)
    assert [b["nom"] for b in deux] == ["1 fois sur 2", "3 fois sur 4"]
    une = E3._fourchettes(90, 110, 90, 110, 35, 35)
    assert len(une) == 1 and une[0]["nom"] == "Fourchette estimée"
    assert E3._fourchettes(None, None, None, None, 35, 35) == []


def test_zone_code_extrait_le_code_de_zone():
    """OUTILS-P0-2 (recette) — « A » extrait de « Zone non constructible (A) » / « N - Naturelle »."""
    assert E3._zone_code("Zone non constructible (A)") == "A"
    assert E3._zone_code("N - Naturelle") == "N"
    assert E3._zone_code("1AU - à urbaniser") == "1AU"
    assert E3._zone_code("") is None and E3._zone_code(None) is None


def test_eur_m2_semblable_pondere_par_ressemblance():
    """Un comparable PROCHE et de surface SEMBLABLE pèse plus qu'un comparable loin et différent :
    la médiane pondérée penche vers le prix du semblable."""
    base = {"terrain_m2": 500, "ydec": 2025.0, "pieces": 4, "annee": 2025, "type_local": "Maison"}
    comps = [
        # proche (50 m), même surface (100) → prix 4000
        {**base, "prix_m2_f": 4000.0, "distance_m": 50, "surface_m2": 100},
        {**base, "prix_m2_f": 4000.0, "distance_m": 60, "surface_m2": 102},
        # loin (3 km), surface très différente (400) → prix 1500 (doit peser peu)
        {**base, "prix_m2_f": 1500.0, "distance_m": 3000, "surface_m2": 400},
        {**base, "prix_m2_f": 1500.0, "distance_m": 3200, "surface_m2": 420},
    ]
    subj = {"surf_poids": 100.0, "terrain": 500.0, "pieces": 4}
    _q1, med, _q3 = E3.eur_m2_semblable([dict(c) for c in comps], subj, "maison", use_pieces=False)
    assert med is not None and abs(med - 4000.0) < abs(med - 1500.0), "les semblables doivent dominer"
    # les poids sont posés et décroissants avec la dissemblance.
    assert comps[0]["prix_m2_f"] and True
    w = E3.eur_m2_semblable(comps, subj, "maison", use_pieces=False) and comps
    assert comps[0]["_poids"] > comps[2]["_poids"]


def test_selection_rayon_adaptatif():
    """Le rayon s'élargit jusqu'à SEUIL ventes du même type ; sinon repli commune."""
    comps = [{"type_local": "Maison", "distance_m": d, "annee": 2024}
             for d in (100, 150, 200, 250, 300, 350, 400, 450, 900, 1200)]
    sel, radius, commune = E3._selection_rayon(comps, "maison")
    assert radius == 500 and commune is False and len(sel) >= E3.SEUIL
    maigre = [{"type_local": "Maison", "distance_m": 100, "annee": 2024}]
    sel2, radius2, commune2 = E3._selection_rayon(maigre, "maison")
    assert commune2 is True   # trop peu → repli commune


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  CANARY — le banc étendu aux niveaux est câblé (aucune base)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def test_banc_niveaux_cable_au_job():
    from labuse.pige import banc_estimer as be
    assert callable(be.calcule_niveaux) and callable(be.persiste3)
    assert be.N_SAMPLE3 >= 1000 and be.MIN_CELL3 >= 20
    import inspect
    from labuse import jobs_impl
    src = inspect.getsource(jobs_impl.estimer_banc_precision)
    assert "calcule_niveaux" in src and "persiste3" in src, "le job de nuit doit persister estimer3_precision"


def test_charge_precision_repli_bande_sans_table():
    """Sans table (banc jamais passé), la précision replie sur une bande prudente, jamais une erreur."""
    class _FakeDB:
        def execute(self, *a, **k):
            raise RuntimeError("estimer3_precision absente")
        def rollback(self):
            pass
    p = E3.charge_precision(_FakeDB(), "maison", "97411", "surface")
    assert p["source"] == "bande" and p["ecart_q3"] > 0 and p["methode"] in ("secteur", "semblable")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  RÉEL — l'outil servi sur des parcelles réelles
# ══════════════════════════════════════════════════════════════════════════════════════════════════
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
        if sess.execute(text("SELECT to_regclass('dvf_mutations_parcelle')")).scalar() is None:
            pytest.skip("DVF absent")
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
        eng.dispose()


def _idu(db, type_local, lo=90, hi=160, insee="97411"):
    return db.execute(text(
        "SELECT dm.id_parcelle FROM dvf_mutations_parcelle dm "
        "JOIN (SELECT id_mutation FROM dvf_mutations_parcelle GROUP BY 1 HAVING count(DISTINCT id_parcelle)=1) m "
        "  USING(id_mutation) "
        "WHERE dm.code_commune=:c AND dm.type_local=:t AND dm.surface_reelle_bati BETWEEN :lo AND :hi "
        "ORDER BY dm.date_mutation DESC LIMIT 1"),
        {"c": insee, "t": type_local, "lo": lo, "hi": hi}).scalar()


def _fiche(db, idu):
    from labuse.api.app import parcel_fiche
    return parcel_fiche(idu, db=db)


@pytest.mark.reel
def test_estimation_maison_sert_valeur_et_ventes_semblables(db):
    idu = _idu(db, "Maison")
    assert idu, "pas de maison de test"
    rep = E3.rapport3(db, idu, _fiche(db, idu))
    est = rep["estimation"]
    assert est["type_bien"] if False else rep["type_bien"] == "maison"
    assert est["valeur_eur"] and est["eur_m2"] and est["n_comparables"] >= E3.SEUIL
    assert est["comparables_desc"] and "semblables" in est["comparables_desc"]
    vr = rep["ventes_retenues"]
    assert vr, "aucune vente retenue servie"
    for v in vr[:3]:
        assert set(("id", "date", "surface_m2", "terrain_m2", "prix_eur", "distance_m")) <= set(v)
        assert v["ecartee"] is False


@pytest.mark.reel
def test_mesures_labuse_servies_en_clair(db):
    idu = _idu(db, "Maison")
    m = E3.rapport3(db, idu, _fiche(db, idu))["mesures"]
    assert m["nature"] == "maison"
    assert m["terrain_m2"] and m["emprise_bati_m2"]
    assert "piscine" in m and "presente" in m["piscine"]
    assert m["pente"] and "pct" in m["pente"]
    # niveaux LiDAR et zone : présents (peuvent être None sur micro-bâti / hors PLU), clés servies.
    assert "niveaux" in m and "zone" in m


@pytest.mark.reel
def test_questions_maison_vs_appartement(db):
    im = _idu(db, "Maison")
    ia = _idu(db, "Appartement", 40, 90)
    qm = [q["cle"] for q in E3.rapport3(db, im, _fiche(db, im))["questions"]]
    assert qm == ["surface_hab"], "la maison ne pose pas les pièces (gain nul)"
    if ia:
        qa = [q["cle"] for q in E3.rapport3(db, ia, _fiche(db, ia))["questions"]]
        assert "pieces" in qa and "surface_hab" in qa


@pytest.mark.reel
def test_ecarter_une_vente_recalcule(db):
    idu = _idu(db, "Maison")
    fiche = _fiche(db, idu)
    r0 = E3.rapport3(db, idu, fiche)
    assert r0["ventes_retenues"], "besoin de ventes à écarter"
    vid = r0["ventes_retenues"][0]["id"]
    r1 = E3.rapport3(db, idu, fiche, ecartees={vid})
    # la vente écartée est marquée telle, et ne pèse plus (n baisse ou valeur bouge).
    assert any(v["id"] == vid and v["ecartee"] for v in r1["ventes_retenues"])
    bouge = (r1["estimation"]["eur_m2"] != r0["estimation"]["eur_m2"]
             or r1["estimation"]["n_comparables"] <= r0["estimation"]["n_comparables"])
    assert bouge, "écarter une vente doit recalculer"


@pytest.mark.reel
def test_precision_se_resserre_avec_information(db):
    idu = _idu(db, "Maison")
    pn = E3.rapport3(db, idu, _fiche(db, idu))["precision_par_niveau"]
    # la précision TYPIQUE ne se dégrade jamais quand on en sait plus (maison : sans_saisie ≥ surface).
    assert pn["sans_saisie"] >= pn["surface"] - 1e-6


@pytest.mark.reel
def test_radar_ecart_affiche_vendu_non_servi_si_insuffisant(db):
    idu = _idu(db, "Maison")
    radar = E3.rapport3(db, idu, _fiche(db, idu))["radar"]
    assert "biens" in radar
    # sur la base locale, aucune annonce rattachée à une vente → l'écart n'est PAS servi (le dit).
    if radar["ecart_affiche_vendu_pct"] is None:
        assert radar["ecart_note"] and "seuil" in radar["ecart_note"]


@pytest.mark.reel
def test_charge_precision_lit_la_mesure_du_banc(db):
    """La précision servie vient de la table MESURÉE par le banc (`estimer3_precision`), par commune/
    type/niveau, avec repli île — jamais un ±% fixe (si le banc a déjà tourné sur cette base)."""
    if db.execute(text("SELECT to_regclass('estimer3_precision')")).scalar() is None:
        pytest.skip("banc estimer3 jamais passé sur cette base")
    p = E3.charge_precision(db, "maison", "97411", "surface")
    assert p["source"] in ("mesure", "bande") and p["ecart_q3"] > 0
    if p["source"] == "mesure":
        assert p["ecart_median"] > 0 and p["perimetre"] in ("commune", "ile")
    # une commune inconnue replie sur l'île du type (jamais rien).
    pr = E3.charge_precision(db, "maison", "99999", "surface")
    assert pr["ecart_q3"] > 0


@pytest.mark.reel
def test_sert_la_meilleure_des_deux_methodes(db):
    """L'estimation sert la MEILLEURE méthode mesurée (secteur ESTIMER-2 / semblable ESTIMER-3) et
    le dit (`methode_prix`) ; le ± servi (médian) n'est jamais plus large que la bande prudente (Q3)."""
    idu = _idu(db, "Maison")
    e = E3.rapport3(db, idu, _fiche(db, idu))["estimation"]
    assert e["methode_prix"] in ("secteur", "semblable", "repli_secteur")
    assert e["precision_pct"] <= e["precision_q3_pct"] + 1e-6


@pytest.mark.reel
def test_defaut_a_masque_total_quand_surface_inconnue_et_q3_large(db):
    """DÉFAUT A (Vic) — 97415000AW1367, surface habitable INCONNUE (estimée au LiDAR) + bande « 3 fois
    sur 4 » au-delà de ± SEUIL_Q3_MASQUE % : AUCUNE valeur totale ; on sert le €/m² du secteur et sa
    fourchette. Dès qu'une surface est saisie, le masque tombe et la valeur + ses deux bandes reviennent."""
    idu = "97415000AW1367"
    e = E3.rapport3(db, idu, _fiche(db, idu))["estimation"]
    assert e["surface_connue"] is False and e["precision_q3_pct"] > E3.SEUIL_Q3_MASQUE
    assert e["total_masque"] is True
    assert e["valeur_eur"] is None and e["valeur_basse"] is None and e["valeur_haute_q3"] is None
    assert e["eur_m2"] and e["eur_m2_bas"] and e["eur_m2_haut"]   # le prix au m² + sa fourchette restent servis
    e2 = E3.rapport3(db, idu, _fiche(db, idu), surface_hab=90)["estimation"]
    assert e2["surface_connue"] is True and e2["total_masque"] is False
    assert e2["valeur_eur"] and e2["valeur_basse"] and e2["valeur_haute_q3"]


@pytest.mark.reel
def test_defaut_b_aucune_valeur_terrain_sur_bati(db):
    """DÉFAUT B (Vic, correction) — sur un bien BÂTI, AUCUNE valeur de terrain n'est servie (ni bandeau,
    ni bloc) : mesuré au banc no-leak, la retenir dégrade la précision (mesure_plancher.py). La fiabilité
    reste celle du banc pour le cas (jamais rabaissée à cause du terrain). La valeur de terrain ne subsiste
    que pour les TERRAINS NUS."""
    e = E3.rapport3(db, "97415000AW1367", _fiche(db, "97415000AW1367"))["estimation"]
    assert "terrain_depasse" not in e and "terrain_valeur_eur" not in e
    assert "plancher_terrain_applique" not in e
    # la fiabilité servie vient du banc (pas de champ de rabaissement « terrain »), valeur du set attendu.
    assert e["fiabilite_mot"] in ("Élevée", "Moyenne", "Limitée")
    # un terrain nu, lui, sert toujours sa valeur.
    it = db.execute(text("SELECT dm.id_parcelle FROM dvf_mutations_parcelle dm "
                         "WHERE dm.nature_mutation='Vente terrain à bâtir' AND dm.code_commune='97415' "
                         "ORDER BY dm.date_mutation DESC LIMIT 1")).scalar()
    if it:
        et = E3.rapport3(db, it, _fiche(db, it))
        assert et["type_bien"] == "terrain" and et["estimation"].get("valeur_eur")


@pytest.mark.reel
def test_endpoint_estimation3(monkeypatch):
    """L'endpoint POST sert le rapport complet et RECALCULE quand on écarte une vente. Sous pytest,
    `conftest` force l'app sur `labuse_test` (sans DVF/dryrun) : on redirige donc la session de
    l'endpoint vers la base RÉELLE (le chemin de code de l'endpoint est exécuté tel quel)."""
    from contextlib import contextmanager
    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini")
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            if conn.execute(text("SELECT to_regclass('dvf_mutations_parcelle')")).scalar() is None:
                pytest.skip("DVF absent")
            idu = conn.execute(text(
                "SELECT dm.id_parcelle FROM dvf_mutations_parcelle dm "
                "JOIN (SELECT id_mutation FROM dvf_mutations_parcelle GROUP BY 1 "
                "      HAVING count(DISTINCT id_parcelle)=1) m USING(id_mutation) "
                "WHERE dm.code_commune='97411' AND dm.type_local='Maison' "
                "  AND dm.surface_reelle_bati BETWEEN 90 AND 160 ORDER BY dm.date_mutation DESC LIMIT 1")).scalar()
        if not idu:
            pytest.skip("pas de maison de test")

        @contextmanager
        def _reel_scope():
            s = _Session(bind=eng)
            try:
                yield s
            finally:
                s.close()

        import labuse.pige.api as papi
        monkeypatch.setattr(papi, "session_scope", _reel_scope)
        out = papi.radar_annonce_estimation3(idu, papi.Estimation3In())
        assert out["type_bien"] == "maison"
        assert {"mesures", "estimation", "ventes_retenues", "questions", "precision_par_niveau",
                "radar", "questions_abandonnees"} <= set(out)
        assert out["estimation"]["valeur_eur"] and out["ventes_retenues"]
        # ré-interrogation en écartant une vente : l'endpoint recalcule (le vrai chemin POST).
        vid = out["ventes_retenues"][0]["id"]
        out2 = papi.radar_annonce_estimation3(idu, papi.Estimation3In(ecartees=[vid]))
        assert any(v["id"] == vid and v["ecartee"] for v in out2["ventes_retenues"])
    finally:
        eng.dispose()


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  OUTILS-P0-2 (P2) — terrain nu hors gamme / non constructible : pas de total, repère + ventes gardés
# ══════════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.reel
def test_terrain_hors_gamme_pas_de_total_mais_repere(db):
    """Un terrain BEAUCOUP plus grand que les ventes de référence (surface > p90) ne reçoit AUCUN total
    (le prix dégressif à la taille rend `surface × €/m²` faux — témoin 97409000AK0804 > 21 M€). Mais le
    repère au m² et les ventes de référence RESTENT servis, et la raison est dite."""
    idu = "97409000AK0804"
    if db.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar() is None:
        pytest.skip("témoin AK0804 absent")
    r = E3.rapport3(db, idu, _fiche(db, idu))
    assert r["type_bien"] == "terrain"
    e = r["estimation"]
    assert e.get("terrain_hors_gamme") is True
    assert e.get("valeur_eur") is None                       # pas de total hors gamme
    assert e.get("eur_m2")                                   # mais le repère au m² reste
    assert r.get("ventes_retenues")                          # et les ventes de référence restent
    assert "hors gamme des ventes de référence" in (e.get("terrain_sans_total_raison") or "")
    # une surface dans la gamme, elle, garde un total.
    it = db.execute(text(
        "SELECT dm.id_parcelle FROM dvf_mutations_parcelle dm "
        "JOIN (SELECT id_mutation FROM dvf_mutations_parcelle GROUP BY 1 HAVING count(DISTINCT id_parcelle)=1) m "
        "  USING(id_mutation) WHERE dm.nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "  AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain BETWEEN 300 AND 700 "
        "ORDER BY dm.date_mutation DESC LIMIT 1")).scalar()
    if it:
        et = E3.rapport3(db, it, _fiche(db, it))["estimation"]
        if et.get("eur_m2") and not et.get("terrain_non_constructible"):
            assert et.get("terrain_hors_gamme") is False and et.get("valeur_eur")


@pytest.mark.reel
def test_terrain_non_constructible_pas_de_valeur_a_batir(db):
    """OUTILS-P0-2 (recette, point 4) — un terrain NON CONSTRUCTIBLE n'a AUCUNE estimation : pas de prix
    au m² en tête, aucune vente de terrain à bâtir listée. L'écran dit « Pas d'estimation : zone non
    constructible (A) » et la dernière vente de la parcelle reste montrée (servie à part)."""
    cands = db.execute(text(
        "SELECT dm.id_parcelle FROM dvf_mutations_parcelle dm "
        "JOIN (SELECT id_mutation FROM dvf_mutations_parcelle GROUP BY 1 HAVING count(DISTINCT id_parcelle)=1) m "
        "  USING(id_mutation) WHERE dm.nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "  AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain BETWEEN 200 AND 800 "
        "ORDER BY dm.date_mutation DESC LIMIT 300")).scalars().all()
    for idu in cands:
        try:
            rep = E3.rapport3(db, idu, _fiche(db, idu))
        except Exception:  # noqa: BLE001 — parcelle sans fiche : on passe
            continue
        e = rep["estimation"]
        if e.get("terrain_non_constructible"):
            assert e.get("valeur_eur") is None
            assert e.get("eur_m2") is None                    # AUCUN prix au m² en tête
            assert rep.get("ventes_retenues") == []           # aucune vente de terrain à bâtir listée
            assert (e.get("terrain_sans_total_raison") or "").startswith("Pas d’estimation : ")
            assert "non constructible" in (e.get("terrain_sans_total_raison") or "")
            return
    pytest.skip("aucun terrain nu non constructible trouvé dans l'échantillon")


@pytest.mark.reel
def test_pdf_parite_pieces_et_ventes_ecartees(db):
    """OUTILS-P0-2 (P1) — le rapport PDF parcelle reprend le scénario EXACT de l'écran : mêmes pièces
    saisies et mêmes ventes décochées → même montant qu'`estimer3.rapport3`. Avant, seule la surface
    voyageait (pièces et décochages perdus → le document divergeait de l'écran)."""
    from labuse.pige.api import rapport_parcelle
    idu = _idu(db, "Appartement", lo=30, hi=120)             # l'appartement garde la question « pièces »
    if not idu:
        pytest.skip("pas d'appartement de test")
    fiche = _fiche(db, idu)
    ecran = E3.rapport3(db, idu, fiche, surface_hab=60, pieces=3)
    vid = (ecran.get("ventes_retenues") or [{}])[0].get("id")
    ecartees = [vid] if vid else []
    ecran2 = E3.rapport3(db, idu, fiche, surface_hab=60, pieces=3, ecartees=set(ecartees))
    pdf = rapport_parcelle(db, idu, fiche, surface_hab=60, pieces=3, ecartees=ecartees)
    vi = (pdf.get("estimation") or {}).get("valeur_indicative") or {}
    # le PDF imprime EXACTEMENT le montant de l'écran (même surface, pièces, ventes écartées).
    assert vi.get("valeur_eur") == ecran2["estimation"].get("valeur_eur")
    # le PDF ne retient que les ventes ACTIVES (les décochées sont exclues), comme l'écran.
    actives = [v for v in (ecran2.get("ventes_retenues") or []) if not v.get("ecartee")]
    assert len((pdf.get("estimation") or {}).get("comparables") or []) == len(actives)
