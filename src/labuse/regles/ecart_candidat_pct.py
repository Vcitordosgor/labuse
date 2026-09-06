"""Fiche de règle — comparaison candidat vs servi (golden ops). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ecart_candidat_pct",),
    formule_codee=("Comparaison des DISTRIBUTIONS de tiers entre le run candidat et le run servi "
                   "(part de chaque tier, écarts en points) — lecture seule, jamais une bascule."),
    entrees=("parcel_p_score_v2 (candidat + servi)", "p_score_v2_runs"),
    classe="choix_labuse",
    fonction="src/labuse/golden_ops.py:comparer",
    verdict="choix_assume",
    choix="Mesure d'aide à la bascule (l'écart alerte, l'humain tranche via la note de version).",
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
