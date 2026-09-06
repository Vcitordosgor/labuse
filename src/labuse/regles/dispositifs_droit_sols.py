"""Fiche de règle — dispositifs du droit des sols (ER, EBC, DPU). SOURCES-1 lot 1."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("dispositifs_parcelle", "er_emplacement_reserve", "ebc_classe", "dpu_perimetre"),
    formule_codee=(
        "Intersections live parcelle × spatial_layers : famille ER = typepsc ∈ "
        "emplacement_reserve_typepsc (05) ∪ rescue libellé ER \\ veto libellés non-ER ; EBC = "
        "typepsc ∈ boise_classe_typepsc (01) ; DPU = kind='dpu' (typeinf 04). Part = "
        "aire(∩)/aire(parcelle). Cascade : ER part ≥ er_hard_exclude_pct (50 %) → RÉDHIBITOIRE, "
        "sinon VIGILANCE + surface ER déduite de l'emprise ; EBC part ≥ ebc_hard_exclude_pct "
        "(80 %) → RÉDHIBITOIRE, sinon VIGILANCE forte + part EBC soustraite de l'assiette "
        "(union ER∪EBC, jamais de double soustraction au chevauchement) ; DPU → VIGILANCE "
        "faible (renforcé → moyen). Seuils lus de config/cascade_rules.yaml (source unique)."),
    entrees=("spatial_layers (kind=plu_gpu_prescription : subtype/typepsc, attrs->libelle, "
             "geom_2975)", "spatial_layers (kind=dpu : subtype, geom_2975)",
             "config/cascade_rules.yaml (prescription_plu, dpu)"),
    classe="choix_labuse",
    fonction=("src/labuse/cascade/layers/phase1.py:PrescriptionPluLayer + DpuLayer ; "
              "src/labuse/faisabilite/db.py:parcel_faisabilite (_EMPRISE, soustraction ER∪EBC)"),
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 (06/09/2026) : « ER → VIGILANCE, RÉDHIBITOIRE au-delà de 50 % de la "
        "parcelle ; EBC → VIGILANCE dès non nul, RÉDHIBITOIRE au-delà de 80 % ; la part EBC est "
        "soustraite de l'assiette du bloc potentiel ; DPU → VIGILANCE ». Le seuil ER 50 % "
        "RÉTABLIT l'exclusion annulée par M129 P1.1 (le motif garde la nature LEVABLE de la "
        "servitude : à réévaluer si l'ER est abandonné). Le seuil EBC 80 % est un choix LABUSE "
        "non calibré par une mesure : appui juridique = L113-1 CU (le classement interdit tout "
        "changement d'affectation de nature à compromettre la conservation du boisement) — à "
        "80 % de couverture l'assiette restante est résiduelle. Le DPU ne pèse que sur la "
        "TRANSACTION (DIA, substitution possible de la commune), jamais sur la constructibilité "
        "→ vigilance seulement, rédhibitoire jamais. Effet cascade : au prochain run candidat "
        "seulement (rien de basculé)."),
    exemple_temoin="tests/test_sources1_lot1.py::test_prescription_er_seuils",
    verifie_le="2026-09-07",
))
