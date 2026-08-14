"""M73-F — le plan de situation ortho : un échec se DIT avec sa RAISON (jamais un cadre vide). Les
raisons sont DISTINCTES (réseau ≠ hors emprise ≠ sans géométrie) — « un garde qui échoue pour raison
d'environnement doit le dire »."""
from __future__ import annotations

from pathlib import Path

from labuse.api.plan_situation import plan_ortho


def test_sans_geometrie_dit_la_raison():
    r = plan_ortho(None, Path("/tmp"))
    assert r["ok"] is False and "géométrie" in r["echec"]
    r2 = plan_ortho("", Path("/tmp"))
    assert r2["ok"] is False and "géométrie" in r2["echec"]


def test_toujours_un_dict_jamais_none():
    # contrat : plan_ortho renvoie TOUJOURS un dict (le premium ne plante pas, il écrit l'absence).
    r = plan_ortho(None, Path("/tmp"))
    assert isinstance(r, dict) and "ok" in r and "echec" in r
