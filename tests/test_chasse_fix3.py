"""CHASSE-FIX-3 — verrous des corrections de CHASSE-3 (docs/audit-2026-10/CHASSE-3/ECARTS.csv).

Un test par écart corrigé, rejoué sur la base de TEST (semis local, nettoyé en fin de test) :
si quelqu'un réintroduit le défaut, le test casse.

  · C3-01 — /readyz (served_run_status) teste le run de CASCADE RÉSOLU (q_v16 → étage 0 réutilisé),
    pas le label de scoring brut : sinon la sonde dit « non matérialisé » alors que l'app sert juste.
  · C3-04/C3-05 — TOUTE cause d'ignorance de faisabilite.engine (hauteur_indispo, indetermine,
    bati_non_ingere…) tombe en NC « Analyse incomplète » au Score, jamais en bande « 0 », même quand
    le résiduel a stocké SDP=0. Une cause CERTAINE (terrain_exigu…) garde son vrai 0.
  · C3-06/C3-07 — chaque table dérivée porte la version de sa règle ; le contrôle de fraîcheur signale
    « à reconstruire » quand le code a bougé sans rebuild (le bug fondateur des tables du 08/08 et 09/08).
  · C3-08 — un LIMIT 1 qui choisit parmi plusieurs établissements d'une PM est DÉTERMINISTE (départage
    explicite par SIRET) : la fiche ne flappe plus d'un appel à l'autre.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text


# ───────────────────────── C3-04 / C3-05 — _cause_nc couvre toutes les ignorances (pur) ──────────

def _entree(cause, *, sdp=0.0):
    from labuse.scoring.score_labuse import ScoreEntrees
    # SDP=0.0 = le STOCK POLLUÉ de C3-04 (ignorance stockée 0 au lieu de ∅) : le filet doit quand
    # même basculer en NC. aire/périmètre valides pour passer la garde géométrie.
    return ScoreEntrees(parcel_id=1, idu="97400000ZZ0001", commune="c", residuel_present=True,
                        sdp_residuelle_m2=sdp, taux_emprise_pct=None, cause=cause,
                        capacite_estimee=None, pente_moy_deg=None, aire_m2=1000.0,
                        perimetre_m=130.0, faitage_m=None, au_classe=None, acces=None)


def test_c3_05_hauteur_indispo_et_ignorances_sont_nc():
    from labuse.scoring.score_labuse import _cause_nc, NC_HAUTEUR

    # hauteur_indispo : motif propre (= celui de la fiche), jamais None → jamais bande 0.
    assert _cause_nc(_entree("hauteur_indispo")) == NC_HAUTEUR
    # TOUTE autre cause d'ignorance de faisabilite.engine tombe en NC (filet cause-indépendant).
    for c in ("indetermine", "bati_non_ingere", "zone_non_resolue:N", "hors_plu",
              "regle_plu_non_validee:U5"):
        assert _cause_nc(_entree(c)) is not None, f"ignorance {c} classée bande 0 (régression C3-04/05)"


def test_c3_05_causes_certaines_gardent_leur_vrai_zero():
    from labuse.scoring.score_labuse import _cause_nc

    # un vrai 0 (verdict ferme) n'est JAMAIS NC — invariant C26.
    for c in ("terrain_exigu", "capacite_nulle", "zone_non_constructible:Ub",
              "habitat_interdit:Uaza", "redhibitoire"):
        assert _cause_nc(_entree(c)) is None, f"cause certaine {c} à tort en NC"
    # parcelle calculée (aucune cause) avec une SDP réelle → calculable.
    assert _cause_nc(_entree(None, sdp=320.0)) is None


def test_c3_05_bande_nc_vs_zero():
    from labuse.scoring.score_labuse import bande_de_score, charger_bareme
    bareme, _ = charger_bareme()
    assert bande_de_score(None, bareme) == "NC"      # non calculable
    assert bande_de_score(0, bareme) != "NC"         # vrai 0 = bande « 0 », jamais NC


def test_c3_05_partition_alignee_sur_engine():
    """Le filet de _cause_nc délègue la partition à faisabilite.engine.cause_certaine (source
    unique) : toute cause NON certaine DOIT devenir NC — aucune ne doit fuir en bande 0."""
    from labuse.faisabilite.engine import cause_certaine
    from labuse.scoring.score_labuse import _cause_nc
    for c in ("hauteur_indispo", "indetermine", "bati_non_ingere", "zone_non_resolue:N",
              "hors_plu", "regle_plu_non_validee:U5"):
        assert not cause_certaine(c)                 # c'est bien une ignorance
        assert _cause_nc(_entree(c)) is not None, c  # … et le Score la met en NC


# ───────────────────────── C3-06 / C3-07 — version de règle des tables dérivées ──────────────────

def test_c3_06_07_derives_signalent_a_reconstruire(engine):
    """Chaque table dérivée porte la version de sa règle ; le contrôle de fraîcheur signale
    « à reconstruire » dès que la version gravée diffère du code (le bug CHASSE-3)."""
    from labuse import fraicheur_caches as fc
    from labuse.db import session_scope
    from labuse.ingestion.fraicheur import _ensure, _etat_set

    with session_scope() as s:
        _ensure(s)      # pose fraicheur_etat (base de test nue)
        s.execute(text("DELETE FROM fraicheur_etat WHERE cle LIKE 'derive:%'"))
        s.commit()
        # jamais gravée → périmé « à reconstruire ».
        assert fc._etat_derives_regle(s)["perime"] is True
        # on grave les versions courantes → frais.
        fc.marquer_regle_derivee(s, "pc_caducs")
        fc.marquer_regle_derivee(s, "parcel_veille_succession")
        s.commit()
        e = fc._etat_derives_regle(s)
        assert e["perime"] is False, e["detail"]
        # une règle du CODE qui bouge sans rebuild (version gravée ancienne) → re-périmé.
        _etat_set(s, "derive:pc_caducs:rule_version", "regle-du-08-08-avant-oracle-fix-1")
        s.commit()
        etat = fc._etat_derives_regle(s)
        assert etat["perime"] is True
        assert "pc_caducs" in etat["detail"]


def test_c3_06_07_versions_de_regle_non_vides():
    """Les deux versions de règle existent et bougent avec leurs paramètres (dérivées, pas figées)."""
    from labuse.ingestion.pc_caducs import RULE_VERSION as PC
    from labuse.scoring.score_v_constants import (VEILLE_SUCCESSION_FORMES,
                                                  VEILLE_SUCCESSION_RULE_VERSION as VS)
    assert PC and "2,5,6" in PC                       # états octroyés doctrinaux (ORACLE-FIX-1)
    assert VS and "age70" in VS
    # la version succession dérive des formes : toutes les formes retenues y figurent.
    for forme in VEILLE_SUCCESSION_FORMES:
        assert forme in VS


# ───────────────────────── C3-08 — départage déterministe d'un LIMIT 1 ───────────────────────────

@pytest.fixture
def sirene_exaequo(engine):
    """Sème 3 établissements d'une même PM, ex æquo sur (actif, date_creation) — EDF-like : sans
    départage par SIRET, le LIMIT 1 flappe."""
    siren = "552081317"
    with engine.begin() as c:
        c.execute(text("DELETE FROM sirene_etablissements WHERE siren = :s"), {"s": siren})
        for siret, adr in ((f"{siren}00011", "11 ex aequo"),
                            (f"{siren}00022", "22 ex aequo"),
                            (f"{siren}00033", "33 ex aequo")):
            c.execute(text(
                "INSERT INTO sirene_etablissements (siret, siren, naf, adresse, commune, actif, "
                " diffusible, date_creation) VALUES (:t, :s, '6820A', :a, 'Saint-Denis', true, true, "
                " DATE '1986-07-08')"), {"t": siret, "s": siren, "a": adr})
    yield siren
    with engine.begin() as c:
        c.execute(text("DELETE FROM sirene_etablissements WHERE siren = :s"), {"s": siren})


def test_c3_08_pm_identite_deterministe(sirene_exaequo):
    from labuse.api.app import _pm_identite
    from labuse.db import session_scope

    vus = set()
    for _ in range(4):
        with session_scope() as s:
            r = _pm_identite(s, sirene_exaequo)
            assert r is not None
            vus.add(r["siege"])
    assert len(vus) == 1, f"fiche non déterministe : {vus}"
    # départage par SIRET croissant → le plus petit SIRET (…00011) gagne.
    assert vus == {"11 ex aequo"}


# ───────────────────────── C3-01 — /readyz lit le run de CASCADE résolu ──────────────────────────

RUN_SERVI = "q_vchfix3_emprunteur"      # DOIT commencer par « q_v »
RUN_CASCADE = "q_vchfix3_cascade"
_GEOM = ("SRID=4326;POLYGON((55.281 -21.021, 55.2813 -21.021, 55.2813 -21.0213, "
         "55.281 -21.0213, 55.281 -21.021))")


@pytest.fixture
def emprunteur_readyz(engine):
    """Run servi SANS cascade propre : dryrun ne porte le parcel QUE sous le run de CASCADE.
    served_run_status doit résoudre la cascade (comme les lecteurs), pas lire le label brut."""
    prev = os.environ.get("LABUSE_SERVED_RUN")
    os.environ["LABUSE_SERVED_RUN"] = RUN_SERVI
    from labuse import runs as _runs
    _runs._cache["val"] = None
    with engine.begin() as c:
        pid = c.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid) "
            "VALUES ('97415000ZZ9930','Saint-Paul','ZZ','9930', ST_GeomFromEWKT(:g), 900, "
            "        ST_Centroid(ST_GeomFromEWKT(:g))) "
            "ON CONFLICT (idu) DO UPDATE SET commune = EXCLUDED.commune RETURNING id"),
            {"g": _GEOM}).scalar()
        for rid, params in ((RUN_SERVI, '{"etage0_run": "%s"}' % RUN_CASCADE), (RUN_CASCADE, "{}")):
            c.execute(text(
                "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, "
                " n_parcelles, computed_at) VALUES (:r,'test','test',CAST(:p AS jsonb),1,now()) "
                "ON CONFLICT (run_id) DO UPDATE SET params = CAST(:p AS jsonb)"),
                {"r": rid, "p": params})
        c.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
            " rang, contrib_z, contrib_d, copro, tier, model_version, computed_at) "
            "VALUES (:r,'97415000ZZ9930',0.8,1.0,0.9,1,0.0,0.0,false,'brulante','test',now())"),
            {"r": RUN_SERVI})
        # dryrun : UNIQUEMENT sous le run de CASCADE (jamais sous le run servi brut).
        c.execute(text(
            "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
            " opportunity_score, opportunity_base, status, created_at) "
            "VALUES (:rl,:p,50,0,0,'exclue',now())"), {"rl": RUN_CASCADE, "p": pid})
    yield pid
    with engine.begin() as c:
        c.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE parcel_id = :p"), {"p": pid})
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE parcelle_id = '97415000ZZ9930'"))
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id IN (:a,:b)"),
                  {"a": RUN_SERVI, "b": RUN_CASCADE})
        c.execute(text("DELETE FROM parcels WHERE id = :p"), {"p": pid})
    if prev is None:
        os.environ.pop("LABUSE_SERVED_RUN", None)
    else:
        os.environ["LABUSE_SERVED_RUN"] = prev
    _runs._cache["val"] = None


def test_c3_01_readyz_resout_la_cascade(emprunteur_readyz):
    from labuse import state
    from labuse.db import session_scope

    with session_scope() as s:
        served = state.served_run_status(s)
    # le run servi est matérialisé (score v2 présent + cascade EMPRUNTÉE résolue) → ok=True.
    assert served["run"] == RUN_SERVI
    assert served["ok"] is True, (
        "C3-01 régression : la sonde lit le label de scoring BRUT (dryrun vide) et dit « non "
        f"matérialisé » alors que la cascade est résolue — missing={served['missing']}")
