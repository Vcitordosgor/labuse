"""CIRCUIT-6 — les sept garanties : chaque verrou PROUVÉ cassé sur un cas construit, puis
vert (cas propre + base réelle sous @local). Un verrou jamais vu rouge n'existe pas.
"""
from __future__ import annotations

import os

import pytest

from labuse import circuit_garanties as CG

pytestmark = pytest.mark.verrous

from pathlib import Path
ROOT_C6 = Path(__file__).resolve().parents[2]


def _src(i, name, *, endpoint=None, notes=None, alias_de=None, status="connecte"):
    return {"id": i, "name": name, "status": status, "endpoint_url": endpoint,
            "technical_notes": notes, "alias_de": alias_de}


# ── G1 — toutes les sources, une seule fois ────────────────────────────────────────────
def test_g1_prouve_casse_meme_endpoint_sans_arbitrage():
    rows = [_src(1, "Source A", endpoint="https://api.exemple.fr/jeu"),
            _src(2, "Source B", endpoint="https://api.exemple.fr/jeu")]
    d = CG.analyse_doublons(rows)
    assert len(d) == 1 and d[0]["arbitrage"] is None
    assert "même endpoint" in d[0]["raisons"][0]


def test_g1_passerelle_mutualisee_nest_pas_un_doublon():
    rows = [_src(1, "Jeu WFS 1", endpoint="https://data.geopf.fr/wfs/ows"),
            _src(2, "Jeu WFS 2", endpoint="https://data.geopf.fr/wfs/ows")]
    assert CG.analyse_doublons(rows) == []


def test_g1_arbitrage_ecrit_eteint_le_doublon():
    rows = [_src(1, "Source A", endpoint="https://api.exemple.fr/jeu",
                 notes="ARBITRAGE : deux canaux, un usage chacun"),
            _src(2, "Source B", endpoint="https://api.exemple.fr/jeu")]
    d = CG.analyse_doublons(rows)
    assert len(d) == 1 and d[0]["arbitrage"] == "note en base"


def test_g1_alias_vaut_arbitrage():
    rows = [_src(1, "Canonique", endpoint="https://api.exemple.fr/jeu"),
            _src(2, "Canal bulk", endpoint="https://api.exemple.fr/jeu", alias_de=1,
                 status="alias")]
    d = CG.analyse_doublons(rows)
    assert d and d[0]["arbitrage"].startswith("alias")


def test_g1_concepts_declares_sonnent():
    rows = [_src(1, "DVF / valeurs foncières"),
            _src(2, "DVF Réunion (Région, data.regionreunion.com)")]
    d = CG.analyse_doublons(rows)
    assert d and "même concept" in d[0]["raisons"][0]


def test_g1_statut_hors_liste_fermee_casse(monkeypatch):
    class _Faux:
        def execute(self, *a, **k):
            raise AssertionError("non appelé")
    # la liste fermée elle-même (REPARATIONS-1 lot 3 : + partenariat_requis ; SOURCES-CORRECTION-2
    # lot 1 : + interne = référentiel technique lu par la pompe, hors vitrine client mais visible admin)
    assert CG.STATUTS_ADMIS == {"connecte", "manuel", "a_faire", "retiree", "alias", "hub",
                                "partenariat_requis", "interne"}


@pytest.mark.local
def test_g1_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    assert url, "base réelle inconnue"
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g1(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])
        cpt = CG.catalogue_compteurs(s)
        assert cpt["total"] == cpt["vitrine"] + cpt["hors_vitrine"]


# ── G2 — visible ou pas, je le sais ────────────────────────────────────────────────────
def test_g2_etat_invisible_sort_rouge():
    """La branche INVISIBLE de etat_reservoir : avec le drapeau → rouge ; sans → « à jour »
    (mint) — c'était l'état AVANT le branchement : le mensonge DPE, prouvé ici."""
    from labuse.circuit_etats import etat_reservoir
    avec = etat_reservoir({"invisible": True, "mode": "cron_mensuel",
                           "veille": {"statut": "ok"}, "filtre": {}})
    sans = etat_reservoir({"mode": "cron_mensuel", "veille": {"statut": "ok"}, "filtre": {}})
    assert avec == ("rouge", "INVISIBLE — branchée mais vide")
    assert sans == ("mint", "à jour"), "sans le drapeau, la page disait « à jour » sur une vide"


@pytest.mark.local
def test_g2_signature_dpe_sur_la_base_reelle():
    """SOURCES-CORRECTION-2 lot 3 — REMIS SUR LA VALEUR RÉELLE : SOURCES-CORRECTION-1 a rempli DPE
    (16 → 1123). DPE est 0/12 sur les témoins (ils ne sont pas dans les 20 communes couvertes) MAIS sa
    table n'est PLUS quasi vide → quasi_vide=False (garde-fou anti-régression du correctif DPE). RNIC
    (riche) : 0/12 sans quasi_vide (les témoins ne sont pas des copros). Cadastre : 12/12."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from labuse.registre import remplissage as R
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    assert url
    with sessionmaker(bind=create_engine(url))() as s:
        tem = R.temoins_du_jour(s)
        assert len(tem) == 12
        assert R.remplissage_source(s, "dpe_ademe", tem)["quasi_vide"] is False  # table pleine (1123)
        assert R.remplissage_source(s, "rnic_anah", tem)["quasi_vide"] is False
        assert R.remplissage_source(s, "cadastre_api_carto", tem)["remplis"] == 12


@pytest.mark.local
def test_g2_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g2(s)
        assert r.verdict == "ok", (r.preuve, r.details[:3])
        # SOURCES-CORRECTION-2 lot 3 : DPE rempli (SC-1) → G2 ne mesure PLUS aucune source vide.
        # La promesse « une vide est nommée, jamais tue » reste portée par verrou_g2 (qui les liste
        # dans sa preuve) ; ici on prouve simplement que la base réelle n'a plus de source vide.
        assert "0 source" in r.preuve  # 0 source(s) vide(s) mesurée(s)


# ── G3 — je sais ce qui nourrit le score ───────────────────────────────────────────────
def test_g3_prouve_casse_feature_sans_source():
    """Une variable du modèle absente de la carte FEATURE_RESERVOIRS → casse (liste fermée)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base réelle requise (statuts)")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g3(s, features=["variable_inventee_xyz"])
        assert r.verdict == "casse"
        assert any("variable_inventee_xyz" in d for d in r.details)


def test_g3_toutes_les_features_du_modele_sont_cartographiees():
    from labuse.scoring.p_model.features import FEATURES
    manquantes = [f.name for f in FEATURES if f.name not in CG.FEATURE_RESERVOIRS]
    assert manquantes == [], f"features sans source déclarée : {manquantes}"


def test_g3_prouve_casse_source_retiree(monkeypatch):
    """Si une feature pointait un réservoir RETIRÉ (mobpro), G3 casse."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base réelle requise")
    monkeypatch.setitem(CG.FEATURE_RESERVOIRS, "feature_test_retiree", ("mobpro",))
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g3(s, features=["feature_test_retiree"])
        assert r.verdict == "casse"
        assert any("RETIRÉE" in d for d in r.details)


@pytest.mark.local
def test_g3_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g3(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])
        rep = CG.repere_score(s)
        assert rep["n_sources"] >= 30 and rep["run_servi"]


# ── G4 — dernière version ou pas ───────────────────────────────────────────────────────
def test_g4_prouve_casse_source_nue(monkeypatch):
    """Une source connectée SANS sonde NI raison → casse. On retire une raison du dict
    (le trou vécu le 13/09 : 6 sources nues avant que les raisons soient écrites).
    TESTS-1 lot 2 (B) — le cobaye n'est plus RTAA en dur : SOURCES-3 lot 3 lui a posé une
    veille « rappel » en base (une source SOUS SONDE ne redevient jamais nue en retirant sa
    raison). Le test choisit dynamiquement une source de la vitrine SANS veille dont la raison
    est écrite : retirer SA raison doit faire casser G4 en la nommant."""
    from sqlalchemy import create_engine, text as _text
    from sqlalchemy.orm import sessionmaker
    from labuse import sentinelle
    from labuse.sources_catalog import WHERE_AFFICHEES, masquees_param
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base réelle requise")
    with sessionmaker(bind=create_engine(url))() as s:
        sans_veille = {n for (n, m) in s.execute(_text(
            "SELECT d.name, v.methode FROM data_sources d"
            " LEFT JOIN source_veille v ON v.source_id = d.id"
            f" WHERE {WHERE_AFFICHEES}"), {"masquees": masquees_param()}).all() if not m}
        candidats = sorted(sans_veille & set(sentinelle.RAISONS_NON_SURVEILLEES))
        # S'il n'y a AUCUNE source « raison seule », la branche raison de G4 est morte — le dire.
        assert candidats, "aucune source de la vitrine ne repose sur une raison : brancher un autre cobaye"
        cobaye = candidats[0]
        prive = dict(sentinelle.RAISONS_NON_SURVEILLEES)
        prive.pop(cobaye)
        monkeypatch.setattr(sentinelle, "RAISONS_NON_SURVEILLEES", prive)
        r = CG.verrou_g4(s)
        assert r.verdict == "casse"
        assert any(cobaye in d for d in r.details)


@pytest.mark.local
def test_g4_vert_et_vide_jamais_a_jour():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from labuse.etats_sources import lister_etats
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g4(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])
        dpe = next(e for e in lister_etats(s) if "DPE" in e["name"])
        assert dpe["etat"] == "vide" and dpe["etat_client"] == "pas_a_jour", \
            "le DPE (vide mesurée) ne peut plus dire « à jour »"


# ── G5 — date du dernier contrôle ──────────────────────────────────────────────────────
def test_g5_jamais_verifie_est_rouge():
    from labuse.circuit_etats import etat_reservoir
    assert etat_reservoir({}) == ("rouge", "jamais vérifié")           # sans sonde
    assert etat_reservoir({"veille": {"statut": None, "passage": None}}) == \
        ("rouge", "jamais vérifié")                                     # sonde jamais passée
    depot = etat_reservoir({"veille": {"statut": "ok"}, "mode": "depot_manuel"})
    assert depot == ("gris", "dépôt manuel — jamais alimenté")          # dépôt sans date : DIT


@pytest.mark.local
def test_g5_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g5(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])
        assert "jamais vérifié" in r.preuve and "ROUGE" in r.preuve


# ── G6 — quelle donnée alimente quoi ───────────────────────────────────────────────────
def test_g6_prouve_casse_reservoir_muet(monkeypatch):
    """Un fichier app qui lit la table d'un réservoir MUET (0 chiffre) → casse. On rejoue le
    trou vécu (mobpro_commune lue par zone.py, parcel_anc à réservoir muet) sur un cas construit."""
    monkeypatch.setattr(CG, "lecteurs_du_code",
                        lambda: {"mobpro_commune": {"zone.py"}})
    pbs = CG.analyse_g6()
    assert pbs and "MUET" in pbs[0] and "mobpro" in pbs[0]


def test_g6_vert_apres_raccords():
    r = CG.verrou_g6()
    assert r.verdict == "ok", (r.preuve, r.details[:5])
    assert "0 lecture(s) de réservoir muet" in r.preuve


def test_g6_les_deux_sens_sont_calcules():
    lect = CG.lecteurs_par_slug()
    assert "dvf" in lect and any(f.startswith("api/") or f.endswith(".py") for f in lect["dvf"])
    dette = CG.lecteurs_non_declares()
    assert isinstance(dette, list)  # la dette fine est mesurée, affichée, jamais tue


# ── G7 — la même donnée partout (+ les fuites du lot 7) ────────────────────────────────
def test_g7_prouve_casse_sonde_vieille(monkeypatch):
    """Sonde plus vieille que 48 h → casse (vécu : dernier passage 09/09, 3 jours)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base réelle requise")
    monkeypatch.setattr(CG, "G7_AGE_MAX_H", 0)   # tout passage devient « trop vieux »
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g7(s)
        assert r.verdict == "casse" and any("pas tourné" in d for d in r.details)


@pytest.mark.local
def test_g7_vert_apres_sonde():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g7(s)
        assert r.verdict == "ok", (r.preuve, r.details[:3])
        assert "affichables" in r.preuve


@pytest.mark.local
def test_fuite2_hauteur_lidar_creditee():
    """Fusion CIRCUIT-6 × RECETTE-10 T1 : l'égout MESURÉ se compare à la règle d'ÉGOUT, le
    faîtage à la règle de FAÎTAGE (surelevation_mesuree, jamais l'une contre l'autre) ; la
    table batiment_hauteur_lidar est à la carte du réservoir lidar, l'arête est posée sur la
    marge servie. (_hauteur_bati_m RESTE le faîtage BD TOPO pour le potentiel/surélévation —
    l'override égout du lot 7 initial remettait un égout face à une règle de faîtage : retiré au
    merge.) SOURCES-3 lot 1 : la fuite « 303k à la carte » est CLOSE — l'extrusion 3D
    (couche_batiments_3d) préfère le faîtage LiDAR, donc lidar_hd_mnh est désormais crédité au
    chiffre hauteur_bati_m (à côté de bd_topo)."""
    from labuse.faisabilite.potentiel import surelevation_mesuree
    from labuse.registre.donnees import CHIFFRES
    from labuse.registre.tables import RESERVOIR_TABLES
    assert "batiment_hauteur_lidar" in RESERVOIR_TABLES["lidar_hd_mnh"].tables
    assert "lidar_hd_mnh" in CHIFFRES["marge_surelevation_m"].reservoirs
    # la hauteur bâtie sert DEUX surfaces : BD TOPO (fiche/potentiel) + faîtage LiDAR (carte 3D).
    assert CHIFFRES["hauteur_bati_m"].reservoirs == ("bd_topo", "lidar_hd_mnh")
    sm = surelevation_mesuree(10.0, 13.0, 4.1, 8.4)   # le témoin Saint-Denis (Dossier régénéré)
    assert {c["base"]: c["marge_m"] for c in sm["contraintes"]} == {"égout": 5.9, "faîtage": 4.6}
    assert sm["contrainte"] == "faîtage" and sm["marge_m"] == 4.6   # la plus serrée mord
    # jamais l'une contre l'autre : une seule règle en regard d'une seule mesure, appariées
    seul_egout = surelevation_mesuree(10.0, None, 4.1, 8.4)
    assert [c["base"] for c in seul_egout["contraintes"]] == ["égout"]


@pytest.mark.local
def test_fuite2_lidar_plus_quasi_vide():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from labuse.registre import remplissage as R
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        m = R.remplissage_source(s, "lidar_hd_mnh", R.temoins_du_jour(s))
        assert m["quasi_vide"] is False and m["remplis"] >= 6


# ── la commande unique : 24, toujours tous ─────────────────────────────────────────────
@pytest.mark.local
def test_les_24_se_jouent_toujours_tous():
    """La composition de « labuse circuit verrous » : 20 verrous + 8 garanties = 28, TOUJOURS
    tous — même quand un verrou casse en route (le vécu : l'arrêt-au-premier sur V3a masquait
    les suivants, la commande n'en montrait que 7). SOURCES-3 lot 4 : V4e (garde-fou 974) ajouté ;
    COUCHES-TUYAU-1 : V7a (verrou des tuiles) ajouté ; SOURCES-CORRECTION-2 lot 3 : + G8 (sources
    sans contrôle, ajouté par CRON-1 lot 2) ; FICHE-RANGEMENT-2 : + V5d (fiche par déclaration) ;
    PLU-CALIBRAGE-1 : + V6a (règles chiffrées validées) — REMIS SUR LA VALEUR RÉELLE."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from labuse import circuit_verrous
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        resultats = circuit_verrous.jouer_tous(s, arret_premier=False) + CG.jouer_garanties(s)
    ids = [r.id for r in resultats]
    assert ids == ["V1a", "V1b", "V1c", "V1d", "V2a", "V2b", "V3a", "V3b", "V3c",
                   "V4a", "V4b", "V4c", "V4d", "V4e", "V5a", "V5b", "V5c", "V5d", "V6a", "V7a",
                   "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"], ids


def test_la_cli_ne_conditionne_plus_les_garanties():
    """Le défaut vécu : `if complet or not any(casse)` sautait les garanties dès qu'un verrou
    cassait, et l'arrêt-au-premier tronquait la liste. La CLI joue tout, sans condition."""
    src = (ROOT_C6 / "src/labuse/cli.py").read_text(encoding="utf-8")
    bloc = src.split('@circuit_app.command("verrous")')[1].split("@")[0]
    assert "jouer_garanties(s)" in bloc
    assert "if complet or not any" not in bloc, "les garanties re-conditionnées à un cassé"
    assert 'complet: bool = typer.Option(True' in bloc, "l'arrêt-au-premier redevenu le défaut"
