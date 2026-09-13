"""Bloc « 9. Bilan de l'opération ». Au lot 2 : l'encart ambre « renseignez votre opération »
tant qu'aucun questionnaire n'est rempli (le vrai bloc Financier s'y branche au lot 5). ABSENT du
Flash (le Flash ne compose pas ce bloc)."""
from __future__ import annotations

from ..rendu import note, section

IDS = ()


def rendu(valeurs) -> str:
    encart = (
        '<div class="projet keep">'
        '<div class="t">Renseignez votre opération pour obtenir le bilan</div>'
        # RECETTE-12 D6 — « scénario » RETIRÉ de la liste : le scénario a été supprimé en RECETTE-10.
        '<p style="margin:0 0 4pt">Le bilan dépend de chiffres que vous seul connaissez : prix '
        'demandé par le vendeur, coût de construction, marge visée. LABUSE ne les '
        'suppose pas à votre place.</p>'
        '<p style="margin:0">Une fois renseignés dans votre projet, cette section imprime le '
        "chiffre d'affaires, la charge foncière supportable, l'écart au prix demandé et la "
        'sensibilité au coût de construction. Le document « Financier » reprend cette section '
        'seule.</p></div>')
    return section("9. Bilan de l'opération", encart)
