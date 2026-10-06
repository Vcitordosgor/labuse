"""Bilan promoteur (BILAN-1).

Le « Bilan » client n'est plus l'ancien Financier renommé : c'est le bilan
promoteur du modèle de la promotrice (toutes ses lignes, dans ses 4 blocs),
dont la structure est déclarée dans ``declarations/bilan/postes.yaml`` et le
calcul tenu par :mod:`labuse.bilan.moteur`.

Doctrine : on ne pré-remplit que le Sourcé (public) ; tout le reste est vide,
avec un repère cliquable qui n'entre dans le calcul que si le client l'adopte.
"""

from .catalogue import Catalogue, Poste, Bloc, charger_catalogue

__all__ = ["Catalogue", "Poste", "Bloc", "charger_catalogue"]
