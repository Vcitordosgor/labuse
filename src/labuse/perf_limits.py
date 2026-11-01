"""FIX-NU3-3 (K-CHG-01/02/03) — LES FILES D'ATTENTE SOUS CHARGE.

Le lot K a mesuré que la garantie « fiche & carte < 1 s pendant les études » TIENT à 10 users mais
CASSE à 25 : le rendu PDF weasyprint (CPU pur, p50 9,5 s → 26 s) et les processus d'étude (jusqu'à
26 simultanés → swap saturé à 8 Go) affament la machine. Aucune requête n'échouait, mais la latence
perçue de fiche/carte montait à ~10 s.

Décision Vic : mettre ces deux travaux lourds EN FILE.
  · `pdf_slot()`      — au plus `pdf_rendu_max` rendus PDF à la fois (les suivants attendent) ;
  · `etude_slot()`    — au plus `etude_processus_max` processus d'étude à la fois ; si la file reste
                        pleine plus de `etude_file_attente_s`, on rend un 503 honnête plutôt que de
                        faire tomber fiche/carte pour tout le monde.

Sémaphores PROCESSUS-LOCAUX (par worker API). Le calcul d'étude tourne dans un process « spawn »
enfant : le plafond est tenu CÔTÉ PARENT (autour du spawn), là où les requêtes arrivent — un enfant
ne voit pas ce sémaphore, et c'est voulu (le parent régule combien d'enfants vivent en même temps).
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from .config import get_settings

# Sémaphores construits UNE fois, à la taille configurée au premier usage. Le cap est un réglage
# d'exploitation (prod), pas un paramètre par requête — un singleton par process convient.
_lock = threading.Lock()
_pdf_sem: threading.BoundedSemaphore | None = None
_etude_sem: threading.BoundedSemaphore | None = None


def _sem(which: str) -> threading.BoundedSemaphore:
    global _pdf_sem, _etude_sem
    with _lock:
        if which == "pdf":
            if _pdf_sem is None:
                _pdf_sem = threading.BoundedSemaphore(max(1, int(get_settings().pdf_rendu_max)))
            return _pdf_sem
        if _etude_sem is None:
            _etude_sem = threading.BoundedSemaphore(max(1, int(get_settings().etude_processus_max)))
        return _etude_sem


@contextmanager
def pdf_slot():
    """Une place de rendu PDF. Bloque tant que `pdf_rendu_max` rendus tournent déjà (file d'attente,
    jamais un rejet : un PDF qui attend 10 s reste correct, un PDF jamais rendu ne l'est pas)."""
    sem = _sem("pdf")
    sem.acquire()
    try:
        yield
    finally:
        sem.release()


@contextmanager
def etude_slot():
    """Une place de processus d'étude. Attente BORNÉE (`etude_file_attente_s`) : si aucune place ne se
    libère, lève `FileEtudePleine` → la route rend un 503 honnête (« trop de monde, réessayez ») au
    lieu de laisser 26 processus saturer la RAM et écrouler fiche/carte. Les plafonds protègent la
    réactivité du reste de l'app, qui est la promesse du mandat."""
    sem = _sem("etude")
    attente = float(get_settings().etude_file_attente_s)
    if not sem.acquire(timeout=attente):
        raise FileEtudePleine()
    try:
        yield
    finally:
        sem.release()


class FileEtudePleine(Exception):
    """Toutes les places d'étude sont prises et aucune ne s'est libérée dans le délai d'attente."""


def _reset_pour_tests() -> None:
    """Oublie les sémaphores (un test qui change les plafonds par env les reconstruit à la bonne taille)."""
    global _pdf_sem, _etude_sem
    with _lock:
        _pdf_sem = _etude_sem = None
