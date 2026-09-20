# EXPORTS-REBRANCHEMENT-1 — Lot 5 : audit du questionnaire Financier (lecture seule)

20/09/2026 · branche `feat/exports-rebranchement-1` · AUCUNE modification de code dans ce lot —
un rapport, Vic tranche ensuite si le Financier reste, se simplifie, ou disparaît.

Sources lues : `financier_questionnaire.py` (ECRANS, `_PREFILL_CONST`, `prefill`, `resoudre`,
`manques`), `exports/builder.py:_financier_contexte`, `exports/financier_bilan.py` (`calculer`,
`_postes`, `_ca_ht`), témoin chiffré AN0347 (saisie minimale 4 logements T3, 3 800 €/m², TVA
assujetti — celle de l'audit EXPORTS-AUDIT-2).

## 1. La matrice des champs — parcours « construction » (19 champs)

| # | Champ | Utilisé au bilan ? | Pré-rempli aujourd'hui | Pré-remplissable depuis la donnée ? |
|---|---|---|---|---|
| 1 | `logements_vises_saisi` | ✓ programme (repli si le potentiel ne chiffre pas) | ✓ capacité du potentiel | déjà fait |
| 2 | `typologie_moyenne_saisi` | ✓ surface vendable = logements × typologie | ✗ (défaut silencieux « T3 » dans le builder) | ✓ le défaut T3 devrait être un PREFILL dit, pas un défaut muet |
| 3 | `part_sociale_saisi_pct` | ✓ partage du CA (libre/bailleur) | ✗ (0 par défaut) | ± seuils de mixité de la zone (`mixite_clause`) quand ils existent |
| 4 | `prix_demande_saisi_eur` | ✓ frais d'acquisition + « écart au prix demandé » | ✗ (par principe : donnée du vendeur) | ± une annonce Radar active porte un prix demandé |
| 5 | `frais_acquisition_saisi_pct` | ✓ | ✓ constante 7 % sourcée | déjà fait |
| 6 | `bilan_demolition_eur` | ✓ poste saisi (projet) | ✗ | ✗ (devis — assumé) |
| 7 | `bilan_depollution_eur` | ✓ poste saisi (projet) | ✗ | ✗ (devis — assumé) |
| 8 | `cout_construction_saisi_eur_m2` | ✓ cœur du bilan | ✓ médiane régionale EPTB/CDC | déjà fait |
| 9 | `honoraires_techniques_saisi_pct` | ✓ | ✓ constante 12 % | déjà fait |
| 10 | `vrd_saisi_eur_m2` | ✓ — **assiette en cause, § 3** | ✓ constante 90 €/m² | l'assiette, pas le taux, est le problème |
| 11 | `cout_place_stationnement_saisi_eur` | ✓ logements × coût | ✗ | ± constante sourcée possible (hypothèses LABUSE) |
| 12 | `aleas_saisi_pct` | ✓ | ✓ constante 4 % | déjà fait |
| 13 | `taxe_amenagement_saisi_eur` | ✓ | ✓ **pré-calculée** (SDP projet × taux communal public) | déjà fait — le meilleur exemple du genre |
| 14 | `prix_sortie_saisi_eur_m2` | ✓ **INDISPENSABLE** (CA) | ✗ | **✓✓ `prix_sortie_bati_eur_m2` du registre** — le Dossier §8 la nomme lui-même « référence de revente … utilisée comme prix de sortie du programme reconstruit » (1 360 €/m² sur AN0347). Pré-remplissable AVEC source ; resterait modifiable |
| 15 | `prix_vente_bailleur_saisi_eur_m2` | ✓ si part sociale > 0 | ✗ | ± barème d'agrément de la zone A/B/C (arrêté) |
| 16 | `marge_visee_saisi_pct` | ✓ | ✓ constante 9 % | déjà fait |
| 17 | `regime_tva_saisi` | ✓ **INDISPENSABLE** (bilan HT ou TTC) | ✗ | ✗ — statut fiscal du porteur, non devinable. LA question irréductible |
| 18 | `duree_portage_saisi_mois` | ✓ portage | ✓ constante 29 mois (9 instruction + 20 chantier) | ± la vélocité communale (`velocite_delai_median_mois`, registre) affinerait les ~9 mois |
| 19 | `taux_apport_saisi_pct` | ✓ portage précis (sinon forfait % CA — repli sain) | ✗ | ✗ (condition bancaire du porteur) |

Parcours « revente » (3 champs propres) : `prix_achat_revente_saisi_eur` (indispensable),
`prix_revente_saisi_eur` (indispensable), `travaux_revente_saisi_eur` (optionnel) — tous
utilisés par `calculer_revente`, aucun pré-remplissable (données de la négociation).

**Aucun champ mort** : les 19+3 entrent tous au calcul (confirme la mesure différentielle
RECETTE-4 « 20 questions toutes au bilan »).

## 2. Combien de champs sont réellement indispensables ?

- **Indispensables stricts : 2** — `prix_sortie_saisi_eur_m2` et `regime_tva_saisi`
  (`OBLIGATOIRES`, `manques()`), plus le **programme** quand le potentiel ne chiffre rien :
  `logements_vises_saisi` (+ la typologie, qui a en réalité un défaut T3). Soit **2 à 4** selon
  la parcelle.
- **7 champs à constante sourcée** (frais, honoraires, coût, VRD, aléas, marge, portage) + la
  taxe pré-calculée + les logements pré-remplis du potentiel : **9 pré-remplis** aujourd'hui.
- **Reste : 8 champs optionnels** (postes « non chiffré » → bilan « en maximum », dit).

**Le chemin de simplification est net** : si `prix_sortie` est pré-rempli depuis
`prix_sortie_bati_eur_m2` (la donnée existe, sourcée, le Dossier l'appelle déjà « prix de
sortie ») et si le défaut T3 devient un prefill dit, le questionnaire tombe à **UNE question
bloquante — le régime de TVA** — plus des confirmations ambrées. Le Financier peut donc rester
ET se simplifier : mêmes écrans, quasi plus de 422.

## 3. L'assiette VRD — 90 €/m² × terrain ENTIER : mauvaise base

La formule (`financier_bilan.py:122`) : `vrd = surface_terrain × vrd_m2`.

Sur AN0347 (le constat de l'audit) : 4 501 m² × 90 € = **405 090 € HT** pour un programme de
**4 logements / 325 m² SDP**, soit :
- **≈ 101 000 € de VRD par logement** (usage petit collectif : ~8 000-15 000 €/logement) ;
- **49 %** du coût de construction (829 k€) — usage : ~10-15 % ;
- **44 %** du CA (911 k€). Le poste à lui seul rend la charge foncière négative.

Le 90 €/m² (« base VRD des hypothèses LABUSE, modulée par la viabilisation ») est un ratio
d'AMÉNAGEMENT : il a un sens sur la surface réellement aménagée d'un lotissement, pas sur la
contenance cadastrale entière d'une opération ponctuelle. **Le biais croît avec la taille de la
parcelle** — il pénalise précisément les grandes parcelles à potentiel (le cœur de cible), et il
est insensible au programme (4 ou 40 logements, même VRD).

Contre-épreuve BO0852 (742 m²) : 67 k€ — plausible par accident (petite parcelle). C'est bien
l'assiette qui est fausse, pas le taux.

**Recommandations (au choix de Vic, aucune appliquée)** :
1. **Assiette = surface de plancher du projet** : 325 m² × 90 € = 29 250 € (3,5 % de la
   construction — dans l'épure) ; cohérente avec la taxe d'aménagement qui se calcule déjà sur
   cette SDP au même endroit ;
2. ou assiette = emprise aménagée SAISIE (un champ de plus — contraire au sens du lot) ;
3. ou plafond de vraisemblance : `min(terrain, k × SDP) × 90 €` + le garde `_hors_marche`
   étendu au poste VRD (aujourd'hui il ne borne que les prix).

## 4. Ce que le lot suggère (rien d'exécuté)

1. Pré-remplir `prix_sortie_saisi_eur_m2` depuis `prix_sortie_bati_eur_m2` (source dite,
   modifiable) — supprime la principale cause de 422.
2. Faire du défaut T3 un prefill AFFICHÉ (source « typologie médiane retenue »), plus un défaut
   silencieux du builder.
3. Corriger l'assiette VRD (reco 1 : SDP du projet).
4. Candidats de pré-remplissage secondaires : prix bailleur (barème zone), coût de place
   (constante sourcée), durée d'instruction (vélocité communale du registre), prix demandé
   (annonce Radar active).
5. Le Financier RESTE utile : moteur sain (bilan à rebours + revente), aucun champ mort, gardes
   hors-marché en place — c'est un problème de remplissage (2 questions de trop) et UNE formule
   d'assiette, pas d'architecture.
