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


def test_fix8_lot3_m10_decommissionnee_ne_nourrit_plus_rien():
    """OUTIL-PERMIS-FIX-8 (LOT 3) — la couche des délais `m10_permit_delais` est DÉCOMMISSIONNÉE : elle
    ne nourrit plus aucun calcul ni écran. La ré-ingestion ne la reconstruit plus ni ne (ré)installe son
    trigger (`ensure_delais_vivants` n'y est plus appelée), le build hebdo est retiré, et le comparateur
    ne lit plus m10 (plus de CTE `velo` ni de lecture de la table dans le SQL des indicateurs)."""
    sdes = _src("src/labuse/ingestion/permits_sdes.py")
    assert "ensure_delais_vivants" not in sdes            # la ré-ingestion ne maintient plus m10
    fra = _src("src/labuse/ingestion/fraicheur.py")
    assert "build_delais" not in fra                      # plus de build hebdo de m10
    commune = _src("src/labuse/registre/moteurs/commune.py")
    assert "FROM m10_permit_delais" not in commune        # le comparateur ne LIT plus m10
    assert "velo AS (" not in commune                     # la CTE de délai médian est supprimée
    assert "velocite" not in _src("src/labuse/registre/moteurs/commune.py").split("INDICATEURS = {")[1].split("}")[0]


def test_fix4_point2_depot_depuis_an_depot_pas_dr_depot():
    """OUTIL-PERMIS-FIX-4 (Point 2) — le DÉPÔT de la couche des délais vient de AN_DEPOT (année), PAS de
    DR_DEPOT (corrompu = date d'autorisation / postérieur à 62,6 %). L'ingestion stocke `an_depot`."""
    from labuse.ingestion import permit_delais_m10 as m10
    # le SQL de la couche dérive le dépôt de raw->>'an_depot' (01-01), plus de s.date_depot (DR_DEPOT)
    assert "an_depot" in m10._M10_ROW_SQL and "-01-01" in m10._M10_DEPOT_SQL
    assert "s.date_depot" not in m10._M10_ROW_SQL          # DR_DEPOT (date_depot) n'alimente plus le délai
    from pathlib import Path
    sdes = (Path(__file__).resolve().parents[1] / "src/labuse/ingestion/permits_sdes.py").read_text(encoding="utf-8")
    assert '"an_depot"' in sdes and "AN_DEPOT" in sdes     # l'ingestion stocke l'année de dépôt


def test_fix4_point4_fiche_depot_precis_via_fonction_unique():
    """OUTIL-PERMIS-FIX-4 puis FIX-8 (LOT 1) — la fiche n'affiche le dépôt QUE s'il est une DATE PRÉCISE
    fiable (antérieure à l'autorisation, non un 1er janvier, année = AN_DEPOT). La règle est désormais
    PORTÉE par la fonction UNIQUE `permis_classe.depot_affichable_*` (plus de littéral inline dans la
    fiche) ; la fiche l'appelle. OUTIL-PERMIS-FIX-8 (LOT 2) — plus AUCUN délai calculé."""
    from labuse import permis_classe as pc
    cond = pc.depot_affichable_cond_sql("s.")
    assert "s.date_depot < s.date" in cond                 # strictement antérieur
    assert "EXTRACT(MONTH FROM s.date_depot) = 1 AND EXTRACT(DAY FROM s.date_depot) = 1" in cond  # proxy 01-01 exclu
    # version Python : même règle, renvoie None si l'année contredit AN_DEPOT (témoin 97441626E0304)
    assert pc.depot_affichable("2020-06-01", "2026-08-03", "2026") is None
    assert str(pc.depot_affichable("2024-09-24", "2026-03-19", "2024")) == "2024-09-24"
    from pathlib import Path
    mods = (Path(__file__).resolve().parents[1] / "src/labuse/api/modules.py").read_text(encoding="utf-8")
    assert "permis_classe.depot_affichable_sql" in mods    # la fiche appelle la fonction unique
    assert "delai_coherent" not in mods and "delai_mois" not in mods   # plus aucune durée calculée
    assert '"delai_instruction"' not in mods               # plus de clé délai servie


def _src(rel: str) -> str:
    from pathlib import Path
    return (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")


def test_fix8_lot3_axe_delai_sorti_du_composite():
    """OUTIL-PERMIS-FIX-8 (LOT 3) — l'axe vélocité (délai) SORT du score composite (FIX-5 l'avait
    seulement caché en le laissant peser 0,15 ; le contre-audit ASTRA-4 le refuse au classement).
    Plus d'indicateur `velocite`, plus de poids `w_velocite` à l'endpoint."""
    import inspect
    from labuse.registre.moteurs.commune import INDICATEURS
    from labuse.api import comparateur
    assert "velocite" not in INDICATEURS                   # l'axe n'est plus un indicateur du composite
    assert "w_velocite" not in inspect.signature(comparateur.comparateur_communes).parameters


def test_fix8_lot3_poids_restants_renormalises_et_formule_dit():
    """OUTIL-PERMIS-FIX-8 (LOT 3) — les CINQ poids restants sont renormalisés (somme = 1) et la méthode
    affichée dit ce qu'elle contient (cinq axes, délai retiré)."""
    cmp = _src("src/labuse/api/comparateur.py")
    assert 'r.pop("velocite"' not in cmp                   # plus de velocite à retirer (supprimée en amont)
    assert "poids_norm" in cmp and "renormalis" in cmp.lower()
    # la méthode servie nomme les cinq axes et dit que le délai est retiré
    assert "CINQ axes" in cmp and "vélocité) est RETIRÉ" in cmp and "somme = 1" in cmp


def test_fix5_point2_delai_median_retire_de_la_fiche_commune():
    """OUTIL-PERMIS-FIX-5 (Point 2) — `delai_median_mois` n'est plus une clé servie par la fiche commune
    (ni bloc comparable, ni carte « Permis et rythme »)."""
    fc = _src("src/labuse/api/fiche_commune.py")
    assert '"delai_median_mois":' not in fc                # plus aucune clé de dict servie


def test_fix5_point2_copilote_ne_sert_plus_le_delai():
    """OUTIL-PERMIS-FIX-5 (Point 2) — l'outil Copilote `delais_instruction` est retiré (registre +
    catalogue + schéma) : le Copilote ne sert plus de chiffre de délai."""
    from labuse.copilote_v2 import outils
    from labuse.copilote_v2 import answering
    assert "delais_instruction" not in outils.OUTILS
    assert "delais_instruction" not in answering._ARG_SPEC
    assert not any(t["nom"] == "delais_instruction" for t in answering.CATALOGUE)


def test_fix5_point2_registre_coherent_velocite_en_attente_sans_robinet():
    """OUTIL-PERMIS-FIX-5 (Point 2) — le chiffre `velocite_delai_median_mois` est `en_attente` (entrée
    interne du composite) et servi par AUCUN robinet ; le registre reste cohérent."""
    from labuse import registre
    assert registre.verifier() == []                       # invariant global tenu
    d = registre.CHIFFRES["velocite_delai_median_mois"]
    assert d.en_attente                                    # déclaré, servi par aucun robinet
    servi = any("velocite_delai_median_mois" in r.chiffres for r in registre.ROBINETS.values())
    assert not servi                                       # plus aucun robinet ne le sert
    assert "copilote_delais_instruction" not in registre.ROBINETS


def test_fix5_point2_front_colonne_et_outil_velocite_retires():
    """OUTIL-PERMIS-FIX-5 (Point 2) — front : colonne « Instruction » du comparateur retirée, composant
    M05 (outil Vélocité) supprimé, helper `modVelocite` supprimé (plus aucun écran n'appelle le délai)."""
    assert "k: 'velocite'" not in _src("frontend/src/components/outils/blocB.tsx")
    assert "export function M05" not in _src("frontend/src/components/outils/ModulePanel.tsx")
    assert "export const modVelocite" not in _src("frontend/src/lib/api.ts")


def test_fix6_point1_liste_permis_sans_depot_ni_delai():
    """OUTIL-PERMIS-FIX-6 (Point 1) — la LISTE /modules/permis ne sert plus le dépôt (1er janvier) ni le
    délai : plus de jointure m10 ni de colonnes `depot`/`delai_mois` (front : plus de « N m » par ligne)."""
    mods = _src("src/labuse/api/modules.py")
    liste = mods[mods.index('@router.get("/permis")'):mods.index('@router.get("/permis/{permit_id}")')]
    assert "m10_permit_delais" not in liste                # plus de jointure m10 dans la liste
    assert "AS depot" not in liste and "delai_mois" not in liste
    assert "i['delai_mois']" not in _src("frontend/src/components/outils/ModulePanel.tsx")


def test_fix6_point1_fiche_depot_exige_annee_an_depot():
    """OUTIL-PERMIS-FIX-6 puis FIX-8 (LOT 1) — une date de dépôt n'est affichable QUE si son année est
    celle déclarée par Sitadel (AN_DEPOT). La règle vit dans la fonction UNIQUE `permis_classe`
    (ex. 97441626E0304 : dépôt 01/06/2020, AN_DEPOT 2026 → écarté)."""
    from labuse import permis_classe as pc
    cond = pc.depot_affichable_cond_sql("s.")
    assert "EXTRACT(YEAR FROM s.date_depot)::int = (s.raw->>'an_depot')::int" in cond
    assert "s.raw->>'an_depot' ~ '^[0-9]{4}$'" in cond


def test_fix6_point2_endpoint_velocite_supprime():
    """OUTIL-PERMIS-FIX-6 (Point 2) — l'endpoint /modules/velocite est SUPPRIMÉ (aucun lecteur)."""
    mods = _src("src/labuse/api/modules.py")
    assert '@router.get("/velocite")' not in mods and "def velocite(" not in mods


def test_fix6_point2_bilan_repere_sitadel_retire():
    """OUTIL-PERMIS-FIX-6 (Point 2) — le repère Bilan « Sitadel : N mois dépôt → PC » est retiré (back +
    catalogue + front), le `defaut: 6` du calendrier est conservé (aucun total ne bouge)."""
    reperes_src = _src("src/labuse/bilan/reperes.py")
    assert "def _sitadel" not in reperes_src               # la fonction du repère est supprimée
    assert 'out["sitadel"] = ' not in reperes_src          # plus d'assignation de la clé
    assert "mois dépôt → PC" not in reperes_src            # plus le libellé « Sitadel : N mois dépôt → PC »
    # catalogue : obtention_pc garde defaut:6 mais plus de repère sitadel
    from labuse.bilan.catalogue import charger_catalogue
    cat = charger_catalogue()
    ob = next(c for c in cat.calendrier if c["id"] == "obtention_pc")
    assert ob.get("defaut") == 6 and not ob.get("repere")
    # front : plus de bouton repère au calendrier (le code conditionnel `c.repere === 'sitadel'` a disparu)
    bilan_tsx = _src("frontend/src/components/fiche/BilanEcran.tsx")
    assert "c.repere === 'sitadel'" not in bilan_tsx
    assert "sitadel.valeur" not in bilan_tsx


def test_fix6_point3_dossier_ligne_permis_honnete():
    """OUTIL-PERMIS-FIX-6 (Point 3) — la ligne « permis à 500 m » du Dossier (exports : extracteur
    n_permis_proximite + miroir) RESTITUE le zéro (0/0 jamais masqué), donne les logements DÉCLARÉS et
    signale les permis sans nombre de logements. (Chaîne : nearby_permits → _c_permis → _r_permis_proximite.)"""
    # 1) nearby_permits remonte les permis SANS nombre de logements
    assert "permis_sans_logements" in _src("src/labuse/ingestion/permits.py")
    # 2) l'extracteur du Dossier ne masque plus le zéro (plus de `if n else None`) et porte logements+réserve
    rf = _src("src/labuse/exports/robinet_fiche.py")
    extr = rf[rf.index('@extracteur("n_permis_proximite")'):rf.index('@extracteur("tier_opportunite")')]
    assert "if n is None:" in extr and '"logements":' in extr and '"sans_logements":' in extr
    assert "if n else None" not in extr                  # le zéro n'est plus masqué
    # 3) le miroir rend logements déclarés + la réserve « sans nombre de logements »
    mir = _src("src/labuse/exports/miroir.py")
    assert "sans nombre de logements" in mir and "logement" in mir


def test_fix7_point1_2_descriptions_portage_corrigees():
    """OUTIL-PERMIS-FIX-7 (Points 1-2) — les descriptions périmées du pré-remplissage du portage par le
    délai d'instruction sont corrigées (catalogue + provenance) : plus de « délai médian + 20 mois »."""
    don = _src("src/labuse/registre/donnees.py")
    i = don.index('"duree_portage_saisi_mois"')
    bloc = don[i:i + 600]
    assert "pré-remplie par le délai" not in bloc and "20 mois" not in bloc
    assert "saisie client" in bloc
    prov = _src("src/labuse/exports/provenance.py")
    assert "9 mois + 20 mois de chantier" not in prov or "retiré" in prov  # l'ex. périmé n'est plus donné tel quel


def test_fix7_point3_dossier_exclut_annules_via_permis_classe():
    """OUTIL-PERMIS-FIX-7 (Point 3) — les permis ANNULÉS sortent du compte « à proximité » du Dossier et
    sont dits à part, via la règle d'état UNIQUE (permis_classe.annule_sql), pas une nouvelle règle."""
    from labuse import permis_classe
    assert hasattr(permis_classe, "annule_sql")
    assert permis_classe.annule_sql("s.") == "s.raw->>'etat' = '4'"   # ETAT_DAU=4, règle unique
    perm = _src("src/labuse/ingestion/permits.py")
    assert "permis_classe.annule_sql" in perm                 # nearby_permits réutilise la règle
    assert '"permis_annules"' in perm                         # annulés comptés à part
    rf = _src("src/labuse/exports/robinet_fiche.py")
    assert '"annules":' in rf                                 # l'extracteur porte le nombre d'annulés
    mir = _src("src/labuse/exports/miroir.py")
    # OUTIL-PERMIS-FIX-8 (LOT 4) — libellé revu : « N permis retenus · M autres permis annulés, exclus »
    assert "permis retenus" in mir or "retenu" in mir         # le compte retenu est nommé
    assert "annulé" in mir and "exclu" in mir                 # annulés dits à part, exclus (plus « non comptés »)
