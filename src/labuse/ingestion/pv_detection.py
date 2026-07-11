"""Stub Lot 4.3 Habitat Solaire — détection des panneaux PV sur orthophoto.

L'implémentation ML est HORS du mandat habitat-solaire : elle appartient au
mandat « Détection Ortho » (même mandat que la détection piscines), qui livrera
la table `parcel_equipements` (le registry des segments l'attend déjà : filtres
`pv_detecte` et `piscine` grisés « disponible prochainement »).
"""
from __future__ import annotations

from typing import Any


def detect_rooftop_pv(ortho_tile: Any) -> list[Any]:
    """Détecte les panneaux photovoltaïques sur une tuile d'orthophoto → polygones.

    Approche prévue (mandat Détection Ortho) :
    - source : ortho IGN 20 cm (Géoplateforme WMS/WMTS), tuilée sur l'emprise bâtie ;
    - segmentation sémantique binaire « panneau PV » (les toits réunionnais tôlés
      offrent un bon contraste ; attention aux chauffe-eau solaires, classe voisine
      à séparer) ; MÊME TOPOLOGIE que la détection piscines : tuile → masques →
      polygonisation → géoréférencement → intersection parcelles ;
    - sortie : polygones 4326 + score de confiance, versés dans
      `parcel_equipements.pv` (bool) et exploités par
      `parcel_solar.pv_existant = 'detecte'` (supplante 'commune_forte_densite')
      et par le badge « équipé » des parkings APER (ombrières existantes).

    Lève NotImplementedError tant que le mandat Détection Ortho n'a pas livré.
    """
    raise NotImplementedError(
        "Détection PV sur ortho : mandat « Détection Ortho » (parcel_equipements). "
        "Voir docstring pour l'approche prévue."
    )
