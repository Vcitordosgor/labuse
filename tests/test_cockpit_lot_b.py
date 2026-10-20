"""COCKPIT-1 (Lot B) — tests de « L'usine ».

Unitaire pur sur `cockpit_resume.composer_usine` (4 familles, gelés extraits, pastilles, boutons) +
le méta-contrôle du registre (famille/libellé/rôle de CHAQUE job). Endpoints (/admin/usine,
/admin/jobs/<nom>/lancer) en `db` (TestClient).
"""
from __future__ import annotations

import pytest

from labuse import cockpit_resume as ck


def _jobs():
    return [
        {"nom": "sonde-sources", "famille": 1, "libelle": "Le veilleur de nuit", "role": "…",
         "cadence": "quotidien", "heure_reunion": "07:00", "gel": None, "lancable": True,
         "dernier": {"statut": "ok", "fin": "2026-10-20T07:00:00+00:00", "duree_s": 12.0},
         "prochaine_reunion": "21/10 07:00"},
        {"nom": "agents-sources", "famille": 1, "libelle": "Les enquêteurs IA", "role": "…",
         "cadence": "15 j", "heure_reunion": "23:00 dim", "gel": None, "lancable": False,
         "dernier": {"statut": None}, "prochaine_reunion": None},
        {"nom": "ingest-bodacc", "famille": 2, "libelle": "Livreur BODACC", "role": "…",
         "gel": None, "lancable": True, "dernier": {"statut": "echec", "erreur": "boom",
         "fin": "2026-10-20T06:40:00+00:00"}, "prochaine_reunion": "21/10 06:40"},
        {"nom": "fiche-commune-cache", "famille": 3, "libelle": "Le précalcul", "role": "…",
         "gel": None, "lancable": True, "dernier": {"statut": "en_cours"}, "prochaine_reunion": "21/10 03:00"},
        {"nom": "digest", "famille": 4, "libelle": "Le digest du matin", "role": "…",
         "gel": "Phase 8", "lancable": False, "dernier": {"statut": None}, "prochaine_reunion": None},
        {"nom": "coherence-banc", "famille": 4, "libelle": "Le contrôleur de nuit", "role": "…",
         "gel": None, "lancable": True, "dernier": {"statut": "ok"}, "prochaine_reunion": "21/10 03:45"},
    ]


def test_quatre_familles_dans_le_bon_ordre():
    u = ck.composer_usine(_jobs())
    assert [f["n"] for f in u["familles"]] == [1, 2, 3, 4]
    assert [f["nom"] for f in u["familles"]] == [
        "Veille des sources", "Livraisons quotidiennes", "Le moteur", "Contrôle, clients, sécurité"]


def test_geles_sortent_des_colonnes():
    u = ck.composer_usine(_jobs())
    f4 = next(f for f in u["familles"] if f["n"] == 4)
    assert [p["nom"] for p in f4["postes"]] == ["coherence-banc"]   # digest gelé est HORS colonne
    assert [p["libelle"] for p in u["geles"]] == ["Le digest du matin"]


def test_pastilles():
    u = ck.composer_usine(_jobs())
    par = {p["nom"]: p for f in u["familles"] for p in f["postes"]}
    par.update({p["nom"]: p for p in u["geles"]})
    assert par["sonde-sources"]["pastille"] == "vert"
    assert par["ingest-bodacc"]["pastille"] == "rouge"
    assert par["fiche-commune-cache"]["pastille"] == "violet"   # en_cours
    assert par["agents-sources"]["pastille"] == "gris"          # jamais parti
    assert par["digest"]["pastille"] == "gris"                  # gelé


def test_pastille_en_cours_via_verrou():
    u = ck.composer_usine(_jobs(), en_cours={"coherence-banc"})
    cb = next(p for f in u["familles"] for p in f["postes"] if p["nom"] == "coherence-banc")
    assert cb["pastille"] == "violet"


def test_boutons():
    u = ck.composer_usine(_jobs())
    par = {p["nom"]: p for f in u["familles"] for p in f["postes"]}
    par.update({p["nom"]: p for p in u["geles"]})
    assert par["sonde-sources"]["bouton"]["action"] == "lancer"           # lançable
    assert par["agents-sources"]["bouton"]["action"] == "agents"          # IA → Démarrer
    assert par["digest"]["bouton"]["action"] == "reveiller"               # gelé → Réveiller
    assert par["ingest-bodacc"]["voir_detail"] is True                    # échec → Voir le détail
    assert "boom" in par["ingest-bodacc"]["detail"]["texte"]


def test_resume():
    assert ck.composer_usine(_jobs())["resume"] == {"postes": 6, "vert": 2, "echec": 1, "arret": 3}


# ─────────────── le registre réel (import) ───────────────

def test_registre_habille_les_31_jobs():
    from labuse import jobs
    # l'assertion de couverture tourne à l'import ; on vérifie en plus que liste() porte l'habillage.
    for j in jobs.liste():
        assert j["famille"] in (1, 2, 3, 4), j["nom"]
        assert j["libelle"] and j["role"], j["nom"]


def test_familles_attendues():
    from labuse import jobs
    par_fam: dict[int, int] = {}
    for j in jobs.liste():
        par_fam[j["famille"]] = par_fam.get(j["famille"], 0) + 1
    # COCKPIT-1 Lot C : restore-test + recap-matin retirés du registre → 29 jobs, F4 passe de 21 à 19.
    assert par_fam == {1: 2, 2: 6, 3: 2, 4: 19}
    assert sum(par_fam.values()) == 29


# ─────────────── endpoints (db) ───────────────

@pytest.mark.db
def test_usine_endpoint():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/admin/usine")
    assert r.status_code == 200
    j = r.json()
    assert [f["n"] for f in j["familles"]] == [1, 2, 3, 4]
    assert len(j["geles"]) == 5   # 4 Radar + digest (restore-test retiré du registre, Lot C)


@pytest.mark.db
def test_lancer_refuse_agents_et_inconnu():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        assert c.post("/admin/jobs/agents-sources/lancer").status_code == 409
        assert c.post("/admin/jobs/inexistant/lancer").status_code == 404
