# EXPORTS — les 12 arbitrages (étape 2)

Source : `DONNEES-RAPPORT.md` (CC, 05/09/2026). Réponds par le numéro et la lettre. « OK » = tu prends ma recommandation.

| # | Question | Ma recommandation | Pourquoi, en une ligne |
|---|---|---|---|
| Q1 | Quel prix en tête de fiche et dans la synthèse marché ? | **a** — `sector_price` parcelle (3 818), avec n et rayon effectif affichés | C'est la doctrine « Mon secteur » déjà décidée ; la médiane par secteur cadastral (3 804) passe en ligne secondaire, étiquetée. |
| Q2 | La ligne « prix ancien médian de la commune » (en réalité autour du centroïde, n 11) ? | **c** — supprimer | La tendance commune (n 218/583) porte déjà la vraie médiane communale (4 490) ; cette ligne ne fait que contredire. |
| Q3 | Quel « neuf » sert le bilan : neuf observé (4 730) ou VEFA à l'acte (4 742) ? | **a** — le neuf observé, décision du 28/07 ; l'autre disparaît de la fiche ou se libelle « VEFA déclaré à l'acte » | Deux chiffres à 12 € d'écart sans définition, c'est pire qu'un seul. |
| Q4 | La table orpheline `parcel_residuel_bati` (les 127 m²) ? | **a** — supprimer sa lecture, moteur commun seul | Ses données datent du 10 juillet et ne bougeront plus jamais ; 85 % de ses lignes sont vides. |
| Q5 | Résolution de zone sur parcelle à cheval : dominante ou centroïde ? | **a** — dominante partout + drapeau « à cheval » avec les deux règlements | C'est ce que l'écran fait déjà ; le centroïde a servi « 27-31 logements » sur une parcelle N. **À traiter avant les exports : c'est un bug du moteur, visible partout.** |
| Q6 | Zone N ou A avec SDP résiduelle > 0 (T3 : 4 188 m²) ? | **a** — 0 par règle en N/A, cause affichée | Boussole : jamais un faux constructible. |
| Q7 | Permis à proximité : une définition ? | **a + c** — 500 m · 24 mois comme définition client ; et tout chiffre qui reste porte son rayon et sa fenêtre | Un seul réflexe pour le lecteur ; le reste ne peut plus mentir. |
| Q8 | La vente d'immeuble agrégée (« appartement 750 m² ») ? | **c** — étiquette `immeuble` à l'ingestion **et** seuil de vraisemblance à l'affichage | L'ingestion corrige la cause, le seuil protège le temps qu'elle tourne. |
| Q9 | ICPE « Non ICPE » : alerter ? | **a** — hors de l'alerte, gardée au tableau avec son régime | Le fait est vrai, l'alerte ne l'est pas. |
| Q10 | Archiver les données d'entrée du Flash payé ? | **a** — oui, JSON à côté du PDF | Sans ça, un document à 79 € n'est pas reproductible. Effort S. |
| Q11 | Coût de démolition ? | **a** — champ de saisie, défaut « non chiffré » | Le lot C a cherché sérieusement : aucun référentiel public au 974. Un chiffre inventé serait pire qu'un vide affiché. |
| Q12 | Saint-André, Saint-Leu, Saint-Philippe (aucun document GPU), Petite-Île (sans prescriptions) ? | **a** — drapeau « prescriptions non vérifiables sur cette commune » dans tout export, dès maintenant ; c) en chantier séparé | Sur ces quatre communes, un emplacement réservé est invisible : le PDF doit le dire plutôt que se taire. |

## Trois choses que le rapport ajoute sans te demander d'arbitrer

- **Coût de construction sourçable** : le 2 300-2 800 €/m² non sourcé peut être remplacé par l'EPTB 2024 et le dataset CDC (prix de revient médian collectif 2 304 → 2 842 €/m², 2021-2025). Ça va dans les correctifs.
- **Quatre sources nouvelles en effort S** : DPU (même connecteur que l'assainissement), PEB des deux aéroports (éliminatoire pour le logement), zonage A/B/C (24 lignes statiques), loyers de marché (24 communes couvertes). Et CatNat à réparer (troncature à 10 arrêtés par commune).
- **Trois mirages** : DPE (17 lignes), contacts mairie (0), programmes promoteurs (9). Ils sortent du sommaire cible jusqu'à nouvel ordre.
