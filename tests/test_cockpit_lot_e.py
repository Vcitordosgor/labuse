"""COCKPIT-1 (Lot E) — Sources (bouton Reconstruire) + Journal (filtre famille, entrées boutons).

Unitaire sur `circuit_journal` : les gestes des boutons du Tableau de bord ont une catégorie LISIBLE
(jamais l'identifiant brut à l'écran), et la FAMILLE d'une entrée (4 colonnes de L'usine) est lue du
registre pour un job, de la catégorie sinon.
"""
from __future__ import annotations

from labuse import circuit_journal as cj


def test_gestes_du_tableau_de_bord_ont_une_categorie_lisible():
    # jamais le geste brut « cockpit:… » à l'écran.
    assert cj.categorie_de("cockpit:injecter") == "vanne"
    assert cj.categorie_de("cockpit:reconstruire") == "reconstruction"
    assert cj.categorie_de("cockpit:accepter-ecarts") == "controle"
    assert cj.categorie_de("cockpit:envoyer-prod") == "deploiement"
    assert cj.categorie_de("cockpit:lancer-job") == "cron"
    # et chaque catégorie a un libellé humain.
    for g in ("cockpit:injecter", "cockpit:reconstruire", "cockpit:envoyer-prod"):
        assert cj.CATEGORIE_LABEL.get(cj.categorie_de(g))


def test_famille_d_un_job_lue_du_registre():
    assert cj.famille_de("job", "ingest-bodacc") == "livraisons"     # famille 2
    assert cj.famille_de("job", "coherence-banc") == "controle"      # famille 4
    assert cj.famille_de("job", "sonde-sources") == "veille"         # famille 1
    assert cj.famille_de("cockpit:lancer-job", "fiche-commune-cache") == "moteur"   # famille 3


def test_famille_des_autres_gestes_par_categorie():
    assert cj.famille_de("cockpit:injecter", None) == "veille"
    assert cj.famille_de("calculer", None) == "moteur"
    assert cj.famille_de("cockpit:envoyer-prod", None) == "moteur"
    assert cj.famille_de("cockpit:accepter-ecarts", None) == "controle"


def test_filtre_famille_cible_les_bons_gestes_et_jobs():
    gestes, jobs = cj.gestes_et_jobs_de_famille("livraisons")
    assert "ingest-bodacc" in jobs and "ingest-dpe" in jobs
    assert "job" not in gestes   # le job n'est ciblé que par sa cible (nom), pas par le geste
    gestes_v, jobs_v = cj.gestes_et_jobs_de_famille("veille")
    assert "cockpit:injecter" in gestes_v or "injecter" in gestes_v
    assert "sonde-sources" in jobs_v


def test_quatre_familles():
    assert [s for s, _ in cj.FAMILLES_JOURNAL] == ["veille", "livraisons", "moteur", "controle"]
