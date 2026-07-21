"""Moteur de segments Habitat — UN query builder + une bibliothèque de presets métiers.

11 métiers (et demain 30) partagent les mêmes données parcelle : seuls les FILTRES
changent. Interdiction de coder une vue par métier — un preset = une ligne de données
(`segment_presets`), le moteur évalue ses filtres via le registry déclaratif.

Résilience : le moteur détecte à l'exécution quelles tables/colonnes existent
(`parcel_equipements`, `parcel_anc`… pas encore ingérées) ; un filtre
dont la source manque est GRISÉ côté UI, un preset qui en dépend est badgé « partiel ».
Ce paquet est donc exécutable quel que soit l'ordre des mandats de la pile.
"""
