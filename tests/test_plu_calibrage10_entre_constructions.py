"""PLU-CALIBRAGE-10 (fix) — garde-fou : l'injection des feuilles `retraits.entre_constructions`
(implantation des constructions d'une même unité foncière, ex-art. 8) ne doit RIEN changer à la
RÉSOLUTION DE ZONE. Ces feuilles sont lues par le seul contrôle d'implantation ; elles ne portent
pas l'enveloppe du gabarit et ne « calibrent » donc pas une zone.

La régression corrigée : une feuille `entre_constructions` posée sur une zone gelée (ex. Les Avirons
AUes, listée en `zones_au_st`) la faisait reconnaître comme calibrée en correspondance directe, d'où
un repli en « estimation générique » CONSTRUCTIBLE au lieu de la branche gelée non constructible.

Ces tests figent que :
  1. les 23 fichiers PLU se chargent (parse + feuilles itérables) ;
  2. le nombre de zones calibrées (portant l'enveloppe) par commune est celui d'AVANT PLU-10 — toute
     casse de fichier (ou une feuille descriptive promue à tort en calibrage) le fait bouger ;
  3. une feuille purement descriptive ne porte pas l'enveloppe ;
  4. Les Avirons AUes : la feuille `entre_constructions` est bien là ET la zone reste non constructible.
"""
from __future__ import annotations

import pytest

from labuse.plu import destinations as D
from labuse.faisabilite.zonage import resolve_zone_v2


def _fichiers_plu():
    return sorted(D._DEST_DIR.glob("974??_*.yaml"))


# Nombre de zones PORTANT l'enveloppe (hauteur/emprise/reculs/stationnement/mixité/pleine terre),
# par commune — relevé AVANT PLU-10 (commit e193d7e5) et inchangé APRÈS le fix. Une évolution
# LÉGITIME du calibrage d'enveloppe met ce tableau à jour À LA MAIN ; l'ajout d'une feuille
# `entre_constructions` NE DOIT PAS le toucher.
ZONES_CALIBREES_ATTENDUES = {
    "97401": 19, "97402": 14, "97403": 5, "97404": 12, "97405": 15, "97406": 9, "97407": 13,
    "97408": 22, "97409": 8, "97410": 5, "97411": 21, "97412": 24, "97413": 18, "97414": 18,
    "97415": 31, "97416": 27, "97418": 19, "97419": 9, "97420": 12, "97421": 10, "97422": 20,
    "97423": 9, "97424": 8,
}


def test_les_23_fichiers_plu_se_chargent():
    """Chaque fichier PLU parse, porte un `meta.insee`, et toutes ses feuilles sont itérables."""
    fichiers = _fichiers_plu()
    assert len(fichiers) == 23, f"attendu 23 fichiers PLU, trouvé {len(fichiers)}"
    for f in fichiers:
        doc = D._load_yaml(str(f))
        assert isinstance(doc, dict) and doc, f"{f.name} ne se charge pas"
        ins = (doc.get("meta") or {}).get("insee")
        assert ins, f"{f.name} sans meta.insee"
        for zone, zv in (doc.get("zones") or {}).items():
            if isinstance(zv, dict) and zv.get("regles"):
                # ne doit pas lever : feuilles bien formées
                list(D.iter_regles_feuilles(zv["regles"]))


@pytest.mark.parametrize("insee,attendu", sorted(ZONES_CALIBREES_ATTENDUES.items()))
def test_nombre_zones_calibrees_identique_a_avant_plu10(insee, attendu):
    """Le nombre de zones calibrées (enveloppe) par commune = celui d'avant PLU-10. Une feuille
    `entre_constructions` injectée sur une zone ne la fait PAS entrer dans ce compte."""
    obtenu = len(D.zones_calibrees(insee))
    assert obtenu == attendu, (
        f"{insee} : {obtenu} zones calibrées, attendu {attendu} (avant PLU-10). "
        f"Une feuille descriptive a-t-elle été comptée comme calibrage, ou un fichier est-il cassé ?")


def test_feuille_descriptive_ne_porte_pas_l_enveloppe():
    """`regles_portent_enveloppe` : seule une feuille d'enveloppe compte ; entre_constructions non."""
    assert D.regles_portent_enveloppe(None) is False
    assert D.regles_portent_enveloppe({}) is False
    descriptive = {"retraits": {"entre_constructions": {
        "forme": "fixe", "min_m": 3, "article": "Art. 8", "page_pdf": 1,
        "citation": "…", "statut": "valide"}}}
    assert D.regles_portent_enveloppe(descriptive) is False
    enveloppe = {"hauteur": {"egout": {"m": 9, "article": "Art. 10", "page_pdf": 1,
                                       "citation": "…", "statut": "valide"}}}
    assert D.regles_portent_enveloppe(enveloppe) is True
    # une zone qui porte LES DEUX est calibrée (l'enveloppe l'emporte) :
    assert D.regles_portent_enveloppe({**descriptive, **enveloppe}) is True


def test_avirons_aues_entre_constructions_reste_non_constructible():
    """La régression d'origine : AUes (Les Avirons) PORTE une feuille `entre_constructions` mais
    reste gelée (zones_au_st) → NON calibrée et NON constructible."""
    regles_aues = D.regles_zone("97401", "AUes")
    assert regles_aues.get("retraits", {}).get("entre_constructions"), \
        "la règle de distance entre constructions doit être présente sur AUes"
    assert "AUes" not in D.zones_calibrees("97401"), \
        "AUes ne doit pas être calibrée sur la seule foi d'une feuille descriptive"
    r = resolve_zone_v2("AUes", "97401")
    assert r is not None and r.constructible_neuf is False
    assert (r.sources or {}).get("zone") != "estimation générique", \
        "AUes doit se résoudre par la branche gelée, pas en estimation générique"
