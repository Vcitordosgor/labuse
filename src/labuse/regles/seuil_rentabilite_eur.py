"""Fiche de règle — bilan du Financier à rebours HT (postes, bornes, sensibilité, sorties).
CIRCUIT-4 · EXPORTS-2 lot 5. Un seul calcul (`financier_bilan.calculer`) produit tous ces postes ;
une seule fiche les couvre."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("seuil_rentabilite_eur", "charge_fonciere_basse_eur", "charge_fonciere_haute_eur",
             "prix_revient_eur_m2", "sensibilite_prix_sortie",
             "bilan_frais_acquisition_eur", "bilan_honoraires_techniques_eur",
             "bilan_stationnement_eur", "bilan_aleas_eur", "bilan_depollution_eur",
             "bilan_portage_eur", "redevance_archeologie_eur"),
    formule_codee=(
        "Bilan à rebours HT (décision Vic 07/09) : CA_HT = surface libre × prix de sortie ÷ (1+taux) "
        "+ surface sociale × prix bailleur (le prix de sortie DVF est TTC, ramené HT par le taux du "
        "régime, 8,5 % à La Réunion). Postes : construction = SDP × coût/m² ; honoraires = hono% × "
        "construction ; stationnement = logements × coût par place saisi ; aléas = aléas% × "
        "construction ; portage = (construction+VRD) × taux × durée/12, ou forfait 3 % du CA si pas "
        "de taux ; frais d'acquisition = frais% × prix demandé ; dépollution SAISIE (jamais estimée). "
        "Redevance d'archéologie préventive = 0,68 €/m² × SDP. Charge foncière supportable = CA_HT − "
        "Σ(postes chiffrés) − marge. Bornes : basse = coût haut × sortie bas ; haute = coût bas × "
        "sortie haut (fourchette de coût = source unique YAML, ±5 % sur le prix de sortie) — jamais "
        "un point seul. Sensibilité (prix de sortie) = charge sur l'axe sortie {bas, retenu, haut} "
        "du tableau double 3×3. Seuil de rentabilité = charge foncière centrale (prix d'achat qui "
        "atteint la marge visée). Prix de revient = (foncier retenu + Σ postes) ÷ surface vendable. "
        "Un poste non chiffré vaut None (jamais un défaut) → le résultat porte la mention « maximum »."),
    entrees=("questionnaire_financier (coûts, %, prix demandé, régime TVA, portage — saisies client)",
             "programme (surface vendable/plancher/terrain, logements)",
             "prix de sortie observé (fiche prix_sortie_bati_eur_m2)",
             "Hypotheses.charger() (fourchette de coût source unique, RAP 0,68 €/m², taux TVA 8,5 %)"),
    classe="methode_standard",
    fonction="src/labuse/exports/financier_bilan.py:calculer",
    verdict="reference_introuvable",
    choix=("Les pourcentages proposés (frais 7 %, honoraires 12 %, aléas 4 %, marge 9 %) et la "
           "fourchette de coût (source unique YAML) sont des HYPOTHÈSES LABUSE, saisissables au "
           "questionnaire et affichées avec le bilan ; le bilan est « indicatif, ne remplace pas un "
           "bilan professionnel ». La redevance d'archéologie préventive applique le taux 0,68 €/m² "
           "de SDP (référence non encore relue à la lettre → verdict honnête reference_introuvable)."),
    exemple_temoin="tests/test_exports2_lot5.py::test_bilan_ht_au_centime",
    verifie_le="2026-09-08",
))
