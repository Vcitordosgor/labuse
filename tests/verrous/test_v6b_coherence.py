"""V6b (COHERENCE-FIX-1 lot G) — le banc de cohérence est permanent, joué à chaque commit.

Sur la base de TEST du process (jamais la vraie base en CI) : structure des tables de
vérification, vocabulaire d'absence à cinq formes, règle du registre (toute donnée a un
lecteur déclaré ou un chantier nommé), et golden des 7 témoins (rejoué quand les témoins
sont en base — un témoin hors base est DIT, pas cassé)."""
from __future__ import annotations

import pytest

from labuse.circuit_verrous import verrou_coherence_banc

pytestmark = pytest.mark.verrous


def test_v6b_coherence_banc():
    r = verrou_coherence_banc()
    assert r.verdict != "casse", f"{r.preuve} — {r.details[:10]}"
