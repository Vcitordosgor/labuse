"""RETOURS-23 (pt 6) — extraction du TITRE « en clair » + corps d'un extrait de règlement PLU
(carte d'articles, maquette 8-plu-articles). Heuristique pure `plu_titre_corps` : titre lu en tête du
verbatim, remis en casse de phrase quand le PDF l'a recopié tout en majuscules ; corps = le reste."""
from labuse.api.modules import plu_titre_corps


def test_titre_majuscules_remis_en_casse_de_phrase():
    v = ("ARTICLE UE 14 - COEFFICIENT D'OCCUPATION DU SOL Il n'est pas fixé de "
         "coefficient d'occupation du sol.")
    titre, corps = plu_titre_corps(v)
    assert titre == "Coefficient d'occupation du sol"
    assert corps.startswith("Il n'est pas fixé")


def test_titre_coupe_au_sous_article():
    v = ("ARTICLE AUE 1 - OCCUPATIONS ET UTILISATIONS DU SOL INTERDITES 1.1 - Rappels 1. "
         "La dérogation à l'interdiction générale de défricher doit être obtenue")
    titre, corps = plu_titre_corps(v)
    assert titre == "Occupations et utilisations du sol interdites"
    assert corps.startswith("1.1")


def test_titre_sans_tiret_ni_majuscules():
    # casse mixte, pas de tiret : le titre reste tel quel (déjà « en clair »), aucune MAJ forcée.
    v = ("Article Ua.13 Espaces libres, aires de jeux et/ou de loisirs, plantations "
         "En secteur Ua : Les espaces libres")
    titre, corps = plu_titre_corps(v)
    assert titre is not None
    assert titre[0].isupper()
    # pas de tout-majuscule imposé : on garde la casse d'origine
    assert titre != titre.upper()


def test_titre_conserve_accents_quand_source_les_a():
    v = ("ARTICLE N 8 - IMPLANTATION DES CONSTRUCTIONS Sans objet.")
    titre, corps = plu_titre_corps(v)
    assert titre == "Implantation des constructions"
    assert corps == "Sans objet."


def test_puces_pdf_retirees_du_titre():
    # le PDF sème une puce Wingdings (U+F0B7) après le titre, avant la 1ʳᵉ sous-section.
    v = "Article 10-  \nHauteur maximale des constructions \n 10.1 - Définition La hauteur…"
    titre, corps = plu_titre_corps(v)
    assert titre == "Hauteur maximale des constructions"
    assert "" not in titre
    assert corps.startswith("10.1")


def test_tiret_de_ref_preserve_le_titre():
    # le « - » ne doit PAS être supprimé du texte (il sépare la réf du titre).
    v = "ARTICLE UE 14 - COEFFICIENT D'OCCUPATION DU SOL Il n'est pas fixé."
    titre, _ = plu_titre_corps(v)
    assert titre == "Coefficient d'occupation du sol"


def test_verbatim_vide_ou_ref_seule():
    assert plu_titre_corps("")[0] is None
    titre, corps = plu_titre_corps("ARTICLE U 6")
    # ref seule : rien d'exploitable → titre None, corps = le texte entier (jamais une exception).
    assert titre is None
    assert corps == "ARTICLE U 6"


def test_corps_ne_repete_pas_le_titre():
    v = "ARTICLE A9 - EMPRISE AU SOL DES CONSTRUCTIONS Il n'est pas fixé de règle."
    titre, corps = plu_titre_corps(v)
    assert titre == "Emprise au sol des constructions"
    assert "EMPRISE AU SOL" not in corps.upper() or corps.upper().startswith("IL")
