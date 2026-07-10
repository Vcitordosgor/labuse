"""Score V (Vendabilité) — barème v1 VERROUILLÉ (mandat SPEC-LABUSE-SCORE-V, décision D1).

V = max(0, min(100, A + B + C + D + E + malus)).
Familles A, B, C, E : MAX intra-famille. Famille D : SOMME plafonnée. Les poids sont des
HYPOTHÈSES — le backtest (Phase 5) jugera ; ne pas retoucher sans nouvelle décision.

Écart validé au GO/NO-GO Phase 0 (Vic, 10/07/2026) : les millésimes DVF 2014-2020 ont été
retirés de la distribution officielle (fenêtre glissante 5 ans DGFiP) → DVF_TENURE_12 (10 pts)
et DVF_TENURE_8 (6 pts) sont INCALCULABLES et remplacés par la variante dégradée
DVF_TENURE_OBS5 (8 pts) : « aucune mutation sur la fenêtre observable 2021-2025 ».
"""
from __future__ import annotations

# ── Tier combiné « Brûlante » 🔥 (décisions D2/D3) ─────────────────────────────────────────
# Brûlante = chaude Q×A ∧ v_score ≥ seuil. Garde-fou : si le nombre de Brûlantes sort de
# [30-120], NE PAS changer le seuil silencieusement — proposer un seuil ajusté dans le rapport
# final (méthode : top décile V des chaudes).
# v1.1 (mandat calibration, 10/07/2026) : seuil re-dérivé après recalibration = top décile V
# des chaudes (p90 = 34, dans la fenêtre d'application [30-60] fixée par Vic) → 93 Brûlantes.
# Valeur v1 historique : 50 (14 Brûlantes, garde-fou déclenché).
V_BRULANTE_THRESHOLD = 34
BRULANTE_GUARDRAIL = (30, 120)

# Run de référence de la matrice Q×A (source de vérité Socle V1 — cf. api SOURCE='q_v2').
Q_A_RUN_LABEL = "q_v2"

# ── Bandes (décision D2) ───────────────────────────────────────────────────────────────────
# (borne basse incluse, code) — évaluées dans l'ordre. V NULL → 'na'.
V_BANDS = (
    (50, "fort"),      # Signal fort (50-100)
    (25, "present"),   # Signaux présents (25-49)
    (1, "faible"),     # Signal faible (1-24)
    (0, "aucun"),      # Aucun signal (0)
)

V_BAND_LABELS = {
    "fort": "Signal fort",
    "present": "Signaux présents",
    "faible": "Signal faible",
    "aucun": "Aucun signal",
    "na": "N.A.",
}

# ── Plafonds par famille ───────────────────────────────────────────────────────────────────
FAMILY_CAPS = {"A": 35, "B": 25, "C": 15, "D": 25, "E": 15}
# A, B, C, E : MAX intra-famille ; D : SOMME plafonnée.
SUM_FAMILIES = {"D"}

# ── Barème par signal : code → (famille, points, label UI) ────────────────────────────────
SIGNALS = {
    # Famille A — Détresse juridique (BODACC)
    "BODACC_LJ":            ("A", 35, "Liquidation judiciaire en cours"),
    "BODACC_LJ_CLOT":       ("A", 30, "Liquidation clôturée, parcelle toujours au nom"),
    "BODACC_RJ":            ("A", 30, "Redressement judiciaire en cours"),
    "BODACC_RADIATION":     ("A", 25, "Radiation < 36 mois"),
    "BODACC_SAUVEGARDE":    ("A", 20, "Sauvegarde en cours"),
    "BODACC_CESSION_FONDS": ("A", 10, "Cession de fonds de commerce < 12 mois"),
    # Famille B — Cycle de vie du propriétaire (RNE / recherche-entreprises)
    "RNE_CESSATION":        ("B", 25, "Cessation déclarée / mise en sommeil"),
    "RNE_DIRIGEANT_75":     ("B", 22, "Dirigeant ≥ 75 ans"),
    "RNE_DIRIGEANT_70":     ("B", 18, "Dirigeant 70–74 ans"),
    "RNE_DIRIGEANT_65":     ("B", 12, "Dirigeant 65–69 ans"),
    "RNE_SCI_DORMANTE":     ("B", 8, "SCI ≥ 20 ans sans événement RNE récent"),
    # Famille C — Détachement géographique (siège du propriétaire)
    "GEO_HORS_ILE":         ("C", 15, "Siège hors Réunion (métropole/étranger)"),
    "GEO_AUTRE_COMMUNE":    ("C", 4, "Siège Réunion, autre commune que la parcelle"),
    # Famille D — Dormance de l'actif (somme plafonnée à 25)
    "FRICHE":               ("D", 18, "Friche recensée (Cartofriches)"),
    # v1.1 : CONDITIONNEL — ne compte que si un AUTRE signal est retenu (A/B/C, FRICHE ou DPE).
    # Tenure seule = 0 pt : au backtest v1, la masse « tenure seule » (81k parcelles) faisait 0.89×
    # de lift (bruit) ; la détention longue n'est un signal QUE combinée (succession, dormance).
    "DVF_TENURE_OBS5":      ("D", 8, "Détention longue (aucune mutation DVF 2021-2025) — combinée à d'autres signaux"),
    "NU_PM_HORS_IMMO":      ("D", 5, "Terrain nu détenu par PM hors construction/immobilier"),
    # Famille E — Pression réglementaire (DPE) — ⚠ libellés UI = calendrier DOM :
    # interdiction de location classe G au 01/01/2028, classe F au 01/01/2031
    # (loi Climat & Résilience, calendrier outre-mer — PAS 2025/2028).
    "DPE_G_MULTI":          ("E", 15, "≥ 2 DPE classe G — location interdite au 01/01/2028 (DOM)"),
    "DPE_G":                ("E", 12, "DPE classe G — location interdite au 01/01/2028 (DOM)"),
    "DPE_F":                ("E", 8, "DPE classe F — location interdite au 01/01/2031 (DOM)"),
}

# Familles/codes QUALIFIANTS pour la tenure conditionnelle (v1.1) : la détention longue ne
# compte que si l'un d'eux est aussi présent. NU_PM_HORS_IMMO n'en fait PAS partie.
TENURE_QUALIFYING_FAMILIES = {"A", "B", "C", "E"}
TENURE_QUALIFYING_CODES = {"FRICHE"}

# Signaux du barème D1 NON calculables (fenêtre DVF) — flaggés au rapport, jamais émis.
SIGNALS_NO_GO = {
    "DVF_TENURE_12": "millésimes DVF 2014-2020 retirés de la distribution officielle",
    "DVF_TENURE_8": "millésimes DVF 2014-2020 retirés de la distribution officielle",
}

# Malus : mutation DVF < 3 ans sur la parcelle.
# v1.1 : NEUTRALISÉ (0, était −15). Le backtest v1 l'a montré CONTRE-prédictif : les parcelles
# récemment mutées RE-vendent plus souvent (flips de marchands de biens, lift 2.04× sur V 0-7).
# Le vrai fix est le raffinement D5 (détection MdB) — consigné v1.2. Constante conservée pour
# que le moteur, l'UI et le backtest gardent le circuit ; à 0, le signal n'est plus émis.
MALUS_ACHAT_RECENT = ("DVF_ACHAT_RECENT", 0, "Achat récent (mutation DVF < 3 ans)")

# ── Fenêtres temporelles (mois) ────────────────────────────────────────────────────────────
RADIATION_WINDOW_MONTHS = 36
CESSION_FONDS_WINDOW_MONTHS = 12
ACHAT_RECENT_WINDOW_MONTHS = 36
SCI_DORMANTE_AGE_ANS = 20
SCI_DORMANTE_INACTIVITE_ANS = 5

# ── Matching (§4.2) ────────────────────────────────────────────────────────────────────────
CONF_SIREN_DIRECT = 1.0
CONF_DENOMINATION = 0.8
# Fallback dénomination : points des familles A/B/C × 0.7 (D/E indépendantes du propriétaire).
FALLBACK_FAMILY_FACTOR = 0.7
FALLBACK_AFFECTED_FAMILIES = {"A", "B", "C"}
# Tokens de forme juridique retirés lors de la normalisation d'une dénomination.
DENOM_STOP_TOKENS = {"SCI", "SARL", "SAS", "SASU", "EURL", "SA", "SNC", "SELARL"}

# ── Typage propriétaire (§4.3) ─────────────────────────────────────────────────────────────
# Groupe DGFiP « personne morale » → owner_type Score V. Groupe 6 (SEM) et 0/8 : raffinés
# par la liste bailleurs + catégorie juridique (7xxx = public) via l'enrichissement.
DGFIP_GROUPE_OWNER_TYPE = {
    1: "public", 2: "public", 3: "public", 4: "public", 9: "public",   # État/Région/Dépt/Commune/EP
    5: "bailleur",                                                     # Office HLM
    7: "copro",                                                        # Copropriétaires
}

# Bailleurs sociaux de La Réunion — liste locale codée en dur, FACILEMENT EXTENSIBLE (D4).
# SIREN vérifiés via recherche-entreprises (10/07/2026).
BAILLEURS_SOCIAUX_SIREN = {
    "310895172",  # SHLMR
    "310863592",  # SIDR
    "332824242",  # SEMADER
    "378918510",  # SODIAC
    "310863378",  # SEDRE
    "380177170",  # SODEGIS
}
# Pattern dénomination complémentaire (uppercase, sans accents).
BAILLEUR_DENOM_PATTERN = r"\b(HABITAT|HLM)\b"

# v1.1 : GRANDS GROUPES (catégorie INSEE, payload recherche-entreprises). Pour un GE/ETI, les
# familles B (âge dirigeant, cessation, dormance) et C (détachement géo) ne signalent RIEN d'une
# vente foncière — un administrateur d'Orange de 75 ans n'est pas un signal. A/D/E restent.
GRANDS_GROUPES_CATEGORIES = {"GE", "ETI"}

# Codes NAF « construction / immobilier » (préfixes) — un PM DANS ces codes n'est pas un
# détenteur passif de terrain nu (signal NU_PM_HORS_IMMO non émis).
NAF_IMMO_PREFIXES = ("41", "42", "43", "68")

# Ratio d'emprise bâtie sous lequel une parcelle est « terrain nu » (aligné bati.py: vacant < 5 %).
NU_RATIO_MAX = 0.05
