"""M2 — panel millésimes DGFiP PM : parsing pur (formats 2021-2023 vs 2024-2025)."""
from __future__ import annotations

import pytest

from labuse.ingestion.pm_millesimes import (_build_idu, _est_974, _sniff_header,
                                            MILLESIME_ATTACHMENTS, url_millesime)


def test_est_974_les_deux_formats():
    assert _est_974(["974", "4", "401"])            # 2024-2025 : département complet
    assert _est_974(["97", "4", "401"])             # 2021-2023 : 97 + direction 4
    assert not _est_974(["97", "2", "401"])         # 972 (Martinique) éclaté → exclu
    assert not _est_974(["973", "", "401"])


def test_build_idu_zfill():
    assert _build_idu("97401", "", "AK", "785") == "97401000AK0785"
    assert _build_idu("97415", "10", "B", "1") == "97415010" + "0B" + "0001"
    assert _build_idu("97401", "", "", "785") is None


def test_sniff_header_leve_sur_schema_divergent():
    with pytest.raises(RuntimeError, match="colonnes"):
        _sniff_header("a;b;c\n", 2021)
    assert len(_sniff_header(";".join(f"c{i}" for i in range(24)) + "\n", 2021)) == 24


def test_les_six_millesimes_sont_adresses():
    # 2019-2020 ajoutés par M3.5 lot A (panel 7 points 01/01/2019 → 01/01/2025)
    assert sorted(MILLESIME_ATTACHMENTS) == [2019, 2020, 2021, 2022, 2023, 2024]
    for a in MILLESIME_ATTACHMENTS.values():
        assert "parcelles" in a and a.endswith("zip")
    assert url_millesime(2024).startswith("https://data.economie.gouv.fr/")
