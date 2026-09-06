"""Scan patrimoine (M02) — inventaire du foncier d'une PERSONNE MORALE. L'endpoint scoré n'avait
AUCUN test. Ici : « ne lève pas » + le ménage des vestiges (matrice morte retirée du fil) + les
gestes de restitution (actionnables, valorisation, signal INPI, assiette contiguë)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

pytestmark = pytest.mark.db

# deux carrés ADJACENTS (partagent une arête → contigus à ≤ 0,5 m)
_WKT = [
    "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))",
    "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))",
]


def _seed(db, idu, wkt, siren, denom, tier="a_creuser", zone_fam="U"):
    pid = db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'Patville','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt}).scalar()
    db.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r,:i,0.5,30,90,1,0.2,1.5,'[]',false,:t,'test')"), {"r": Q_A_RUN_LABEL, "i": idu, "t": tier})
    db.execute(text("INSERT INTO parcelle_personne_morale (idu, siren, denomination) VALUES (:i,:s,:d)"),
               {"i": idu, "s": siren, "d": denom})
    db.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) VALUES (:i,:z,:f)"),
               {"i": idu, "z": "U", "f": zone_fam})
    return pid


def test_patrimoine_search_ne_leve_pas(db_session):
    from labuse.api.modules import patrimoine_search
    assert patrimoine_search("x", db=db_session) == []          # < 2 car. → vide, jamais une exception
    _seed(db_session, "97499000PA0001", _WKT[0], "111222333", "SCI PATCO ALPHA")
    out = patrimoine_search("PATCO", db=db_session)             # ne lève pas
    assert any(r["siren"] == "111222333" and r["n"] >= 1 for r in out)


def test_patrimoine_hors_ecartees_par_vous(db_session, monkeypatch):
    """CONNEXIONS-2 Lot 4 (KO-10) — « actionnables » retire les parcelles que CE COMPTE a écartées
    dans un de ses projets (projet_parcelles.statut='ecartee') ; le libellé le dit. Sans décision (ou
    sans compte), rien n'est retiré et aucun « hors écartées » n'est affirmé (plus de faux ami)."""
    import types
    monkeypatch.setattr("labuse.api.app._score_v2_run_id", lambda _db: Q_A_RUN_LABEL)
    from labuse.api.modules import patrimoine
    s = db_session
    siren = "777888999"
    _seed(s, "97499000EC0001", _WKT[0], siren, "SCI ECART", tier="a_creuser")
    pid2 = _seed(s, "97499000EC0002", _WKT[1], siren, "SCI ECART", tier="a_creuser")
    # SANS compte → 2 actionnables, pas de mention « hors écartées »
    out0 = patrimoine(siren=siren, limit=200, offset=0, request=None, db=s)
    assert out0["n_actionnables"] == 2 and out0["hors_ecartees_par_vous"] is False
    # ce compte écarte la 2ᵉ parcelle dans un de SES projets
    cid = s.execute(text(
        "INSERT INTO comptes (nom, plan, statut) VALUES ('KO-10', 'integral', 'actif') RETURNING id")).scalar()
    pjid = s.execute(text(
        "INSERT INTO projets (compte_id, nom) VALUES (:c, 'Test KO-10') RETURNING id"), {"c": cid}).scalar()
    s.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut) VALUES (:pj, :p, 'ecartee')"),
        {"pj": pjid, "p": pid2})
    req = types.SimpleNamespace(state=types.SimpleNamespace(compte_id=cid))
    out = patrimoine(siren=siren, limit=200, offset=0, request=req, db=s)
    assert out["n_actionnables"] == 1                     # la 2ᵉ, écartée par ce compte, sort
    assert out["hors_ecartees_par_vous"] is True and out["n_ecartees_par_vous"] == 1
    # un AUTRE compte ne voit pas cette décision (cloison)
    req2 = types.SimpleNamespace(state=types.SimpleNamespace(compte_id=99999))
    out2 = patrimoine(siren=siren, limit=200, offset=0, request=req2, db=s)
    assert out2["n_actionnables"] == 2 and out2["hors_ecartees_par_vous"] is False


def test_patrimoine_ne_leve_pas_et_ménage_vestiges(db_session, monkeypatch):
    # le run v2 servi est épinglé à p_score_v2_runs (vide en test) → on le pointe sur le run seedé.
    monkeypatch.setattr("labuse.api.app._score_v2_run_id", lambda _db: Q_A_RUN_LABEL)
    from labuse.api.modules import patrimoine
    s = "444555666"
    _seed(db_session, "97499000PB0001", _WKT[0], s, "SCI PATCO BETA")
    _seed(db_session, "97499000PB0002", _WKT[1], s, "SCI PATCO BETA")   # contiguë
    out = patrimoine(siren=s, limit=200, offset=0, db=db_session)   # ne lève pas (GB-018 : pagination)
    assert out["siren"] == s and out["n_parcelles"] == 2
    # #2 — l'agrégat dit l'ACTIONNABLE + SDP RÉSIDUELLE (renommé, plus « SDP totale »)
    assert out["n_actionnables"] == 2 and "sdp_residuelle_m2" in out and "sdp_totale_m2" not in out
    # #3 — la clé valorisation existe (None si pas de DVF terrain en base de test — jamais une exception)
    assert "valorisation_nu_eur" in out
    # #4 — signal INPI : aucun dirigeant seedé → société absente du registre
    assert out["inpi_sans_dirigeant"] is True
    # #5 — assiette contiguë détectée dans le portefeuille (2 parcelles mitoyennes)
    assert set(out["assiette_contigue"]) == {"97499000PB0001", "97499000PB0002"}
    # LE MÉNAGE — matrice morte retirée du payload ET des items ; statut (doublon tier_v2) retiré
    for k in ("q_score", "a_score", "completeness_score"):
        assert k not in out
    for it in out["items"]:
        assert "tier_v2" in it and "sdp" in it
        assert "q_score" not in it and "a_score" not in it and "completeness_score" not in it and "statut" not in it


def test_patrimoine_entreprise_sans_foncier_pas_de_signal_inpi(db_session, monkeypatch):
    """OUTILS-FIX-3 B3 — une entreprise ABSENTE du fichier foncier (0 parcelle à La Réunion, ex. le
    pétitionnaire d'un permis basé hors de l'île) ne doit PAS déclencher l'encart « aucun dirigeant
    INPI → succession / sommeil probable » : l'absence de ligne pm_dirigeants y est un angle mort
    (INPI non résolu), pas une preuve. L'endpoint ne lève pas et rend n_parcelles=0, nom=None."""
    monkeypatch.setattr("labuse.api.app._score_v2_run_id", lambda _db: Q_A_RUN_LABEL)
    from labuse.api.modules import patrimoine
    out = patrimoine(siren="392801130", limit=200, offset=0, db=db_session)   # jamais seedée
    assert out["n_parcelles"] == 0 and out["nom"] is None
    assert out["inpi_sans_dirigeant"] is False                                # plus de faux signal


def test_patrimoine_signal_inpi_sur_proprietaire_resolu(db_session, monkeypatch):
    """OUTILS-FIX-3 B3 — le signal RESTE pour une entreprise RÉSOLUE (≥ 1 parcelle + raison sociale)
    sans dirigeant au registre : c'est le vrai « foncier fantôme ». Avec un dirigeant seedé, il tombe."""
    monkeypatch.setattr("labuse.api.app._score_v2_run_id", lambda _db: Q_A_RUN_LABEL)
    from labuse.api.modules import patrimoine
    _seed(db_session, "97499000FZ0001", _WKT[0], "121212121", "SCI FONCIER FANTOME")
    assert patrimoine(siren="121212121", limit=200, offset=0, db=db_session)["inpi_sans_dirigeant"] is True
    db_session.execute(text(
        "INSERT INTO pm_dirigeants (siren, nom) VALUES ('121212121', 'DUPONT')"))
    assert patrimoine(siren="121212121", limit=200, offset=0, db=db_session)["inpi_sans_dirigeant"] is False
