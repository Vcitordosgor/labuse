"""SCORING-8 lot A bis (2) — C26 (arbitrage Vic) : une SDP résiduelle INCONNUE (non calculée)
n'est jamais lue comme 0 dans l'éligibilité du classement.

  · sdp = NULL  → NC « Analyse incomplète » (motif « capacité résiduelle non calculée »).
  · sdp = 0     → bande « 0 / Non retenue » (vrai zéro produit par le moteur) — INCHANGÉ.

Le filet est CAUSE-INDÉPENDANT : une SDP NULL tombe en NC même si sa cause n'est pas un motif
NC connu (cas possible à q_v16 : exception PLU non modélisée, trou de donnée).
"""
from labuse.scoring.score_labuse import (NC_SDP, ScoreEntrees, charger_bareme,
                                         libelle_client_bande, score_parcelle)

BAREME, VERSION = charger_bareme()


def _e(**kw) -> ScoreEntrees:
    base = dict(parcel_id=1, idu="x", commune="Saint-Paul", residuel_present=True,
                sdp_residuelle_m2=1000.0, taux_emprise_pct=0.0, cause=None,
                capacite_estimee=False, pente_moy_deg=3.0, aire_m2=1000.0,
                perimetre_m=130.0, faitage_m=None, au_classe=None, acces="POSITIVE")
    base.update(kw)
    return ScoreEntrees(**base)


def _s(**kw):
    return score_parcelle(_e(**kw), BAREME, VERSION, "test")


def test_sdp_inconnue_devient_nc_jamais_zero():
    # SDP NULL, SANS cause NC connue → NC, pas bande 0.
    r = _s(sdp_residuelle_m2=None, cause=None)
    assert r.non_calculable and r.score is None
    assert r.bande == "NC" and r.cause == NC_SDP
    assert r.bande != "0"
    lib = libelle_client_bande(r.bande, BAREME, r.cause)
    assert lib.startswith("Analyse incomplète")
    assert "Non retenue" not in lib


def test_sdp_inconnue_meme_avec_cause_non_nc():
    # Une cause quelconque non-NC (ex. un libellé futur) ne doit pas faire retomber en bande 0.
    r = _s(sdp_residuelle_m2=None, cause="motif_inconnu_q_v16")
    assert r.non_calculable and r.bande == "NC" and r.cause == NC_SDP


def test_sdp_zero_connue_reste_non_retenue():
    # Vrai zéro produit par le moteur (terrain exigu, zone inconstructible…) → bande 0, PAS NC.
    r = _s(sdp_residuelle_m2=0.0, cause="terrain_exigu")
    assert not r.non_calculable and r.score == 0 and r.bande == "0"
    assert libelle_client_bande(r.bande, BAREME) == "Non retenue"


def test_hors_plu_garde_son_motif_zone():
    # hors_plu (SDP NULL) garde le motif le plus informatif « zone non résolue », pas NC_SDP.
    r = _s(sdp_residuelle_m2=None, cause="hors_plu")
    assert r.non_calculable and r.bande == "NC" and r.cause == "zone non résolue"
