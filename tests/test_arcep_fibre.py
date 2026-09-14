"""SOURCES-4 lot 2 — Arcep « Ma connexion internet » : toutes les technos + le meilleur débit.

On ne gardait que le FttH (FO) ; l'Arcep publie AUSSI le cuivre/DSL, la 4G fixe, le satellite et la
classe de débit (descendant/montant) par immeuble. `_meilleur_debit` retient la meilleure classe
disponible (THD1G > THD100 > … > INEL). Les technos hors FttH restent déclaratives (étiquetées).
"""
from __future__ import annotations

from labuse.ingestion.arcep_fibre import _meilleur_debit


def test_meilleur_debit_ordre():
    assert _meilleur_debit({"BHD8", "THD1G", "HD3"}) == "THD1G"     # le meilleur l'emporte
    assert _meilleur_debit({"HD05", "HD3"}) == "HD3"
    assert _meilleur_debit({"INEL"}) == "INEL"
    assert _meilleur_debit(set()) is None                          # rien → None (jamais inventé)
    assert _meilleur_debit({"XXX_inconnu"}) is None                # classe inconnue ignorée
