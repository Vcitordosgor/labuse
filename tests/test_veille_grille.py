"""VEILLE-FIX-2 — LA GRILLE fait loi (config/veille.yaml), et le code en dérive.

Ce test GRAVE la décision de Vic (27/09/2026) : toute dérive de la table (qui est prévenu, cloche, mail)
casse ici. Il vérifie aussi que les listes de `kind` du code (events._DIGEST_KINDS / _CLOCHE_KINDS /
_IMMEDIAT_KINDS) sont bien DÉRIVÉES de la grille — pas une seconde source de vérité qui pourrait diverger.
"""
from __future__ import annotations

from labuse import veille_grille as g

# La table décidée par Vic — recopiée ICI (le test), comparée à la config. Deux copies indépendantes :
# si l'une bouge sans l'autre, le test tombe. (event → destinataire, cloche, mail)
GRILLE_DECIDEE = {
    "parcelle_suivie":   ("suiveur",  "oui",  "digest"),
    "radar_match":       ("criteres", "oui",  "digest"),
    "radar_baisse":      ("criteres", "oui",  "digest"),
    "radar_retrait":     ("criteres", "oui",  "digest"),
    "parcelle_en_vente": ("suiveur",  "tete", "immediat"),
    "bascule":           ("tous",     "oui",  "non"),
    "nouvelle_source":   ("tous",     "oui",  "non"),
    "essai":             ("compte",   "non",  "dedie"),
}


def test_grille_yaml_est_exactement_la_decision():
    evs = g.evenements()
    assert set(evs) == set(GRILLE_DECIDEE), "les événements de config/veille.yaml ≠ la table décidée"
    for nom, (dest, cloche, mail) in GRILLE_DECIDEE.items():
        e = evs[nom]
        assert (e["destinataire"], e["cloche"], e["mail"]) == (dest, cloche, mail), f"ligne {nom} a dérivé"


def test_frequences_et_defaut():
    assert g.frequences() == ["quotidien", "hebdo", "cloche_seule"]
    assert g.frequence_defaut() == "quotidien"
    assert g.frequence_valide(None) == "quotidien"
    assert g.frequence_valide("hebdo") == "hebdo"
    assert g.frequence_valide("n'importe quoi") == "quotidien"
    assert g.hebdo_jour() == 0            # lundi
    assert g.digest_heure_reunion() == "07:15"


def test_une_seule_notification_immediate():
    """Règle : la SEULE notification immédiate est la mise en vente d'une parcelle suivie."""
    assert g.kinds_immediat() == ("parcelle_en_vente",)


def test_le_code_derive_de_la_grille():
    """Les listes de kinds d'events.py DÉRIVENT de la grille (pas de seconde source de vérité)."""
    from labuse.api import events as e
    assert e._DIGEST_KINDS == g.kinds_digest()
    assert e._IMMEDIAT_KINDS == g.kinds_immediat()
    # tous les kinds « cloche » de la grille sont bien affichables à la cloche du client
    for k in g.kinds_cloche():
        assert k in e._CLOCHE_KINDS, f"{k} manque à _CLOCHE_KINDS"
    # un kind IMMÉDIAT ne part JAMAIS dans le digest (sinon double envoi)
    for k in g.kinds_immediat():
        assert k not in e._DIGEST_KINDS, f"{k} ne doit pas être dans le digest"
    # marché / nouveauté : cloche pour tous, JAMAIS de mail
    for k in g.kinds_broadcast():
        assert k not in e._DIGEST_KINDS, f"{k} (broadcast) ne doit jamais être e-mailé"


def test_chaque_kind_de_la_grille_est_declare_au_registre():
    """Un kind produit par la grille doit être routable par le registre des notifications."""
    from labuse.notif_registry import type_pour_kind, est_declare
    for nom, e in g.evenements().items():
        kind = e.get("kind")
        if not kind:
            continue
        assert est_declare(type_pour_kind(kind)), f"{nom} ({kind}) → type non déclaré au registre"
