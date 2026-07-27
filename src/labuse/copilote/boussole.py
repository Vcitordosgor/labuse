"""M26-A — filtre boussole sur les payloads d'événements.

Même règle que les exports/courrier : JAMAIS l'identité d'une personne physique dans un
événement. La classification s'appuie sur le référentiel existant
`proprietaire_type.classify_owner_type` (types de personne morale/publique — dont le nom,
adossé à un SIREN public, est servable ; cf. /moteurs/assemblage).

Mécanique en profondeur : dans chaque dict, les clés NOMINATIVES (nom, dénomination,
contact…) ne sont conservées que si le dict porte la preuve d'une personne morale ou
publique (`owner_type`/`type` dans les types PM, ou `personne_morale: true`). Sans cette
preuve → valeur remplacée par le marqueur de filtrage. Deuxième barrière : les wrappers
de moteurs ne mettent déjà que des champs compacts en payload — ce filtre attrape ce qui
passerait quand même.
"""
from __future__ import annotations

import re
from typing import Any

# Types pour lesquels une dénomination est PUBLIQUE (registre SIREN/collectivités) —
# alignés sur proprietaire_type.OWNER_TYPES hors personne_physique/indivision/inconnu.
PM_TYPES = frozenset({
    "commune", "etat", "collectivite", "epf", "etablissement_public",
    "sem", "bailleur_social", "sci", "societe", "copropriete",
})

MARQUEUR = "[identité filtrée — boussole]"

_NOMINATIF = re.compile(
    r"(^|_)(nom|noms|prenom|prenoms|denomination|denom|contact|dirigeant|proprietaire_nom"
    r"|owner_name|owner_denom)($|_)", re.I)
# Bloqués MÊME en contexte personne morale : une PM n'a ni prénom ni contact nominatif ni
# dirigeant servable (le nom d'un dirigeant est une personne physique — cf. Score V v1.3).
_TOUJOURS_BLOQUE = re.compile(r"(^|_)(prenom|prenoms|contact|dirigeant)($|_)", re.I)


def _est_personne_morale(d: dict) -> bool:
    if d.get("personne_morale") is True:
        return True
    for key in ("owner_type", "type_proprietaire", "type"):
        if d.get(key) in PM_TYPES:
            return True
    return d.get("famille") == "public"


def filtrer_payload(payload: Any) -> tuple[Any, int]:
    """Copie filtrée du payload + nombre de valeurs masquées (0 = rien à masquer)."""
    n = 0

    def _walk(o: Any, pm_ctx: bool) -> Any:
        nonlocal n
        if isinstance(o, dict):
            pm = pm_ctx or _est_personne_morale(o)
            out = {}
            for k, v in o.items():
                if _TOUJOURS_BLOQUE.search(str(k)) or (_NOMINATIF.search(str(k)) and not pm):
                    if isinstance(v, (dict, list)):
                        n += 1
                        out[k] = MARQUEUR
                    elif isinstance(v, str) and v.strip() and v != MARQUEUR:
                        n += 1
                        out[k] = MARQUEUR
                    else:
                        out[k] = v
                else:
                    out[k] = _walk(v, pm)
            return out
        if isinstance(o, list):
            return [_walk(v, pm_ctx) for v in o]
        return o

    return _walk(payload, False), n
