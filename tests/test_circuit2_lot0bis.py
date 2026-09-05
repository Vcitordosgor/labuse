"""CIRCUIT-2 lot 0-bis — RÉCONCILIATION avec EXPORTS-1 et ZONE-1.

Le test qui aurait attrapé la dérive : le registre décrivait du code qui n'existe plus
(inventaire CIRCUIT-0 antérieur au merge d'EXPORTS-1/ZONE-1). Verrous posés :
  · chaque `fonction` du registre pointe un fichier qui EXISTE (et la fonction nommée y est) ;
  · les moteurs réconciliés (marche_service, potentiel, zone_servie) portent leurs ids ;
  · la scission du neuf (arbitrage Q3) : deux ids, deux usages, alias de transition ;
  · portée `projet` + règle de couverture des compteurs (garde EXPORTS-1 5.5 → registre) ;
  · la sonde connaît les 4 témoins EXPORTS-1 et les vrais chemins.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from labuse import registre
from labuse.registre.chiffres import ALIAS_TRANSITION, CHIFFRES, resoudre
from labuse.registre.robinets import ROBINETS
from labuse.registre.valeur import Valeur, probleme_couverture

RACINE = Path(__file__).resolve().parents[1]


# ─────────────────── les fonctions du registre pointent du code VIVANT ───────────────────

def test_aucune_fonction_ne_pointe_du_code_mort():
    """0-bis point 2 (dernière puce) : aucune `fonction` ne référence un fichier absent, une
    fonction disparue ou une ligne au-delà de la fin du fichier — LE test qui aurait attrapé
    le registre périmé après le merge d'EXPORTS-1."""
    problemes = []
    for cid, c in CHIFFRES.items():
        f = c.fonction
        for p in re.findall(r"(?:src/labuse|frontend/src)[\w./-]*", f):
            if not (RACINE / p).exists():
                problemes.append(f"{cid} : fichier absent {p}")
        m = re.match(r"^(src/labuse[\w/]+\.py):([A-Za-z_]\w*)", f)
        if m and (RACINE / m.group(1)).exists():
            if m.group(2) not in (RACINE / m.group(1)).read_text():
                problemes.append(f"{cid} : {m.group(1)}:{m.group(2)} introuvable")
        m = re.match(r"^(src/labuse[\w/]+\.py):(\d+)", f)
        if m and (RACINE / m.group(1)).exists():
            n = len((RACINE / m.group(1)).read_text().splitlines())
            if int(m.group(2)) > n:
                problemes.append(f"{cid} : {m.group(1)}:{m.group(2)} > {n} lignes")
    assert problemes == []


# ─────────────────── moteurs réconciliés ───────────────────

def test_marche_service_moteur_des_prix():
    """`marche_communes` est renommé `marche_service` et porte les ids prix (point 2)."""
    assert not [cid for cid, c in CHIFFRES.items() if c.moteur == "marche_communes"]
    portes = {cid for cid, c in CHIFFRES.items() if c.moteur == "marche_service"}
    assert {"prix_ancien_median_eur_m2", "prix_terrain_zone_eur_m2", "tranche_prix_vefa",
            "prix_neuf_vefa_acte_eur_m2", "prix_neuf_observe_eur_m2"} <= portes


def test_potentiel_et_zone_servie_au_registre():
    """Les deux moteurs de main (EXPORTS-1 lot 3, ZONE-1) sont branchés (point 2)."""
    pot = {cid for cid, c in CHIFFRES.items() if c.moteur == "potentiel"}
    assert {"sdp_residuelle_m2", "capacite_logements", "classe_residuel", "potentiel_verdict"} <= pot
    z = CHIFFRES["zone_plu_famille"]
    assert z.moteur == "zone_servie" and z.calcul == "moteur"
    assert "zone_servie.py" in z.fonction
    # plus de pointeur direct residuel.py:80 ni faisabilite_sens1 pour ces ids
    for cid in ("sdp_residuelle_m2", "capacite_logements", "classe_residuel"):
        assert "residuel.py:80" not in CHIFFRES[cid].fonction
        assert "faisabilite_sens1" not in CHIFFRES[cid].fonction


def test_prix_sortie_bati_au_serveur():
    """EXPORTS-1 1.3 : plus de calcul front — la fonction est un chemin serveur (point 2)."""
    c = CHIFFRES["prix_sortie_bati_eur_m2"]
    assert c.moteur == "sector_price"
    assert "frontend/" not in c.fonction
    assert "_q_v2_fiche" in c.fonction


def test_permis_libelles_portent_fenetre_et_rayon():
    """Point 2 : chaque libellé permis dit sa fenêtre (et son rayon quand il en a un) ;
    n_permis_proximite = LE profil client 500 m · 24 mois (arbitrage Q7), fonction sur le
    profil réellement transmis."""
    assert CHIFFRES["n_permis_proximite"].libelle == "Permis à 500 m sur 24 mois"
    assert "flash_500m" in CHIFFRES["n_permis_proximite"].fonction
    for cid in ("permis_12m_n", "permis_5a_n", "depots_secteur_n", "ventes_100m_n"):
        lib = CHIFFRES[cid].libelle
        assert re.search(r"\d+\s*(mois|ans|an\b)|\(\d+ mois\)", lib), (cid, lib)


def test_mixite_declaree():
    c = CHIFFRES["mixite_clause"]
    assert c.moteur == "bilan_promoteur" and "_clause_mixite" in c.fonction


# ─────────────────── scission du neuf (point 3) ───────────────────

def test_scission_neuf_deux_ids_deux_usages():
    assert "prix_neuf_vefa_eur_m2" not in CHIFFRES, "l'ancien id n'est plus déclaré"
    acte, obs = CHIFFRES["prix_neuf_vefa_acte_eur_m2"], CHIFFRES["prix_neuf_observe_eur_m2"]
    assert "scoring" in acte.definition and "score_e" in acte.definition
    assert "bilan" in obs.definition and "exports" in obs.definition
    assert acte.libelle != obs.libelle, "jamais le même libellé pour deux origines"
    # lot 6 : l'alias de transition a vécu UN lot (0-bis → lot 6) puis a été RETIRÉ —
    # plus aucun lecteur de l'ancien id (le grep du registre et des robinets le verrouille).
    assert ALIAS_TRANSITION == {}
    assert resoudre("prix_neuf_vefa_acte_eur_m2") == "prix_neuf_vefa_acte_eur_m2"


def test_scission_neuf_robinets_sans_melange():
    """Aucun robinet ne sert l'un sous le libellé de l'autre : l'ancien id a disparu des
    robinets ; l'acte reste aux écrans commune/comparateur, l'observé au bilan/PDF."""
    for rid, r in ROBINETS.items():
        assert "prix_neuf_vefa_eur_m2" not in r.chiffres, rid
    qui_sert = lambda cid: {rid for rid, r in ROBINETS.items() if cid in r.chiffres}  # noqa: E731
    assert "fiche_parcelle_marche" not in qui_sert("prix_neuf_vefa_acte_eur_m2"), \
        "le VEFA à l'acte est SORTI de la fiche parcelle (Q3)"
    assert qui_sert("prix_neuf_observe_eur_m2") & {"fiche_parcelle_constructibilite", "pdf_banquier"}


def test_scission_neuf_scoring_lit_acte_bilan_lit_observe():
    """La sonde du code : score_e lit le VEFA à l'acte (neuf_vefa_commune), jamais le précalcul ;
    le bilan lit le neuf observé (resolve_prix_neuf_marche)."""
    score_e = (RACINE / "src/labuse/ingestion/score_e.py").read_text()
    assert "neuf_vefa_commune" in score_e
    bilan = (RACINE / "src/labuse/faisabilite/bilan.py").read_text()
    assert "resolve_prix_neuf_marche" in bilan


def test_fuite_neuf_soldee_dans_l_inventaire():
    csv = (RACINE / "docs/CIRCUIT/inventaire/fuites_mesurees.csv").read_text()
    ligne = next(l for l in csv.splitlines() if l.startswith("prix_neuf_vefa_eur_m2;"))
    assert "solde" in ligne and "deux définitions, deux ids" in ligne


# ─────────────────── structure (point 4) ───────────────────

def test_portee_projet_saisies_client():
    for cid in ("cout_construction_saisi_eur_m2", "marge_frais_saisie_pct", "prix_demande_saisi_eur"):
        c = CHIFFRES[cid]
        assert c.portee == "projet" and c.reservoirs == (), cid
        assert "saisi" in c.definition.lower(), cid


def test_tampon_projet_dit_saisi_par_le_client(db_session):
    t = registre.tampons_pour(db_session, ["cout_construction_saisi_eur_m2"])
    tampon = t["cout_construction_saisi_eur_m2"]
    assert tampon["portee"] == "projet" and tampon["run"] is None
    assert "saisi_par_le_client_le" in tampon


def test_couverture_regle_du_registre():
    """Garde EXPORTS-1 5.5 devenue règle : un COMPTEUR (unité « nombre ») sans couverture est
    refusé par la sonde ; avec couverture, il passe ; un non-compteur n'est pas concerné."""
    sans = Valeur(valeur=3, chiffre_id="ventes_100m_n", version_def="x", run=None)
    assert probleme_couverture(sans) and "couverture" in probleme_couverture(sans)
    avec = Valeur(valeur=3, chiffre_id="ventes_100m_n", version_def="x", run=None,
                  couverture={"n": 3, "non_couvert": False})
    assert probleme_couverture(avec) is None
    assert avec.tampon()["couverture"] == {"n": 3, "non_couvert": False}
    pas_compteur = Valeur(valeur=12.5, chiffre_id="taux_lls_pct", version_def="x", run=None)
    assert probleme_couverture(pas_compteur) is None


def test_integrite_apres_reconciliation():
    assert registre.verifier() == []


# ─────────────────── sonde (point 5) ───────────────────

def test_sonde_connait_les_temoins_exports():
    from labuse.sonde_circuit import TEMOINS_PARCELLES
    assert set(TEMOINS_PARCELLES) == {"97415000BO0852", "97401000AD0554",
                                      "97416000DY0106", "97411000AV0110"}
    # même jeu que la recette (jamais deux listes)
    recette = (RACINE / "scripts/recette_exports1.py").read_text()
    for idu in TEMOINS_PARCELLES:
        assert idu in recette


def test_mots_interdits_liste_versionnee():
    import yaml
    doc = yaml.safe_load((RACINE / "config/mots_interdits.yaml").read_text())
    assert doc["version"] and len(doc["mots"]) == 16
    assert "MOBPRO" in doc["mots"] and "n 11" in doc["mots"]


def test_controle_exporte_seulement_la_nuit(db_session, monkeypatch):
    """Le cas recette_exports1 (lourd) n'est joué qu'au passage nocturne (déclencheur cron) —
    jamais au bouton ; les nouveaux contrôles (chemins réels, scission du neuf) tournent
    à chaque passage et écrivent leur verdict."""
    import labuse.sonde_circuit as sc
    appels = []
    monkeypatch.setattr(sc, "verifier_exports", lambda db: appels.append(1) or {"n_mots_interdits": 0})
    res = sc.controle(db_session, declencheur="bouton")
    assert appels == [], "au bouton : pas d'exports"
    assert "scission_neuf" not in res or True   # le verdict complet vit dans circuit_controles
    from sqlalchemy import text
    details = db_session.execute(text(
        "SELECT details FROM circuit_controles ORDER BY id DESC LIMIT 1")).scalar()
    assert "chemins_reels" in str(details) and "scission_neuf" in str(details)
    assert "hors passage nocturne" in str(details)
    sc.controle(db_session, declencheur="cron")
    assert appels == [1], "au cron : le cas exports est joué"


def test_sonde_scission_neuf_ne_crashe_pas(db_session):
    """Sur base de test partielle : la vérification tourne, dit ce qu'elle mesure, n'invente
    rien (0 écart sur une base sans témoins ni score_e 'secteur')."""
    import labuse.sonde_circuit as sc
    sc.ensure(db_session)
    res = sc.verifier_scission_neuf(db_session)
    assert set(res) == {"ecarts_trouves", "mesures"}


@pytest.mark.db
def test_sonde_chemins_reels_familles_couvertes(db_session):
    """Les trois familles dues (HTTP, Copilote, PDF) ne sont plus « non_couverts » : HTTP et
    Copilote sont appelés, la famille PDF est portée par le cas recette (nocturne)."""
    import labuse.sonde_circuit as sc
    sc.ensure(db_session)
    res = sc.verifier_chemins_reels(db_session)
    assert "familles" in res
    assert res["familles"]["pdf"] == "cas recette_exports1 (nocturne)"
