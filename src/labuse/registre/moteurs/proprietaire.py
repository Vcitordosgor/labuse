"""CIRCUIT-2 lot 1.6 — maille PROPRIÉTAIRE (moteur `proprietaire_historique`). Le portefeuille PM
vit dans api/modules.py:patrimoine (une requête multi-jointures run-scopée, dont `n_parcelles` est
un sous-produit) : extraction refusée — un count parallèle sur parcelle_personne_morale ferait DEUX
chemins qui divergent (assiette jointe vs table brute). Délégation nommée, une seule vérité.
"""
from __future__ import annotations


def compte_parcelles_pm(db, siren: str) -> int:
    """n_parcelles_pm — délégation : le calcul vit dans api/modules.py:patrimoine (le portefeuille
    complet du SIREN, jointure parcels — même assiette que la liste et le CSV)."""
    from ...api.modules import patrimoine
    return int(patrimoine(siren, db=db)["n_parcelles"])
