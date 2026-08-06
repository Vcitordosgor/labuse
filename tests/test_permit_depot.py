"""M38 — capture de la date de DÉPÔT Sitadel (DR_DEPOT) : validation, sans DB.

Le validateur `_date_depot` suit la même discipline que la date d'autorisation (correctif
Vic 04/08) : invalide/future → None, valeur brute tracée, compteur bruyant. On n'invente
jamais une date ; on refuse d'en servir une fausse.
"""
from __future__ import annotations

from datetime import datetime, timezone

from labuse.ingestion.permits_sdes import _date_depot


def _stats() -> dict:
    return {"depots_futurs": 0, "depots_invalides": 0}


def test_date_depot_valide():
    raw, st = {}, _stats()
    assert _date_depot({"DR_DEPOT": "2025-09-22"}, raw, st) == "2025-09-22"
    assert st == {"depots_futurs": 0, "depots_invalides": 0} and "date_depot_brute" not in raw


def test_date_depot_absente():
    raw, st = {}, _stats()
    assert _date_depot({"DR_DEPOT": ""}, raw, st) is None
    assert _date_depot({}, raw, st) is None


def test_date_depot_invalide_tracee_et_comptee():
    raw, st = {}, _stats()
    assert _date_depot({"DR_DEPOT": "pas-une-date"}, raw, st) is None
    assert st["depots_invalides"] == 1 and raw["date_depot_brute"] == "pas-une-date"


def test_date_depot_future_refusee():
    raw, st = {}, _stats()
    futur = str(datetime.now(timezone.utc).date().replace(year=datetime.now().year + 2))
    assert _date_depot({"DR_DEPOT": futur}, raw, st) is None
    assert st["depots_futurs"] == 1 and raw["date_depot_brute"] == futur
