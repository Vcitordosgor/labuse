"""CHASSE-FIX-2 — verrous des corrections de CHASSE-2 (docs/audit-2026-10/CHASSE-2/ECARTS.csv).

Un test par écart bloquant, rejoué sur la base de TEST (semis local, nettoyé en fin de test) :
si quelqu'un réintroduit le défaut, le test casse.

  · D05/D06 — TOUT lecteur de filtre résout la cascade du run (q_v16 → étage 0 réutilisé) avant
    de joindre dryrun_parcel_evaluations. Le piège : un run EMPRUNTEUR (sans cascade propre) dont
    la table dryrun ne porte QUE le run de cascade → un lecteur qui lit le run BRUT rend 0 ligne.
  · D03/D04 — une parcelle à cause (terrain_exigu…) NOMME sa raison partout (fiche, liste, PDF,
    Copilote) et ne se contredit plus (bloc Potentiel « Marge SDP non calculée » vs SDP 0).
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(engine):
    from labuse import config
    from labuse.api.app import app

    os.environ.pop("LABUSE_AUTH_PASSWORD", None)
    os.environ["LABUSE_ENV"] = "local"
    config.get_settings.cache_clear()
    return TestClient(app)


IDU = "97415000ZZ9910"
# run EMPRUNTEUR servi (pas de cascade propre) + le run où VIT réellement la cascade (étage 0).
RUN_SERVI = "q_vchfix2_emprunteur"   # DOIT commencer par « q_v » (garde /filtre)
RUN_CASCADE = "q_vchfix2_cascade"
_GEOM = ("SRID=4326;POLYGON((55.271 -21.011, 55.2713 -21.011, 55.2713 -21.0113, "
         "55.271 -21.0113, 55.271 -21.011))")


@pytest.fixture
def emprunteur_seed(engine):
    """Sème le cas « run servi SANS cascade propre » : la table dryrun ne porte le parcel QUE
    sous le run de CASCADE. Un lecteur qui joint le run BRUT (q_v16) ne trouve rien ; un lecteur
    qui résout `_cascade_run` le trouve. `LABUSE_SERVED_RUN` force le run servi, sans cache."""
    from labuse import runs as _runs

    prev_served = os.environ.get("LABUSE_SERVED_RUN")
    os.environ["LABUSE_SERVED_RUN"] = RUN_SERVI
    _runs._cache["val"] = None   # pas de surprise de cache (override non caché de toute façon)
    with engine.begin() as c:
        pid = c.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid) "
            "VALUES (:i, 'Saint-Paul', 'ZZ', '9910', ST_GeomFromEWKT(:g), 900, "
            "        ST_Centroid(ST_GeomFromEWKT(:g))) "
            "ON CONFLICT (idu) DO UPDATE SET commune = EXCLUDED.commune RETURNING id"),
            {"i": IDU, "g": _GEOM}).scalar()
        # le run servi EMPRUNTE son étage 0 au run de cascade (params.etage0_run) : c'est ce que
        # `resoudre_cascade_run` lit pour résoudre q_v16 → q_v13_sources1 en prod.
        for rid, params in ((RUN_SERVI, '{"etage0_run": "%s"}' % RUN_CASCADE), (RUN_CASCADE, "{}")):
            c.execute(text(
                "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, "
                " n_parcelles, computed_at) "
                "VALUES (:r, 'test', 'test', CAST(:p AS jsonb), 1, now()) "
                "ON CONFLICT (run_id) DO UPDATE SET params = CAST(:p AS jsonb)"),
                {"r": rid, "p": params})
        # le score v2 servi est épinglé au run SERVI (compteur/liste le comptent).
        c.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
            " rang, contrib_z, contrib_d, copro, tier, model_version, computed_at) "
            "VALUES (:r, :i, 0.8, 1.0, 0.9, 1, 0.0, 0.0, false, 'brulante', 'test', now())"),
            {"r": RUN_SERVI, "i": IDU})
        # dryrun : UNIQUEMENT sous le run de CASCADE (jamais sous le run servi brut).
        c.execute(text(
            "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
            " opportunity_score, opportunity_base, status, created_at) "
            "VALUES (:rl, :p, 50, 0, 0, 'exclue', now())"),
            {"rl": RUN_CASCADE, "p": pid})
    yield pid
    with engine.begin() as c:
        c.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE parcel_id = :p"), {"p": pid})
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE parcelle_id = :i"), {"i": IDU})
        if c.execute(text("SELECT to_regclass('parcel_renouvellement')")).scalar():
            c.execute(text("DELETE FROM parcel_renouvellement WHERE idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id IN (:a, :b)"),
                  {"a": RUN_SERVI, "b": RUN_CASCADE})
        c.execute(text("DELETE FROM parcels WHERE id = :p"), {"p": pid})
    if prev_served is None:
        os.environ.pop("LABUSE_SERVED_RUN", None)
    else:
        os.environ["LABUSE_SERVED_RUN"] = prev_served
    from labuse import runs as _runs
    _runs._cache["val"] = None


# ───────────────────────── D05 — /filtre?idus=1 résout la cascade (carte = compteur = liste)

def test_d05_filtre_idus_resout_la_cascade(client, emprunteur_seed):
    from labuse.faisabilite.db import parcel_context  # noqa: F401 (assure l'import du moteur)

    r = client.get("/filtre", params={"source": RUN_SERVI, "commune": "Saint-Paul",
                                       "idus": 1, "limit": 20})
    assert r.status_code == 200, r.text
    out = r.json()
    # le parcel servi (score v2 sous le run servi) DOIT être peint sur la carte : s'il manque,
    # c'est qu'un lecteur a joint dryrun sur le run BRUT (q_v16), absent de la table (régression D05).
    assert out.get("idus") is not None, "idus tronqué/None inattendu"
    assert IDU in out["idus"], (
        "D05 régression : /filtre?idus=1 ne résout pas la cascade — la carte reçoit 0 parcelle "
        f"alors que le compteur en voit (idus={out['idus']}, compte={out.get('compte')})")
    # invariant du mandat : compteur = parcelles peintes.
    assert out["compte"] == len(out["idus"]) == 1, out


# ───────────────────────── D06 — Densifier : puce « écartée » (étage 0) lit la cascade

def test_d06_densifier_etage0_resout_la_cascade(client, emprunteur_seed, engine):
    pid = emprunteur_seed
    from labuse.renouvellement import DDL as _RENOUV_DDL
    with engine.begin() as c:
        c.execute(text(_RENOUV_DDL))   # table absente en base de test fraîche (créée par `labuse renouv`)
        c.execute(text(
            "INSERT INTO parcel_renouvellement (idu, renouv_score, comp_potentiel, comp_assiette, "
            " comp_marche, code_bati_origine, surface_m2, commune, rang_segment, rang_commune, "
            " run_label, computed_at) "
            "VALUES (:i, 10, 10, 10, 10, 'deja_bati', 900, '97415', 1, 1, :rl, now()) "
            "ON CONFLICT (idu) DO UPDATE SET run_label = EXCLUDED.run_label"),
            {"i": IDU, "rl": RUN_SERVI})
    r = client.get("/renouvellement/liste", params={"limit": 200})
    assert r.status_code == 200, r.text
    j = r.json()
    items = next((j[k] for k in ("items", "liste", "rows", "page", "resultats")
                  if isinstance(j, dict) and isinstance(j.get(k), list)), j if isinstance(j, list) else [])
    mine = [it for it in items if it.get("idu") == IDU]
    assert mine, f"parcel {IDU} absent de la liste Densifier"
    # dryrun status='exclue' vit sous le run de CASCADE : la puce ne s'allume QUE si la jointure
    # a résolu la cascade (sinon d.status NULL → etage0 toujours false — régression D06).
    assert mine[0].get("etage0") is True, (
        "D06 régression : la puce « écartée » ne lit pas la cascade (etage0 non allumé)")


# ───────────────────────── D04 — la cause est NOMMÉE partout (un seul helper)

def test_d04_cause_libelle_nomme_la_raison():
    from labuse.faisabilite.engine import cause_certaine, cause_libelle

    # terrain exigu : le mot « exigu » / « terrain trop » est TOUJOURS présent (invariant mandat).
    for raison in ("ppr_rouge", "emplacement_reserve", "ebc", "contraintes", "portion_reduite",
                   "reculs", None):
        lib = cause_libelle("terrain_exigu", raison)
        assert lib and ("exigu" in lib.lower() or "terrain trop" in lib.lower()), (raison, lib)
    assert "PPR" in cause_libelle("terrain_exigu", "ppr_rouge")
    # causes à code de zone : la zone est nommée.
    assert "Ub" in cause_libelle("zone_non_constructible:Ub")
    assert cause_libelle("redhibitoire", None).startswith("Non retenue")
    # parcelle calculée → aucun libellé de cause.
    assert cause_libelle(None) is None


def test_d04_familles_certaine_vs_ignorance():
    """Arbitrage Vic — CERTAINE → « Non retenue » (verdict ferme) ; IGNORANCE → « Analyse
    incomplète » (cohérent C26/NC). cause_certaine partitionne les deux."""
    from labuse.faisabilite.engine import cause_certaine, cause_libelle

    for c in ("zone_non_constructible:Ub", "terrain_exigu", "habitat_interdit:Uaza",
              "redhibitoire", "capacite_nulle"):
        assert cause_certaine(c), c
        assert cause_libelle(c).startswith("Non retenue — "), (c, cause_libelle(c))
    for c in ("zone_non_resolue:N", "hors_plu", "regle_plu_non_validee:U5", "hauteur_indispo",
              "indetermine"):
        assert not cause_certaine(c), c
        assert cause_libelle(c).startswith("Analyse incomplète — "), (c, cause_libelle(c))
    assert not cause_certaine(None)


# ───────────────────────── D07 — « retirées 30 j » : UN SEUL lecteur (celui de RADAR-FIX-3)

def test_d07_retirees_un_seul_lecteur():
    """Le compteur 4-chiffres (`_AGG`) doit compter les retirées EXACTEMENT comme le tableau
    (`bouge_30j`) : retraits confirmés, import initial exclu. Sinon 101 (naïf) vs 1 (corrigé)."""
    from labuse.pige import marche

    agg = marche._AGG
    i = agg.lower().index("as retirees_30j")
    bloc = agg[max(0, i - 600):i]   # le FILTER qui alimente retirees_30j
    assert "pige_passes" in bloc and "confirmation" in bloc, (
        "D07 régression : retirees_30j ne partage plus la définition RADAR-FIX-3 (import initial "
        "exclu, retraits confirmés) — risque de 101 vs 1 sur le même écran")
    assert "retiree_le >= now() - interval '30 days'" not in bloc, \
        "D07 régression : retour au comptage naïf de retiree_le (import initial en bloc compté)"


# ───────────────────────── D01 — plan de situation : retry avec backoff sur tuile IGN transitoire

class _FakeResp:
    def __init__(self, status: int, content: bytes = b"PNG"):
        self.status_code = status
        self.content = content

    def raise_for_status(self):
        import httpx
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=self)


class _FlakyClient:
    """Échoue `fails` fois (400 transitoire) puis réussit — comme data.geopf.fr sous rafale."""
    def __init__(self, fails: int, status: int = 400):
        self.fails, self.status, self.calls = fails, status, 0

    def get(self, url):
        self.calls += 1
        if self.calls <= self.fails:
            return _FakeResp(self.status)
        return _FakeResp(200, b"PNG-OK")


def test_d01_fetch_tile_reessaie_un_400_transitoire(tmp_path):
    from labuse.flash import carte

    cl = _FlakyClient(fails=2, status=400)   # 2 × 400 puis OK (le cas réel d'AD0554)
    png = carte._fetch_tile(19, 1, 1, tmp_path, cl, retries=3, backoff_s=0)
    assert png == b"PNG-OK", "D01 régression : un 400 transitoire n'est plus réessayé"
    assert cl.calls == 3


def test_d01_fetch_tile_ne_reessaie_pas_un_404(tmp_path):
    import httpx

    from labuse.flash import carte

    cl = _FlakyClient(fails=9, status=404)   # tuile hors couverture : inutile d'insister
    with pytest.raises(httpx.HTTPStatusError):
        carte._fetch_tile(19, 1, 1, tmp_path, cl, retries=3, backoff_s=0)
    assert cl.calls == 1, "un 404 (tuile absente) ne doit pas être réessayé"


# ───────────────────────── C35 — badge « Propriétaire public » : UNE règle (liste = fiche = filtre)

def test_c35_regle_unique():
    """La détection du propriétaire public est la MÊME partout : la clause SQL du filtre et la liste
    des groupes DGFiP utilisés par la fiche sont construites depuis la MÊME constante."""
    from labuse.proprietaire_type import PUBLIC_DGFIP_GROUPES, PUBLIC_GROUPES_SQL
    assert PUBLIC_DGFIP_GROUPES == (1, 2, 3, 4, 9)
    assert PUBLIC_GROUPES_SQL == "(1,2,3,4,9)"


def test_c35_badge_public_liste_fiche_filtre(client, emprunteur_seed, engine):
    pid = emprunteur_seed
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO parcelle_personne_morale (idu, groupe, groupe_label, denomination) "
            "VALUES (:i, 4, 'Commune', 'COMMUNE DE SAINT-PAUL') "
            "ON CONFLICT (idu) DO UPDATE SET groupe = 4, groupe_label = 'Commune'"),
            {"i": IDU})
        # reste AU CLASSEMENT : on retire l'étage 0 posé par le seed D06 (status 'exclue') pour que
        # la parcelle apparaisse dans le périmètre de liste par défaut — le badge public ne doit pas
        # dépendre de l'exclusion (un public « retenu » le porte aussi).
        c.execute(text("UPDATE dryrun_parcel_evaluations SET status = 'ok' WHERE parcel_id = :p"),
                  {"p": pid})
    try:
        # fiche : le badge public est servi (même règle DGFiP groupe 4 = commune).
        fi = client.get(f"/parcels/{IDU}").json()
        pm = fi.get("proprietaire_moral") or {}
        assert pm.get("proprietaire_public") is True, pm
        # liste : la parcelle RESTE au classement AVEC le drapeau public (jamais écartée d'office).
        out = client.get("/filtre", params={"source": RUN_SERVI, "commune": "Saint-Paul",
                                             "limit": 20}).json()
        mine = [it for it in out.get("page", []) if it.get("idu") == IDU]
        assert mine and mine[0].get("proprietaire_public") is True, out.get("page")
        # filtre d'exclusion : proprietaire_type=public la retrouve bien (même clause SQL).
        pub = client.get("/filtre", params={"source": RUN_SERVI, "commune": "Saint-Paul",
                                            "proprietaire_type": "public", "idus": 1, "limit": 20}).json()
        assert IDU in (pub.get("idus") or []), "le filtre public et le badge doivent voir la MÊME parcelle"
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": IDU})
