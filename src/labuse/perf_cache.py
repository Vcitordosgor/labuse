"""VITESSE-3 — mémo IN-PROCESS à clé de FRAÎCHEUR (chaque worker réchauffe le sien).

Doctrine déjà en place dans LA BUSE (`circuit_garanties.noms_vides_caches`, `stripe_lecture._CACHE`,
`recherche._communes_cache`) : un calcul coûteux ET stable est servi depuis la mémoire du worker.

Garantie d'IDENTITÉ (mandat VITESSE-3 : « identique à l'octet près à l'avant »). L'entrée n'est
servie que si sa CLÉ DE FRAÎCHEUR est inchangée. La clé embarque tout ce dont dépend le calcul :
`empreinte_attendue` (run servi + cascade + résiduel + millésimes sources + version du code — la
MÊME clé que le cache de fiche commune) et, quand la réponse porte un délai en jours, le jour
Réunion. Clé identique ⇒ mêmes entrées ⇒ recalcul octet pour octet. Clé différente ⇒ recalcul.

La réponse mémoïsée est traitée en LECTURE SEULE : l'appelant la sérialise sans la muter.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Callable

_MISS = object()


class MemoLRU:
    """Mémo borné (LRU) et thread-safe. Le plafond protège les clés à cardinalité ouverte
    (polygones d'étude de zone dessinés librement) : au-delà, la plus ancienne entrée tombe."""

    def __init__(self, maxsize: int = 256) -> None:
        self._d: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = threading.Lock()
        self.maxsize = maxsize

    def get_or_compute(self, cle: str, calcul: Callable[[], Any]) -> Any:
        with self._lock:
            if cle in self._d:
                self._d.move_to_end(cle)
                return self._d[cle]
        # calcul HORS verrou (ne sérialise pas les requêtes lentes entre elles ; au pire deux
        # workers calculent la même clé une fois — le résultat est identique, aucune incohérence).
        val = calcul()
        with self._lock:
            self._d[cle] = val
            self._d.move_to_end(cle)
            while len(self._d) > self.maxsize:
                self._d.popitem(last=False)
        return val

    def peek(self, cle: str) -> Any:
        with self._lock:
            return self._d.get(cle, _MISS)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()


def manque(valeur: Any) -> bool:
    return valeur is _MISS
