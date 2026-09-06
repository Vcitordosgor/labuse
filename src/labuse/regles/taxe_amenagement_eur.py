"""Fiche de règle — calculette de taxe d'aménagement. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    # FICHE-1 lot 5 — taxe_amenagement_estimee_eur (fiche parcelle) partage CE calcul : même
    # calculer(), assiette = surface de plancher du scénario table rase, taux communal PUBLIC.
    donnees=("taxe_amenagement_eur", "taxe_amenagement_estimee_eur",),
    formule_codee=(
        "Assiette = surface_taxable × valeur forfaitaire de l'année (892 €/m² hors IdF, millésime "
        "2026 du YAML daté) + forfaits d'installations (piscine 251 €/m², PV au sol 10 €/m², "
        "stationnement extérieur 2 928 €/place, éolienne 3 000 €/mât) ; abattement 50 % sur les "
        "100 premiers m² d'une résidence principale et sur les logements aidés ; exonération de "
        "plein droit des surfaces < 5 m². Taxe = assiette × (taux communal + taux départemental) — "
        "le taux communal est SAISI (ou lu de taxe_amenagement_taux si une délibération publique "
        "est en base), JAMAIS un défaut : sans taux, pas de total. Taux départemental plafond "
        "légal 2,5 %, étiqueté « à confirmer ». Détail ligne par ligne, vérifiable."),
    entrees=("config/taxe_amenagement.yaml (millésime 2026, source service-public A15416, relevé "
             "2026-08-28)", "taxe_amenagement_taux (délibérations publiques)", "saisies client"),
    classe="regle_externe",
    fonction="src/labuse/taxe_amenagement.py:calculer",
    verdict="conforme",
    reference=Reference(
        titre="Code général des impôts — taxe d'aménagement (assiette)",
        article="art. 1635 quater H (valeurs forfaitaires) et 1635 quater I (abattement 50 %)",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049641227/",
        version="1635 quater H en vigueur au 01/07/2026 ; 1635 quater I version 16/02/2025→01/01/2027 ; "
                "valeurs 2026 confirmées par service-public.gouv.fr A15416 (07/01/2026)",
        extrait=("1635 quater H : « fixée forfaitairement à 892 € pour les communes situées hors de "
                 "la région d'Ile-de-France et à 1 011 € pour les communes situées dans la région "
                 "d'Ile-de-France » (actualisation annuelle ICC INSEE). 1635 quater I : « Un "
                 "abattement de 50 % est appliqué sur les valeurs mentionnées au 1° de l'article "
                 "1635 quater H pour : […] Les cent premiers mètres carrés des locaux d'habitation "
                 "et leurs annexes à usage d'habitation principale ». service-public A15416 "
                 "(2026) : piscines 251 €/m², stationnement extérieur 2 928 €/place (jusqu'à "
                 "5 857 € sur délibération), panneaux PV au sol 10 €/m², éolienne > 12 m "
                 "3 000 €/unité."),
        lu_le="2026-09-06"),
    choix=("Doctrine « aucun taux inventé » : le taux communal vient d'une délibération ou du "
           "client, jamais d'un défaut. ERRATA DOCUMENTAIRES consignés (REGLES-ECARTS) : le mandat "
           "cite « art. L331-10 s. » (code de l'urbanisme), ABROGÉ depuis l'ord. 2022-883 — la "
           "base en vigueur est le CGI ; et les commentaires du YAML INVERSENT H et I (valeurs "
           "forfaitaires attribuées à I, abattement à H) — les VALEURS, elles, sont exactes."),
    exemple_temoin="tests/regles/test_taxe_amenagement.py::test_calcul_ligne_a_ligne_independant",
    valide_par="cc",
    verifie_le="2026-09-06",
))
