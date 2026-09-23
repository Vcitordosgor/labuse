"""CIRCUIT-P4 (lot 2) — l'onglet « À faire » : chaque type de ligne construit, puis le cas vide.

Cinq types de lignes seulement (Injecter · Calculer · Basculer · Déposer · Décider). Le nombre de
l'onglet = le nombre de lignes.
"""
from labuse import circuit_resume as R


def _res(nom, lib, **extra):
    return {"id": extra.pop("id", 1), "nom": nom, "etat": ["ambre", lib], **extra}


def test_ligne_injecter():
    res = [_res("BD TOPO", "nouvelle version", millesime="2025-12",
               veille={"vu": "2026-03"}, vanne={"label": "ingest-bdtopo"})]
    af = R.composer_a_faire(res, residuel=None, candidat=None, run_servi="q", verrous={"casses": []})
    assert af["total"] == 1
    l = af["lignes"][0]
    assert l["type"] == "injecter" and l["bouton"]["label"] == "Injecter"
    assert l["bouton"]["source"] == 1


def test_ligne_deposer():
    res = [_res("Radar", "échue", cadence_jours=7, dernier_controle="2026-09-09T00:00:00")]
    af = R.composer_a_faire(res, residuel=None, candidat=None, run_servi="q", verrous={"casses": []})
    assert af["total"] == 1 and af["lignes"][0]["type"] == "deposer"
    assert af["lignes"][0]["bouton"]["label"] == "Déposer un fichier"


def test_ligne_calculer_depuis_residuel():
    af = R.composer_a_faire([], residuel={"changees": True, "detail": "PLU/GPU a bougé"},
                            candidat=None, run_servi="q", verrous={"casses": []})
    assert af["total"] == 1 and af["lignes"][0]["type"] == "calculer"
    assert af["lignes"][0]["ghost"]["label"] == "voir les changements"


def test_ligne_calculer_enrichie_lot4():
    """Quand le lot 4 passe `calculer`, la ligne prend son titre/phrase/touche."""
    calc = {"actif": True, "titre": "Calculer le résiduel", "phrase": "Règles PLU changées. Touche : capacité.",
            "touche": ["capacité", "score"], "changements": ["règles PLU : 97411"]}
    af = R.composer_a_faire([], residuel=None, candidat=None, run_servi="q",
                            verrous={"casses": []}, calculer=calc)
    assert af["total"] == 1 and af["lignes"][0]["titre"] == "Calculer le résiduel"


def test_ligne_basculer_grisee_si_calculer_precede():
    """Un candidat + un Calculer présent → Basculer GRISÉ avec sa raison."""
    af = R.composer_a_faire([], residuel={"changees": True, "detail": "x"}, candidat="q_v15",
                            run_servi="q_v11", verrous={"casses": []})
    types = [l["type"] for l in af["lignes"]]
    assert types == ["calculer", "basculer"]
    basc = af["lignes"][1]
    assert basc["bouton"]["disabled"] is True and basc["bouton"]["raison"]


def test_ligne_basculer_active_sans_calculer():
    af = R.composer_a_faire([], residuel={"changees": False}, candidat="q_v15",
                            run_servi="q_v11", verrous={"casses": []})
    assert af["total"] == 1 and af["lignes"][0]["type"] == "basculer"
    assert af["lignes"][0]["bouton"]["disabled"] is False


def test_ligne_decider_par_verrou_casse():
    af = R.composer_a_faire([], residuel=None, candidat=None, run_servi="q",
                            verrous={"casses": ["V1c", "V3a"]})
    assert af["total"] == 2 and all(l["type"] == "decider" for l in af["lignes"])


def test_compteur_egale_lignes():
    """Le nombre de l'onglet = le nombre de lignes, tous types confondus."""
    res = [_res("BD TOPO", "nouvelle version", id=1),
           _res("Radar", "échue", id=2, dernier_controle="2026-09-09T00:00:00")]
    af = R.composer_a_faire(res, residuel={"changees": True, "detail": "x"}, candidat="q_v15",
                            run_servi="q_v11", verrous={"casses": ["V1c"]})
    assert af["total"] == len(af["lignes"])
    # injecter + calculer + basculer + deposer + decider = 5
    assert af["total"] == 5


def test_vide_rien_a_faire():
    """Rien à faire → total 0, aucune ligne (la page dira « Rien à faire »)."""
    af = R.composer_a_faire([_res("Cadastre", "à jour")], residuel={"changees": False},
                            candidat=None, run_servi="q", verrous={"casses": []},
                            etats_compte={"nouvelle version": 0, "sonde en panne": 0, "total": 91})
    assert af["total"] == 0 and af["lignes"] == []
    assert af["calme"]["vitrine"] == 91
