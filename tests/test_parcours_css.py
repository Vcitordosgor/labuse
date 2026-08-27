"""E7 (parcours d'entrée) — garde-fous CSS mobile des pages serveur (coffre_ui).

Deux bugs trouvés et gelés :
- le raccourci `font:<size> inherit` est INVALIDE (`inherit` n'est pas une font-family de
  shorthand) → la règle était IGNORÉE ; les champs tombaient au défaut UA ~13 px, sous le seuil
  iOS 16 px → zoom au focus. Les champs doivent porter font-size 16px en LONGHAND.
- les titres `'Space Grotesk',inherit` étaient invalides → la police d'identité ne s'appliquait pas.
"""
from __future__ import annotations

import re

from labuse.api import coffre_ui

# Dépouiller les commentaires /* … */ (ils peuvent CITER l'ancien bug sans être une vraie règle).
CSS = re.sub(r"/\*.*?\*/", "", coffre_ui.CSS, flags=re.S)


def test_pas_de_raccourci_font_inherit_invalide():
    """Aucun `font:… inherit` (raccourci invalide) ne doit subsister dans la CSS du parcours."""
    coupables = re.findall(r"font:[^;}]*\binherit\b", CSS)
    assert not coupables, f"raccourci font:…inherit invalide (règle ignorée) : {coupables}"


def test_champs_texte_en_16px():
    """La règle des champs email/password/text porte font-size:16px (anti-zoom iOS)."""
    m = re.search(r"input\[type=email\][^{]*\{([^}]*)\}", CSS)
    assert m, "règle des champs introuvable"
    corps = m.group(1)
    assert "font-size:16px" in corps, corps


def test_titres_ont_une_famille_valide():
    """h1 et .prix gardent Space Grotesk avec un repli GÉNÉRIQUE valide (pas 'inherit')."""
    for sel in ("h1", r"\.recap \.prix"):
        m = re.search(sel + r"\{([^}]*)\}", CSS)
        assert m and "Space Grotesk" in m.group(1)
        assert "sans-serif" in m.group(1), f"{sel} sans repli générique valide"
