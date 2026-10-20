"""COCKPIT-1 (Lot A) — tests du Tableau de bord.

Le gros est en UNITAIRE PUR (pas de base, pas de réseau — tourne dans la sélection du hook) : la
composition des trois sections par `cockpit_resume.composer_cockpit` (cartes groupées PAR problème,
tuiles, étapes, règle « Envoyer en prod » gated local/prod). Les endpoints (/version,
/admin/cockpit/etat-prod, le bloc `cockpit` de /admin/circuit) sont couverts en `db` (TestClient).
"""
from __future__ import annotations

import pytest

from labuse import cockpit_resume as ck


def _entrees(**over):
    base = dict(
        a_faire={"lignes": [
            {"type": "injecter", "titre": "Injecter Communes IGN", "bouton": {"source": 10}},
            {"type": "injecter", "titre": "Injecter FRR", "bouton": {"source": 11}},
            {"type": "deposer", "titre": "Déposer SPANC", "bouton": {"source": 20}},
            {"type": "decider", "titre": "Décider — sonde en panne : OSM transport",
             "bouton": {"source": 30}},
            {"type": "calculer", "titre": "Calculer le résiduel", "bouton": {"action": "calculer"}},
            {"type": "basculer", "titre": "Basculer sur q_v20", "bouton": {"candidat": "q_v20"}},
        ]},
        etats_sources={"total": 99, "nouvelle version": 2},
        reservoirs=[{"id": 10, "nom": "Communes IGN"}, {"id": 11, "nom": "FRR ex-ZRR"},
                    {"id": 20, "nom": "SPANC"}, {"id": 30, "nom": "OSM transport"}],
        verrous={"casses": ["V1c", "G5"]},
        fuites_rob=[{"id": "couches:x", "nom": "Couches découpées"}],
        # COCKPIT-1b (point 4) — un cache périmé = une carte « Reconstruire ».
        caches_perimes=[{"cache": "commune_contexte_cache", "perime": True,
                         "detail": "23 périmée(s), 0 manquante(s)", "porte_sur": "24 communes",
                         "cle_attendue": "abc", "cle_reelle": "def"}],
        incidents=[],
        ecarts_toleres=48,
        jobs_list=[
            {"nom": "sonde-sources", "gel": None, "dernier": {"statut": "ok", "fin": "2026-10-20T07:00:00+00:00"}},
            {"nom": "ingest-bodacc", "gel": None, "dernier": {"statut": "ok"}},
            {"nom": "coherence-banc", "gel": None, "dernier": {"statut": "ok"}},
            {"nom": "mail-queue-consommer", "gel": None, "dernier": {"statut": "echec"}},
            {"nom": "digest", "gel": "Phase 8", "dernier": None},
            {"nom": "ingest-sitadel", "gel": None, "dernier": None},
        ],
        run_servi="q_v19", candidat=None, calculer_present=True, dernier_calcul="2026-10-18T00:00:00+00:00",
        env="local", prod_run="q_v18",
    )
    base.update(over)
    return base


def test_cartes_groupees_par_probleme_et_triees():
    c = ck.composer_cockpit(**_entrees())
    cartes = {x["id"]: x for x in c["aujourdhui"]["cartes"]}
    # UNE carte par problème (pas par occurrence) : 2 sources en nouvelle version = 1 carte ;
    # un cache périmé = 1 carte « cache:… » (COCKPIT-1b point 4).
    assert set(cartes) == {"injecter", "cache:commune_contexte_cache", "verrous", "sondes", "fuites",
                           "ecarts-toleres", "deposer"}
    # les données à injecter d'abord (tri=0), puis le reste.
    assert c["aujourdhui"]["cartes"][0]["id"] == "injecter"
    assert [x["id"] for x in c["aujourdhui"]["cartes"]] == [
        "injecter", "cache:commune_contexte_cache", "verrous", "sondes", "fuites",
        "ecarts-toleres", "deposer"]
    assert c["aujourdhui"]["n"] == 7


def test_carte_sauvegarde_en_retard():
    """COCKPIT-1b (point 5) — une sauvegarde en retard (incident ops ouvert), qui a quitté le rail du
    Pilotage, apparaît comme une CARTE rouge du Tableau de bord avec « Réessayer » (relance le dump)."""
    inc = [{"cle": "sauvegarde-absente", "sujet": "Aucune sauvegarde présente",
            "detail": "Aucun dump dans /var/backups — la sauvegarde ne tourne plus.",
            "ouvert_at": "2026-10-20T13:50:00+00:00", "rappels": 1}]
    c = ck.composer_cockpit(**_entrees(incidents=inc))
    carte = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "incident:sauvegarde-absente")
    assert carte["pastille"] == "rouge"
    assert carte["titre"] == "La sauvegarde ne tourne plus"
    assert carte["bouton"] == {"label": "Réessayer", "action": "lancer-job", "nom": "backup-postgres"}
    assert "Aucune sauvegarde présente" in carte["detail"]["texte"]
    # une vigie sans incident ne crée AUCUNE carte (pas de bruit).
    assert not any(x["id"].startswith("incident:") for x in ck.composer_cockpit(**_entrees(incidents=[]))["aujourdhui"]["cartes"])


def test_carte_cache_perime_en_francais():
    """COCKPIT-1b (point 4) — un cache périmé = une carte EN FRANÇAIS avec « Reconstruire » ; les
    codes techniques (clé attendue/réelle, run) seulement dans « Voir le détail »."""
    c = ck.composer_cockpit(**_entrees())
    cache = next(x for x in c["aujourdhui"]["cartes"] if x["id"].startswith("cache:"))
    assert cache["pastille"] == "jaune" and cache["code"] is False
    assert cache["titre"] == "23 fiches communes en retard sur les dernières sources"
    assert cache["bouton"]["action"] == "reconstruire"
    assert "abc" in cache["detail"]["texte"]           # clé attendue dans le détail…
    assert "abc" not in cache["titre"]                 # …jamais dans le titre


def test_carte_injecter_bulk():
    c = ck.composer_cockpit(**_entrees())
    inj = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "injecter")
    assert inj["pastille"] == "jaune"
    assert inj["bouton"]["action"] == "injecter"
    assert inj["bouton"]["label"] == "Injecter les 2"
    assert inj["bouton"]["sources"] == [10, 11]
    assert inj["code"] is False


def test_verrous_et_fuites_demandent_du_code_sans_bouton():
    c = ck.composer_cockpit(**_entrees())
    v = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "verrous")
    assert v["pastille"] == "rouge"
    assert v["code"] is True
    assert "bouton" not in v           # demande du code = pas de bouton primaire
    assert v["voir_detail"] is True
    assert "V1c" in v["detail"]["texte"] and "G5" in v["detail"]["texte"]
    f = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "fuites")
    assert f["code"] is True and "bouton" not in f


def test_sondes_reessayer_et_ecarts_accepter():
    c = ck.composer_cockpit(**_entrees())
    s = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "sondes")
    assert s["pastille"] == "rouge" and s["bouton"]["action"] == "reessayer"
    e = next(x for x in c["aujourdhui"]["cartes"] if x["id"] == "ecarts-toleres")
    assert e["pastille"] == "gris" and e["bouton"]["action"] == "accepter-ecarts"
    assert e["bouton"]["label"] == "Accepter les 48"


def test_calculer_basculer_ne_sont_pas_des_cartes():
    """Calculer/Basculer vivent dans « Où en est la mise à jour ? » (section 3), pas en cartes."""
    c = ck.composer_cockpit(**_entrees())
    ids = {x["id"] for x in c["aujourdhui"]["cartes"]}
    assert "calculer" not in ids and "basculer" not in ids


def test_aucun_bouton_decider():
    c = ck.composer_cockpit(**_entrees())
    for carte in c["aujourdhui"]["cartes"]:
        assert "décider" not in (carte.get("bouton", {}).get("label", "") or "").lower()
        assert carte["id"] != "decider"


def test_tuiles_tout_tourne():
    c = ck.composer_cockpit(**_entrees())
    tuiles = {t["id"]: t for t in c["tout_tourne"]["tuiles"]}
    assert set(tuiles) == {"veille", "livraisons", "controle", "courrier"}
    assert tuiles["courrier"]["pastille"] == "rouge"     # mail-queue en échec
    assert tuiles["controle"]["pastille"] == "vert"
    assert tuiles["veille"]["pastille"] == "vert"


def test_resume_usine():
    r = ck.composer_cockpit(**_entrees())["tout_tourne"]["resume"]
    # 6 jobs : 3 ok (sonde/bodacc/coherence) + mail echec + digest gelé + sitadel jamais → 3/1/2.
    assert r == {"postes": 6, "vert": 3, "echec": 1, "arret": 2}


def test_envoyer_prod_local_en_retard_a_un_bouton():
    e = ck.composer_cockpit(**_entrees(env="local", prod_run="q_v18"))["mise_a_jour"]["etapes"]
    env4 = next(x for x in e if x["id"] == "envoyer-prod")
    assert env4["fait"] is False and env4["bouton"]["action"] == "envoyer-prod" and env4["local"] is True


def test_envoyer_prod_a_jour_pas_de_bouton():
    e = ck.composer_cockpit(**_entrees(env="local", prod_run="q_v19"))["mise_a_jour"]["etapes"]
    env4 = next(x for x in e if x["id"] == "envoyer-prod")
    assert env4["fait"] is True and env4["bouton"] is None


def test_envoyer_prod_sur_le_vps_est_inactif():
    e = ck.composer_cockpit(**_entrees(env="production", prod_run="q_v19"))["mise_a_jour"]["etapes"]
    env4 = next(x for x in e if x["id"] == "envoyer-prod")
    assert env4["local"] is False and env4["bouton"] is None and "Mac" in env4["ligne"]


def test_etape_prod_en_cours_de_lecture_quand_run_inconnu():
    e = ck.composer_cockpit(**_entrees(env="local", prod_run=None))["mise_a_jour"]["etapes"]
    env4 = next(x for x in e if x["id"] == "envoyer-prod")
    assert env4["fait"] is False and env4["bouton"] is None


def test_calculer_fait_quand_rien_ne_change():
    e = ck.composer_cockpit(**_entrees(calculer_present=False))["mise_a_jour"]["etapes"]
    calc = next(x for x in e if x["id"] == "calculer")
    assert calc["fait"] is True and calc["bouton"] is None


# ─────────────────── endpoints (db — hors sélection du hook, joués en CI) ───────────────────

@pytest.mark.db
def test_version_endpoint():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/version")
    assert r.status_code == 200
    j = r.json()
    assert "run" in j and "env" in j and "promu_le" in j


@pytest.mark.db
def test_etat_prod_endpoint_local(monkeypatch):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    # prod injoignable (URL morte) → joignable False, ne casse pas.
    monkeypatch.setenv("LABUSE_PROD_URL", "http://127.0.0.1:59999")
    with TestClient(app) as c:
        r = c.get("/admin/cockpit/etat-prod")
    assert r.status_code == 200
    assert r.json()["joignable"] is False


@pytest.mark.db
def test_circuit_contient_cockpit():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/admin/circuit")
    assert r.status_code == 200
    ckd = r.json().get("cockpit")
    assert ckd and set(ckd) == {"aujourdhui", "tout_tourne", "mise_a_jour"}
