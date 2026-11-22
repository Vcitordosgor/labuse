"""OUTIL-PERMIS-FIX-1 — tests UNITAIRES (sans base) de la définition unique des états et du correctif
d'ingestion. Les tests sur base (partition compteur=filtre, dormant mesuré, voisinage 200 m) vivent
dans test_retours16/17_permis et test_point_mort ; ici, la logique pure, rapide (lot pre-push)."""
from __future__ import annotations

from labuse import permis_classe as pc


def test_lot1_ordre_de_priorite_ecrit_dans_le_case():
    """L'ORDRE est écrit et vérifiable : Achevé AVANT Dormant AVANT Récent (le premier WHEN gagne).
    Un permis achevé (DAACT/code 6) est donc 'acheve' même récent → même état à toutes les échelles."""
    case = pc.etat_case_sql("", ":dmax")
    i_ach = case.index("'acheve'")
    i_dor = case.index("'dormant'")
    i_rec = case.index("'recent'")
    assert i_ach < i_dor < i_rec, "ordre de priorité rompu (achevé > dormant > récent)"
    # achevé = DAACT présente OU code 6 (île ET parcelle, plus de divergence de code)
    assert "daact' IS NOT NULL OR" in case and "'6'" in case
    # une seule horloge : la fenêtre récente est ancrée sur :dmax (fin des données), pas now()
    assert ":dmax - interval '24 months'" in case and "now()" not in case


def test_lot2_dormant_exclut_annules_commences_et_mesure_le_bati():
    """Le dormant EXCLUT les annulés (code 4) et les travaux commencés (code 5), exige l'absence de
    DAACT et l'âge > 3 ans, et MESURE le bâti (parcel_bati_emprise < seuil) — plus « absence d'exclusion
    au run ». Le libellé dit ce qui est mesuré, jamais « terrain nu »/« caducité »."""
    d = pc._dormant_sql("s.", ":dmax")
    assert "NOT IN ('4','5','6')" in d          # annulés + commencés + achevés hors dormants
    assert "raw->>'daact' IS NULL" in d          # sans achèvement déclaré
    assert f"interval '{pc.DORMANT_MOIS} months'" in d and pc.DORMANT_MOIS == 36
    assert "parcel_bati_emprise" in d and f">= {pc.BATI_SEUIL_M2}" in d and pc.BATI_SEUIL_M2 == 10
    assert "dryrun" not in d.lower()             # plus de proxy « absence d'exclusion au run »


def test_lot2_dormant_inactif_sans_couche_bati():
    """Sans la couche d'emprise bâtie (bati=False), le dormant vaut `false` : aucun dormant plutôt
    qu'un 500 ou un « terrain nu » non mesuré (garde des bases fraîches / de test)."""
    assert pc._dormant_sql("", ":dmax", bati=False) == "false"
    case = pc.etat_case_sql("", ":dmax", bati=False)
    assert "WHEN false THEN 'dormant'" in case
    assert "parcel_bati_emprise" not in case


def test_lot1_filtre_et_whitelist():
    """Le prédicat de FILTRE dérive du MÊME CASE que le compteur (→ compteur = lignes du filtre) ; une
    valeur d'état hors whitelist ne produit AUCUN filtre (pas d'injection)."""
    for etat in pc.ETATS:
        frag = pc.etat_pred_sql(etat, "s.", ":dmax")
        assert frag.startswith(" AND (") and f"= '{etat}'" in frag
    assert pc.etat_pred_sql("n_importe_quoi", "s.") == ""
    assert pc.etat_pred_sql(None, "s.") == ""


def test_lot4_refresh_correction_safe():
    """LOT 4 — le refresh mensuel est CORRECTION-SAFE : `refresh_since` renvoie None (re-charge le
    millésime complet), car le filtre serveur par date d'autorisation ratait les corrections SDES sur
    permis anciens (cas 97440925G0371 : 12/12/2025 → 16/02/2026). None = réconciliation pleine."""
    from labuse.ingestion.permits_sdes import refresh_since
    assert refresh_since(None) is None
