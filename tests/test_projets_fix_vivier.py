"""PROJETS-FIX F1 — le compteur du wizard et le compteur « À trier » du projet ouvert sortent de
LA MÊME requête (`_cadrage_total`) : ils sont IDENTIQUES PAR CONSTRUCTION.

Contexte (diagnostic D) : Vic a créé deux projets ; le wizard annonçait ~30 000 parcelles, les
projets ouverts affichaient « vivier 0 ». Deux fuites prouvées :
  · le RÉCAP lisait `r.total` = `_q_v2_stats` (total carte GONFLÉ, ~79 % d'exclusions dures) au lieu
    du vivier réel — d'où un nombre que le projet démentait ;
  · l'étape CADRAGE comptait l'ÎLE ENTIÈRE (le périmètre communal, étape séparée du wizard, n'était
    pas passé au compteur) pendant qu'on cadrait une commune.
Le fix aligne les deux sur `_cadrage_total(...)["total"]`, exactement ce que `/{pid}/parcelles`
sert à « À trier ». Ce test verrouille l'invariant et la sensibilité au périmètre.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import projets
from labuse.api.projets import CadrageIn, _cadrage_page_idus, _cadrage_total, clean_cadrage, projet_compteur
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

RUN = Q_A_RUN_LABEL   # `_cadrage_total` joint dryrun ET score sur le run servi (épinglé au label)

_WKT = ("POLYGON((55.45 -20.90, 55.451 -20.90, 55.451 -20.901, "
        "55.45 -20.901, 55.45 -20.90))")


def _parcel(session, idu: str, commune: str, surface: float) -> int:
    return session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        "                     centroid, bbox) "
        "VALUES (:i, :c, 'AS', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), :s, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "c": commune, "w": _WKT, "s": surface}).scalar()


def _seed(session):
    """Deux communes, parcelles NON étage 0, toutes scorées au run servi. Alpha : 3 parcelles de
    800 m² ; Beta : 2 parcelles de 800 m². Aucune n'a 900 m² → un cadrage `surfaceMin=900` est
    LÉGITIMEMENT vide (analogue de « zone UB à Saint-Denis » : facette valable, univers vide)."""
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles) "
        "VALUES (:r, 'fix-test', 'abc', '{}', 5)"), {"r": RUN})
    rang = 0
    for commune, n in [("Alpha", 3), ("Beta", 2)]:
        for k in range(n):
            idu = f"97999{commune[0]}A{k:04d}00"[:14].ljust(14, "0")
            pid = _parcel(session, idu, commune, 800)
            session.execute(text(
                "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
                "opportunity_score, status, q_score, a_score, matrice_statut) "
                "VALUES (:r, :p, 70, 10, 'a_creuser', 60, 40, 'a_creuser')"),
                {"r": RUN, "p": pid})
            rang += 1
            session.execute(text(
                "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
                "rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
                "VALUES (:r, :i, 0.5, 10, 90, :rg, 0.2, 1.5, '[]', false, 'a_creuser', 'fix-test')"),
                {"r": RUN, "i": idu, "rg": rang})
    session.flush()


def _wizard(db, cadrage: dict) -> int:
    """Le nombre que le WIZARD affiche (compteur endpoint /projets/compteur)."""
    projets._COMPTEUR_CACHE.clear()
    return projet_compteur(CadrageIn(cadrage=cadrage), db)["vivier"]


def _a_trier(db, cadrage: dict) -> int:
    """Le nombre que « À trier » sert dans le projet ouvert (offset 0)."""
    return _cadrage_total(db, clean_cadrage(cadrage))["total"]


@pytest.mark.db
def test_wizard_et_a_trier_identiques_par_construction(db_session):
    """L'INVARIANT central : pour tout cadrage, wizard == À trier == la page réellement servie."""
    _seed(db_session)
    cadrages = [
        {"communes": ["Alpha"]},                       # cadrage communes SANS facette → vivier > 0
        {"communes": ["Alpha"], "surfaceMin": 500},    # analogue « cadrage de Vic » (facette) → > 0
        {"communes": ["Alpha"], "surfaceMin": 900},    # analogue « zone absente » → vide LÉGITIME
        {"communes": ["Alpha", "Beta"]},               # deux communes
        {"surfaceMin": 500},                           # toute l'île (sans commune)
    ]
    for cad in cadrages:
        wiz = _wizard(db_session, cad)
        trier = _a_trier(db_session, cad)
        page = len(_cadrage_page_idus(db_session, clean_cadrage(cad), 10_000, 0))
        assert wiz == trier == page, f"divergence sur {cad} : wizard={wiz} à_trier={trier} page={page}"


@pytest.mark.db
def test_deux_cadrages_de_vic_donnent_un_vivier_non_nul(db_session):
    """« création par l'API avec les deux cadrages de Vic (+ un cadrage communes sans facette) →
    vivier > 0 et égal au compteur du wizard ». Les cadrages qui ONT un univers rendent > 0 ; le
    wizard annonce ce même nombre — jamais un total gonflé qui serait ensuite démenti."""
    _seed(db_session)
    for cad in [{"communes": ["Alpha"], "surfaceMin": 500},   # cadrage « de Vic » (avec facette)
                {"communes": ["Alpha", "Beta"]},              # cadrage communes sans facette
                {"surfaceMin": 500}]:                          # toute l'île
        wiz = _wizard(db_session, cad)
        assert wiz > 0, f"vivier attendu > 0 pour {cad}, obtenu {wiz}"
        assert wiz == _a_trier(db_session, cad)


@pytest.mark.db
def test_le_perimetre_scope_le_compteur(db_session):
    """La cause du mirage : le compteur DOIT dépendre du périmètre. Sur l'île entière il compte les
    deux communes (5) ; borné à Alpha il n'en compte que 3. Sans cette sensibilité, le wizard
    annonçait l'île pendant qu'on cadrait une commune."""
    _seed(db_session)
    assert _wizard(db_session, {"surfaceMin": 500}) == 5              # Alpha (3) + Beta (2)
    assert _wizard(db_session, {"communes": ["Alpha"], "surfaceMin": 500}) == 3
    assert _wizard(db_session, {"communes": ["Beta"], "surfaceMin": 500}) == 2


@pytest.mark.db
def test_cadrage_vide_legitime_rend_zero_des_deux_cotes(db_session):
    """Le cas « zone absente de la commune » (cadrage 236 de Vic) : un vrai 0, cohérent des deux
    côtés — le wizard ne promet plus 30 000. Ce 0 est le déclencheur de l'état vide F4."""
    _seed(db_session)
    cad = {"communes": ["Alpha"], "surfaceMin": 900}
    assert _wizard(db_session, cad) == 0
    assert _a_trier(db_session, cad) == 0
