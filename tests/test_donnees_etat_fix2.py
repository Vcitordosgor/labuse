"""DONNEES-ETAT-FIX-2 — garde-fous des lots 0, A, B, C, D.

- Lot 0 : couvert dans test_donnees_etat_fix1.py (deploy_app repose le crontab, deploiement.json, vps obsolète).
- Lot A : agent de restauration Mac (garde 20 Go, run servi, marqueur) + carte + lecteur.
- Lot B : carte copie hors-site (jaune 7 j / rouge 10 j).
- Lot C : une carte par incident OUVERT, y compris vérité-sources et job-echec:* ; un fermé disparaît.
- Lot D : la bascule rejoue la cloche + rafraîchit les caches (propagation).
"""
from __future__ import annotations

import json
from pathlib import Path

from labuse import cockpit_resume as ck

RACINE = Path(__file__).resolve().parents[1]


# ─────────────── Lot B — carte copie hors-site ───────────────

def test_carte_copie_externe_seuils():
    assert ck._carte_copie_externe({"age_j": 3}) is None                      # fraîche → pas de carte
    assert ck._carte_copie_externe({"age_j": 7, "derniere": "21/10"})["pastille"] == "jaune"   # 7 j
    assert ck._carte_copie_externe({"age_j": 9, "derniere": "19/10"})["pastille"] == "jaune"   # 7–9 j
    assert ck._carte_copie_externe({"age_j": 10, "derniere": "18/10"})["pastille"] == "rouge"  # 10 j
    assert ck._carte_copie_externe(None) is None                              # marqueur absent → pas de carte


# ─────────────── Lot A — carte + lecteur du test de restauration ───────────────

def test_carte_restore_test_verdicts():
    assert ck._carte_restore_test(None) is None
    assert ck._carte_restore_test({"statut": "ok", "test_at": "2026-10-28T02:00"})["pastille"] == "gris"
    assert ck._carte_restore_test({"statut": "ko", "message": "x"})["pastille"] == "rouge"
    assert ck._carte_restore_test({"statut": "refuse", "message": "espace"})["pastille"] == "jaune"


def test_lire_restore_test_marqueur(tmp_path):
    from labuse import ops_alertes
    assert ops_alertes.lire_restore_test(str(tmp_path)) is None               # absent → None
    (tmp_path / ops_alertes.MARQUEUR_RESTORE_TEST).write_text(
        json.dumps({"statut": "ok", "test_at": "2026-10-28T02:00:00", "run_servi": "q_v20"}))
    d = ops_alertes.lire_restore_test(str(tmp_path))
    assert d and d["statut"] == "ok" and d["run_servi"] == "q_v20"


def test_restore_test_sh_garde_run_servi_marqueur():
    sh = (RACINE / "deploy/mac/restore_test.sh").read_text()
    assert "LABUSE_RESTORE_MIN_GO" in sh and "df -g" in sh                    # garde-fou espace
    assert "20" in sh                                                         # défaut 20 Go
    assert "served_run.txt" in sh and "score_labuse WHERE run_label" in sh    # compte le run servi
    assert ".restore-test.json" in sh and "ecrire_marqueur" in sh            # marqueur dashboard
    assert "DROP DATABASE IF EXISTS" in sh                                    # base jetable supprimée


def test_restore_test_installe_par_install_agents():
    sh = (RACINE / "deploy/mac/install_agents.sh").read_text()
    assert "restore_test.sh" in sh and "com.labuse.restore-test" in sh
    plist = (RACINE / "deploy/mac/com.labuse.restore-test.plist").read_text()
    assert "/.labuse/ops/restore_test.sh" in plist                           # chemin installé (pas ~/Desktop)
    assert "/Desktop/" not in plist


# ─────────────── Lot C — toutes les incidents ouverts deviennent des cartes ───────────────

def test_cartes_incidents_rend_verite_sources_et_job_echec():
    incs = [
        {"cle": "verite-sources", "sujet": "Vérité sources : 3 écart(s)",
         "detail": "• A — zone : servi X vs source Y", "ouvert_at": "2026-10-15T06:04", "rappels": 0},
        {"cle": "job-echec:agents-sources", "sujet": "Job en échec : agents-sources",
         "detail": "boom", "ouvert_at": "2026-10-28T01:46", "rappels": 1},
    ]
    cartes = ck._cartes_incidents(incs)
    ids = {c["id"] for c in cartes}
    assert "incident:verite-sources" in ids and "incident:job-echec:agents-sources" in ids
    vs = next(c for c in cartes if c["id"] == "incident:verite-sources")
    assert vs["pastille"] == "rouge" and vs["voir_detail"] is True            # carte rouge + Voir le détail
    assert "écart" in vs["detail"]["texte"]                                   # les 3 écarts lisibles
    assert vs["bouton"]["action"] == "accepter-incident"                     # bouton Accepter


def test_cartes_incidents_copie_externe_deleguee_et_ferme_disparait():
    # la copie externe est rendue par la carte dédiée (Lot B), pas ici
    assert ck._cartes_incidents([{"cle": "copie-externe-ancienne", "sujet": "x"}]) == []
    # un incident fermé n'est pas dans la liste incidents_ouverts → aucune carte
    assert ck._cartes_incidents([]) == []


# ─────────────── Lot D — la bascule propage (cloche + caches) ───────────────

def test_bascule_a_une_propagation():
    src = (RACINE / "src/labuse/bascule_flux.py").read_text()
    assert "_propager_apres_bascule" in src
    assert "detect_events" in src and "evaluer_radar_cloche" in src            # cloche rejouée
    assert "\"rebuild\"" in src or "'rebuild'" in src                         # caches rafraîchis (détaché)
    # basculer() renvoie la propagation
    assert "\"propagation\": propagation" in src
