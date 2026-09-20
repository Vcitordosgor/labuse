"""Fiche de règle — outil « Successions à venir » (M28). CIRCUIT-4 / OUTILS-FIX-5 L6."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_successions_veille",),
    formule_codee=("Parcelles à potentiel dont le propriétaire personne morale approche une "
                   "succession : signal Score V — dirigeant PM ≥ 70 ans OU SCI dormante (≥ 20 ans, "
                   "sans mise à jour RNE depuis ≥ 5 ans) — figé dans parcel_veille_succession ; "
                   "n = count sur l'île ou une commune. JAMAIS une succession ouverte : un radar 3-7 ans."),
    entrees=("parcel_veille_succession", "parcelle_personne_morale", "pm_dirigeants (RNE INPI)"),
    classe="choix_labuse",
    fonction="src/labuse/api/modules.py:successions_liste (snapshot produit par le moteur Score V)",
    verdict="choix_assume",
    choix=("« Succession à venir » = définition LABUSE d'un SIGNAL d'approche (dirigeant PM âgé ou "
           "SCI dormante), pas un fait juridique : ni succession ouverte, ni décès, ni certitude. "
           "Seuils 70 ans / SCI 20 ans + 5 ans d'inactivité, RNE INPI daté (OUTILS-MUSCLER-1)."),
    valide_par="en_attente",
    verifie_le="2026-09-20",
))
