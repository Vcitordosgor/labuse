from labuse.api.modules import _plu_dates_gpu


def test_vote_zattes_source_et_reserve():
    actes = _plu_dates_gpu()["97423"]["modifications"]
    acte = next(a for a in actes if a["date"] == "2026-08-27")
    assert "Zattes" in acte["note"]
    assert "entrée en vigueur non établie" in acte["note"]
    assert acte["url"].endswith("27082026.pdf#page=2")


def test_la_possession_reference_publique():
    note = _plu_dates_gpu()["97408"]["note"]
    assert "97408_PLU_20260625" in note
    assert "OUTIL-PLU-FIX" not in note
