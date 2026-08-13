"""M73 §1 — arbitrage & libellés client des lignes de risque servies (fonction pure)."""
from labuse.api.risques_arbitrage import arbitrer_risques, libelle_client_detail


def _l(result, detail, weight=0):
    return {"layer": "risques", "result": result, "severity": "moyen", "weight": weight, "detail": detail}


def test_alea_un_seul_niveau_le_plus_contraignant():
    lines = [_l("SOFT_FLAG", "Aléa mouvement_terrain — niveau faible."),
             _l("SOFT_FLAG", "Aléa mouvement_terrain — niveau moyen."),
             _l("SOFT_FLAG", "Aléa inondation — niveau fort.")]
    out = arbitrer_risques(lines)
    details = [l["detail"] for l in out]
    # un seul aléa mouvement de terrain, le plus contraignant (moyen), jamais « faible » à côté
    assert "Aléa mouvement de terrain — niveau moyen." in details
    assert not any("faible" in d for d in details)
    assert "Aléa inondation — niveau fort." in details        # autre type conservé
    assert len(out) == 2


def test_alea_eleve_accentue_et_retient():
    lines = [_l("SOFT_FLAG", "Aléa mouvement_terrain — niveau moyen."),
             _l("SOFT_FLAG", "Aléa mouvement_terrain — niveau eleve.")]
    out = arbitrer_risques(lines)
    assert len(out) == 1
    assert out[0]["detail"] == "Aléa mouvement de terrain — niveau élevé."


def test_ppr_reglementaire_prime_sur_geometrique():
    lines = [_l("HARD_EXCLUDE", "Exclue : PPR zone rouge (inconstructible)."),
             _l("SOFT_FLAG", "Périmètre PPR INONDATION_MOUVEMENT_DE_TERRAIN (~7% de la parcelle) — "
                             "intersection marginale (< 10 %) : à vérifier au règlement.")]
    out = arbitrer_risques(lines)
    details = [l["detail"] for l in out]
    # le régime réglementaire reste, l'intersection géométrique marginale disparaît
    assert any("PPR zone rouge (inconstructible)" in d for d in details)
    assert not any("intersection marginale" in d for d in details)


def test_marginal_conserve_sans_regime_reglementaire():
    # sans HARD_EXCLUDE, la ligne marginale reste (honnête) mais son libellé est nettoyé
    lines = [_l("SOFT_FLAG", "Périmètre PPR INONDATION_MOUVEMENT_DE_TERRAIN — intersection marginale (< 10 %).")]
    out = arbitrer_risques(lines)
    assert len(out) == 1
    assert "INONDATION_MOUVEMENT_DE_TERRAIN" not in out[0]["detail"]
    assert "PPR inondation et mouvement de terrain" in out[0]["detail"]


def test_libelle_client_retire_id_technique_sup():
    d = libelle_client_detail("Servitude(s) d'utilité publique : PM1 (PM1_PPR_i_mvt_SAINT_BENOIT_gen2_ass). Suite.")
    assert "PM1_PPR_i_mvt" not in d
    assert "PM1. Suite." in d or "PM1 . Suite." in d.replace(".", ". ").replace("  ", " ")


def test_libelle_client_retire_nom_table():
    assert "parcel_residuel" not in libelle_client_detail("Droits hors couverture parcel_residuel.")
