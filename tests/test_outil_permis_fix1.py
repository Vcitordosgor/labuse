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


def test_fix2_defautC_dormant_exige_toutes_parcelles_mesurees():
    """OUTIL-PERMIS-FIX-2 (Défaut C) — « aucun bâtiment détecté sur LEURS parcelles » (toutes) : le
    prédicat exclut tout permis dont une parcelle est ABSENTE de la mesure (LEFT JOIN + `IS NULL`) ou
    bâtie. Avant, une parcelle absente de `parcels` était IGNORÉE (EXISTS trop faible) → bâti invisible."""
    d = pc._dormant_sql("s.", ":dmax")
    assert "LEFT JOIN parcel_bati_emprise" in d
    assert "_be.idu IS NULL" in d               # une parcelle NON mesurée disqualifie
    assert "jsonb_array_length(s.idu_codes) >= 1" in d
    assert "NOT EXISTS" in d and f">= {pc.BATI_SEUIL_M2}" in d
    # plus de JOIN strict « au moins une parcelle mesurée » (qui ignorait les absentes) : seul le LEFT JOIN
    assert "JOIN parcel_bati_emprise _be ON _be.idu = _c.idu)" not in d


def test_fix2_defautA_signal_peremption_viabilisation():
    """OUTIL-PERMIS-FIX-2 (Défaut A) — la fonction de fraîcheur existe et le signal est câblé (fiche +
    readyz) : parcel_viabilisation ne peut plus être plus vieux que via_permits_geo sans être signalé."""
    from labuse.faisabilite import viabilisation_build as vb
    assert hasattr(vb, "viabilisation_fraicheur") and hasattr(vb, "ensure_via_permits_geo")
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert "viabilisation_fraicheur" in app and "perimee" in app


def test_fix2_G2_garde_fraicheur_bati():
    """OUTIL-PERMIS-FIX-2 (G2) — la couche `parcel_bati_emprise` (qui fonde « aucun bâtiment détecté »)
    a un garde-fou de fraîcheur, comme la viabilisation : `bati_emprise_fraicheur()` existe, sa date est
    servie dans la partition (pour le « i » des dormants), et `/readyz` la signale."""
    from labuse.faisabilite import viabilisation_build as vb
    assert hasattr(vb, "bati_emprise_fraicheur")
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    mods = (root / "src/labuse/api/modules.py").read_text(encoding="utf-8")
    assert "bati_fraicheur" in mods and "bati_emprise_fraicheur" in mods   # servie dans la partition
    app = (root / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert "bati_emprise" in app and "bati_emprise_fraicheur" in app       # signalée dans /readyz
    mp = (root / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
    assert "bati_fraicheur" in mp and "bâti mesuré le" in mp               # date dans le « i » des dormants


def test_fix2_G3_libelle_fiche_commune_mesure_bati():
    """OUTIL-PERMIS-FIX-2 (G3) — la source du bloc dormant de la fiche commune ne dit plus « run servi »
    (ancien proxy) mais ce qui est MESURÉ (bâti)."""
    from pathlib import Path
    fc = (Path(__file__).resolve().parents[1] / "src/labuse/api/fiche_commune.py").read_text(encoding="utf-8")
    # l'ancienne formulation « (36 mois sans DAACT, run servi) » du bloc dormant a disparu…
    assert "36 mois sans DAACT, run servi" not in fc
    # …remplacée par ce qui est MESURÉ (le « run servi » résiduel ligne ~395 est un autre bloc, Densifier).
    assert "permis dormants (PC > 3 ans sans DAACT, aucun bâtiment détecté sur leurs parcelles)" in fc


def test_fix2_defautD_F_libelles():
    """OUTIL-PERMIS-FIX-2 (Défauts D & F) — « Permis déposés, 12 mois » → « autorisés » (AnalyserAnnonce) ;
    le marqueur millésime figé « 2026-07 » de sitadel/via_permits_geo disparaît (couche suivie par trigger)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    aa = (root / "frontend/src/components/outils/AnalyserAnnonce.tsx").read_text(encoding="utf-8")
    assert "Permis autorisés, 12 mois" in aa and "Permis déposés, 12 mois" not in aa
    tb = (root / "src/labuse/registre/tables.py").read_text(encoding="utf-8")
    assert 'millesime="2026-07"' not in tb


# ─────────────────── OUTIL-PERMIS-FIX-3 (relecteur externe sur 2fc4636f9) ───────────────────

def test_fix3_point1_rayon_dossier_present():
    """Point 1 — le compte `dynamique` du Dossier (nearby_permits) GARDE le RAYON (ST_DWithin) ET
    l'exclusion des dates nulles. Garde NON-DB (le vrai test spatial est db-marqué, hors hook — c'est
    justement pourquoi la régression du mandat 1 n'a pas été vue : aucun test non-db ne couvrait le rayon)."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/labuse/ingestion/permits.py").read_text(encoding="utf-8")
    # la sous-requête de dynamique (fenêtre now()-mois) doit porter le rayon ET l'exclusion des dates nulles
    import re
    dyn = src[src.index("Dynamique de secteur"):]
    dyn = dyn[:dyn.index("niveau =")]
    assert "ST_DWithin" in dyn, "le RAYON a disparu du compte de dynamique (régression Dossier)"
    assert ":r" in dyn and "s.date IS NOT NULL" in dyn


def test_fix3_point2_promesses_lit_fonction_unique_et_clampe():
    """Point 2 — la liste /promesses lit la DÉFINITION UNIQUE et l'affinage ne peut que RESTREINDRE les
    854 (seuil d'âge clampé ≥ 36 mois), côté liste ET compteur ; le front n'offre plus « 24 »."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    mods = (root / "src/labuse/api/modules.py").read_text(encoding="utf-8")
    assert "permis_classe._dormant_sql" in mods          # la liste lit la fonction unique
    assert "max(int(months), permis_classe.DORMANT_MOIS)" in mods   # clamp côté liste
    cm = (root / "src/labuse/registre/moteurs/commune.py").read_text(encoding="utf-8")
    assert "max(int(months), permis_classe.DORMANT_MOIS)" in cm     # clamp côté compteur (point_mort)
    mp = (root / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
    assert "MONTHS_PM = [36, 48, 60, 72]" in mp           # plus de « 24 » (< plancher)


def test_fix3_point3_delais_vivants_et_fiche_coherente():
    """Point 3 — la couche des délais est MAINTENUE PAR TRIGGER (dérivée de sitadel_permits) et la fiche
    n'affiche un délai que s'il est COHÉRENT avec le dépôt ET l'autorisation montrés (source unique)."""
    from labuse.ingestion import permit_delais_m10 as m10
    assert hasattr(m10, "ensure_delais_vivants") and "m10_permit_delais_sync" in m10._M10_TRIGGER_FN
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    mods = (root / "src/labuse/api/modules.py").read_text(encoding="utf-8")
    assert "delai_coherent" in mods                       # garde de cohérence dans la fiche
    assert "s.date_depot::date::text AS date_depot" in mods   # dépôt depuis Sitadel (source unique)
    sdes = (root / "src/labuse/ingestion/permits_sdes.py").read_text(encoding="utf-8")
    assert "ensure_delais_vivants" in sdes                # la ré-ingestion rafraîchit la couche
