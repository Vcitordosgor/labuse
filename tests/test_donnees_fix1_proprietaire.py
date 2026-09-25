"""DONNEES-FIX-1 lot B — plus de faux changements de propriétaire (pseudo-siren « U… »).

Règle UNIQUE `changements_millesimes` (proprietaire_historique.py) lue par la fiche §Identité ET la
frise « Remonter le temps ». Un changement n'est affirmé que si les deux SIREN sont réels et
différents ; sinon « non identifiable ». Témoins réels de l'audit DONNEES-LIDAR-PROPRIO.
"""
from labuse.proprietaire_historique import siren_reel, changements_millesimes


def test_siren_reel():
    assert siren_reel("483339628") is True
    assert siren_reel("U23719996") is False   # pseudo-siren LABUSE
    assert siren_reel("u15960284") is False    # pseudo, casse indifférente
    assert siren_reel(None) is False
    assert siren_reel("") is False
    assert siren_reel("   ") is False


def _r(millesime, siren, denom):
    return {"millesime": millesime, "siren": siren, "denomination": denom}


def test_temoin_sci_laurent_grandpre():
    """NULL(2019) → U(2020) → réel 483339628 (2021-2025), dénomination qui oscille. AVANT : 2 faux
    « changements » (dont un SCI LAURENT GRANDPRE → SCI LAURENT GRANDPRE identique). APRÈS : 0 vrai
    changement, transitions marquées « non identifiable »."""
    rows = [
        _r(2019, None, "SCI LAURENT GRANDPRE"),
        _r(2020, "U23719996", "SCI LAURENT GRANDPRE"),
        _r(2021, "483339628", "LAURENT GRANDPRE"),
        _r(2022, "483339628", "LAURENT GRANDPRE"),
        _r(2023, "483339628", "LAURENT GRANDPRE"),
        _r(2024, "483339628", "SCI LAURENT GRANDPRE"),
        _r(2025, "483339628", "SCI LAURENT GRANDPRE"),
    ]
    ch = changements_millesimes(rows)
    reels = [c for c in ch if not c["non_identifiable"]]
    assert reels == []                                   # AUCUN vrai changement
    # la re-clé de dénomination 2023→2024 (SIREN réel inchangé) n'est PAS listée
    assert all(not (c["de_millesime"] == 2023) for c in ch)
    assert all(c["non_identifiable"] for c in ch)        # ce qui reste = non identifiable


def test_temoin_onf():
    """ONF : U(2019,2020) → réel 662043116 (2021+). AVANT : 1 faux changement 2020→2021. APRÈS : 0."""
    rows = [
        _r(2019, "U15960284", "OFFICE NATIONAL  DES FORETS"),
        _r(2020, "U15960284", "OFFICE NATIONAL  DES FORETS"),
        _r(2021, "662043116", "OFFICE NATIONAL DES FORETS"),
        _r(2022, "662043116", "OFFICE NATIONAL DES FORETS"),
    ]
    ch = changements_millesimes(rows)
    assert [c for c in ch if not c["non_identifiable"]] == []   # aucun vrai changement
    # 2019→2020 (U == U, dénom identique) n'est même pas listé ; 2020→2021 = non identifiable
    ids = [(c["de_millesime"], c["a_millesime"], c["non_identifiable"]) for c in ch]
    assert (2019, 2020, True) not in [(a, b, n) for a, b, n in ids]
    assert (2020, 2021, True) in ids


def test_vrai_changement_deux_siren_reels():
    """Deux SIREN réels DISTINCTS (DÉPARTEMENT 229740014 → COMMUNE 219740024) = VRAI changement."""
    rows = [
        _r(2019, "229740014", "DEPARTEMENT DE LA REUNION"),
        _r(2020, "219740024", "COMMUNE DE BRAS PANON"),
        _r(2021, "219740024", "COMMUNE DE BRAS PANON"),
    ]
    ch = changements_millesimes(rows)
    reels = [c for c in ch if not c["non_identifiable"]]
    assert len(reels) == 1
    assert reels[0]["de_millesime"] == 2019 and reels[0]["a_millesime"] == 2020
    assert reels[0]["siren_avant"] == "229740014" and reels[0]["siren_apres"] == "219740024"


def test_re_cle_denomination_siren_reel_inchange_pas_un_changement():
    """Même SIREN réel, dénomination reformatée → PAS un changement (ni réel ni non identifiable)."""
    rows = [
        _r(2019, "483339628", "SCI LAURENT GRANDPRE"),
        _r(2020, "483339628", "LAURENT GRANDPRE"),
    ]
    assert changements_millesimes(rows) == []
