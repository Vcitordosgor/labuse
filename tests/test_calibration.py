"""Calibration web du bilan — le socle sourcé lève le bandeau « non fiable » DUR ; les valeurs
ESTIMÉES restent signalées « à affiner ». Le socle respecte les overrides de Vic (idempotent).
"""
from __future__ import annotations

import pytest

from labuse.faisabilite import bilan_calibration as cal
from labuse.faisabilite import bilan_params as bp

pytestmark = pytest.mark.db


def test_socle_calibre_les_critiques_et_signale_les_estimes(db_session):
    r = bp.resolve(db_session, None)              # global '*' — socle injecté au boot (ensure_bilan_params)
    # Coût de construction : PLUS d'override global (mandat hypothèses bilan, Vic 28/07/2026) —
    # défaut registre 0 = repli fourchette YAML auditée dans compute_bilan ; pas de bandeau DUR.
    assert r["cout_construction_m2_sdp"]["value"] == 0.0
    assert r["cout_construction_m2_sdp"]["source"] == "défaut"
    assert r["cout_construction_m2_sdp"]["is_placeholder"] is False
    assert bp.uncalibrated_critical(r) == []
    # Prix neuf : PLUS de socle global 4900 (mandat calibration estimées, Vic 28/07/2026 —
    # back-test contre le réel). Le défaut registre 0 signifie « résolution par commune via
    # dvf_prix_sortie_neuf (préséance), ou non calculable » — jamais un socle saint-paulois servi
    # à toute l'île. Un override de BASSIN sourcé (secteur ≠ '*') survit, lui (cf. test suivant).
    assert r["prix_m2_neuf"]["provenance"] is None and r["prix_m2_neuf"]["value"] == 0.0
    assert r["prix_m2_neuf"]["source"] == "défaut"
    # marge = ESTIMÉE → sous-bandeau « à affiner » ET placeholder (une estimée non confirmée
    # reste visible — verrou anti-« provisoire devenu permanent »).
    assert r["marge_cible_pct"]["provenance"] == "estimee"
    assert r["marge_cible_pct"]["is_placeholder"] is True
    aff = " ".join(bp.estimated_to_refine(r))
    assert "Marge cible promoteur" in aff


def test_prix_neuf_ventile_par_secteur(db_session):
    """Recette ventilation : les 5 overrides de bassin sont DÉMOTÉS en `estimee` (is_placeholder,
    HORS préséance) — mandat prix sortie consommateurs (Vic 28/07/2026) : observatoire de l'existant
    non confirmé DVF neuf → ne prime jamais sur la médiane communale DVF. `resolve_prix_neuf_marche`
    n'honore que `sourcee` : ces bassins ne priment plus. Pas de socle 4900. Défaut registre 0."""
    sg = bp.resolve(db_session, "Saint-Gilles")["prix_m2_neuf"]
    assert sg["value"] == 5800.0 and sg["provenance"] == "estimee" and sg["is_placeholder"] is True
    gui = bp.resolve(db_session, "Le Guillaume")["prix_m2_neuf"]
    assert gui["value"] == 3900.0 and gui["provenance"] == "estimee"   # Hauts — fragile, déjà placeholder
    unc = bp.resolve(db_session, "Secteur Inexistant")["prix_m2_neuf"]
    assert unc["value"] == 0.0 and unc["source"] == "défaut"           # plus de socle commun 4900


def test_socle_prix_neuf_retire_du_seed():
    """VERROU (mandat calibration estimées, Vic 28/07/2026) : le socle global `prix_m2_neuf`
    4900 n'est PLUS au seed (sinon ré-injecté au boot — piège du 2100). Les 5 overrides de bassin
    sont DÉMOTÉS en `estimee` (mandat prix sortie consommateurs) : observatoire non confirmé DVF →
    hors préséance. AUCUN bassin ne reste `sourcee`."""
    assert "prix_m2_neuf" not in cal.CALIBRATION
    assert cal.SECTEUR_PRIX_NEUF["Saint-Gilles"] == (5800.0, "estimee")
    assert all(prov == "estimee" for _v, prov in cal.SECTEUR_PRIX_NEUF.values())


def test_motif_non_calculable_formulations():
    """VERROU des formulations produit imposées (Vic) — au mot près. Depuis le repli île (mandat
    couverture prix), SEULES les communes social-dominantes sont non calculables ; les communes de
    marché sans local reçoivent le repli île (cf. test_repli_ile_preseance_et_etiquettes)."""
    from labuse.ingestion.dvf_prix_neuf import motif_non_calculable, SOCIAL_DOMINANT_INSEE
    assert "97407" in SOCIAL_DOMINANT_INSEE                      # Le Port (social 96 %)
    assert motif_non_calculable("97407") == (
        "Charge foncière de marché non atteignable sur cette commune — le collectif y est "
        "majoritairement social ou aidé.")


def test_repli_ile_preseance_et_etiquettes():
    """VERROU (mandat couverture prix, Vic 28/07/2026) : partition des 24 communes en 4 niveaux de
    confiance + étiquettes au mot près. Le repli île ne touche JAMAIS les social-dominantes."""
    from labuse.ingestion import dvf_prix_neuf as dp
    couvertes = {"97411", "97416", "97415", "97413", "97422"}
    # partition exhaustive et disjointe des 24 communes
    assert len(dp.ILE_VALIDEES_INSEE) == 9 and len(dp.ILE_SANS_OPERATION_INSEE) == 2
    assert len(dp.SOCIAL_DOMINANT_INSEE) == 8
    tous = couvertes | dp.ILE_VALIDEES_INSEE | dp.ILE_SANS_OPERATION_INSEE | dp.SOCIAL_DOMINANT_INSEE
    assert len(tous) == 24                                       # partition sans recouvrement
    assert not (dp.ILE_VALIDEES_INSEE & dp.SOCIAL_DOMINANT_INSEE)   # jamais île sur une social-dom.
    assert not (dp.ILE_SANS_OPERATION_INSEE & dp.SOCIAL_DOMINANT_INSEE)
    # étiquettes à 4 niveaux (au mot près)
    assert dp.niveau_prix_label("commune", 54) == "Estimé — médiane locale, 54 ventes"
    assert dp.niveau_prix_label("ile_validee") == "Estimé — estimation île, ± 12 %, validée sur cette commune"
    assert dp.niveau_prix_label("ile_sans_operation") == (
        "Estimé — estimation île, aucune opération de marché observée sur cette commune")


def test_boot_purge_socle_4900_idempotente(db_session):
    """VERROU : la purge de boot retire un socle 4900 système ré-injecté ; un override saisi survit."""
    from sqlalchemy import text
    # simulate un socle système ré-injecté + un override Vic sur un bassin
    db_session.execute(text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance) "
                            "VALUES ('*','prix_m2_neuf',4900,false,'sourcee') ON CONFLICT (secteur,param) "
                            "DO UPDATE SET value=4900, provenance='sourcee'"))
    db_session.execute(text("DELETE FROM bilan_params WHERE secteur='*' AND param='prix_m2_neuf' "
                            "AND provenance='sourcee' AND value=4900"))  # = purge de ensure_bilan_params
    r = bp.resolve(db_session, None)["prix_m2_neuf"]
    assert r["value"] == 0.0 and r["source"] == "défaut"        # socle système purgé


def test_socle_respecte_les_overrides_de_vic(db_session):
    """Un override saisi par Vic survit à une ré-injection du socle (ON CONFLICT DO NOTHING)."""
    bp.save(db_session, "*", "cout_construction_m2_sdp", 2400.0)   # Vic calibre
    cal.seed(db_session)                                           # ré-injection du socle
    r = bp.resolve(db_session, None)
    assert r["cout_construction_m2_sdp"]["value"] == 2400.0        # l'override prime, jamais écrasé
