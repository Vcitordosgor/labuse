"""CIRCUIT-1 lot 2.5 → CIRCUIT-2 lot 1.6 — les fonctions de calcul EXTRAITES des endpoints, une
par donnée (ou par famille de données). Un robinet ne calcule pas : il appelle ici.

Modules (un par maille) : `zonage` (moteur zonage_commune — parts de SURFACE d'une commune, ≠
zone_servie d'une parcelle), `commune` (commune_compteurs), `parcelle` (parcelle_proximites),
`plateforme` (plateforme_compteurs), `proprietaire` (délégations maille propriétaire). Aucun
import ici (les modules s'importent à la demande — pas de coût ni de cycle au boot).
"""
