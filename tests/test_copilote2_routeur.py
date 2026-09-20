"""COPILOTE-2 lot 5 — LE ROUTEUR : 9 intentions → 3 chemins + refus. La MESURE de précision (le
routeur est un appel modèle) est différée (clé à créditer) ; le mandat PRÉPARE le jeu. Ici on
verrouille la partie DÉTERMINISTE : la table 9→3, la taille du jeu, et le routage OUTIL sans modèle."""
from __future__ import annotations

import json
from pathlib import Path

from labuse.copilote_v2 import answering

JEU = Path(__file__).resolve().parents[1] / "captures/copilote2/routeur_jeu.json"


def test_mapping_9_intents_vers_3_chemins():
    """La table 9 intentions → 3 chemins + refus (source de vérité de « d'où sort une réponse »)."""
    cp = answering.chemin_pour
    assert cp("EXPLIQUER") == "WEB"
    assert cp("QUESTION", a_idu=True) == "FICHE"
    assert cp("QUESTION", a_commune=True) == "FICHE"
    assert cp("QUESTION") == "OUTIL"                       # question d'analyse sans lieu nommé
    for i in ("OUTIL", "RECHERCHE", "VERIFICATION", "VEILLE", "PROJET", "PREPARER"):
        assert cp(i) == "OUTIL", i
    assert cp("HORS_SUJET") == "REFUS"


def test_jeu_couvre_les_trois_chemins_plus_hors():
    """Le jeu : au moins 15 questions par chemin + 10 hors périmètre (exigence du mandat)."""
    jeu = json.loads(JEU.read_text(encoding="utf-8"))
    assert len(jeu["FICHE"]) >= 15
    assert len(jeu["OUTIL"]) >= 15
    assert len(jeu["WEB"]) >= 15
    assert len(jeu["REFUS"]) >= 10


def test_jeu_outil_route_sans_modele():
    """Les questions OUTIL qui décrivent une action outillée (comparer, taxe, règlement, charge, assembler,
    courrier) trouvent leur porte SANS modèle (table déterministe) — la part mesurable hors ligne du jeu."""
    attendus = {
        "compare ces deux parcelles": "comparer",
        "quelle charge foncière je peux payer pour ce terrain ?": "calculette-fonciere",
        "écris un courrier au propriétaire": "courriers",
        "montre-moi le règlement de la zone UE à Saint-Denis": "plu",
        "assemble les parcelles voisines de celle-ci": "assemblage",
    }
    for msg, porte in attendus.items():
        cible = answering._match_outil(msg)
        assert cible and cible[0] == porte, f"{msg} → {cible}"


def test_fiche_idu_detecte_sans_modele():
    """Les questions FICHE du jeu portant un IDU sont reconnues déterministiquement (court-circuit lot 1)."""
    jeu = json.loads(JEU.read_text(encoding="utf-8"))
    avec_idu = [q for q in jeu["FICHE"] if answering._idu_dans(q)]
    assert len(avec_idu) >= 10        # la majorité des cas FICHE nomment la parcelle → routables sans modèle
