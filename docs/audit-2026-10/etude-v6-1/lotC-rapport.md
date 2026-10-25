# ÉTUDE V6 — Lot C : stationnement par type de projet

Cas test obligatoire : **Saint-Denis DL0247-0248, zone Ui, « Résidence senior ».**

## Source du ratio 1 place / 3 logements de l'architecte
**Introuvable dans le PLU de Saint-Denis.** La règle Ui (art. XVII « Stationnement » / Ui.12, millésime
**2026-08-05**) est **1 place / logement** (plat, « 1 place par logement d'une surface plancher < 100 m² »).
Aucune réduction RPA / personnes âgées en Ui. Le ratio **1/3 existe ailleurs** (Saint-Benoît, zone U,
art. U.12 : « Résidences universitaires et de personnes âgées : 1 place pour 3 logements ») — **pas à
Saint-Denis**. Le PDF de l'architecte ne cite aucune base. Le plafond national **L151-35** (modélisé dans
LABUSE, `regles/distance_arret_m.py`) plafonne à **0,5 place/logt** les catégories L151-34 (logement
aidé / personnes âgées / étudiant) **à moins de 800 m d'un TCSP** — soit 0,5, **pas 1/3**.

## Appliqué (avec sa source seulement)
- **Règle générale du PLU** (opposable) : 1 place/logt, art. XVII, millésime 2026-08-05 → **appliquée**
  (c'est la base servie), contrôle binding.
- **Plafond L151-35** (national) : ≤ 0,5 place/logt pour résidence de personnes âgées (L151-34, 3°).
  Condition TCSP < 800 m **vérifiée par LABUSE** (station à **33 m**). Éligibilité de catégorie **À
  confirmer** (le nom « senior » ne prouve pas la catégorie juridique). → **les deux calculs affichés**,
  le plafond en **« À confirmer »**, jamais présenté comme acquis ni comme règle du PLU.
- Capacité **sous le régime réduit** (2ᵉ passage moteur au plafond 0,5, seulement si le stationnement
  plafonne et le TCSP est < 800 m) : **24 logements, À confirmer**.

## Tableau Saint-Denis — LABUSE avant / après / architecte

| Poste | LABUSE **avant** (Lot B) | LABUSE **après** (Lot C) | Architecte (URBAN) |
|---|---|---|---|
| Type de projet | collectif (non différencié) | **Résidence senior** (destination L151-34) | RPA LLTS |
| Règle stationnement **appliquée** | 1 pl./logt (barème Ui, non rattaché au type) | **1 pl./logt** — PLU Ui art. XVII, millésime 2026-08-05, *règle vérifiée, appliquée* | **1 pl./3 logts** (1/3) |
| Source du ratio réduit | — (non traité) | **Plafond L151-35** : ≤ 0,5 pl./logt · TCSP < 800 m **vérifié (33 m)** · catégorie **À confirmer** | **aucune source** (= règle Saint-Benoît, pas Saint-Denis) |
| Logements (règle générale) | 12 max / 10 votre programme | 10 votre prog. / 12 optim — *stationnement limitant* | 22–27 |
| Logements **sous régime réduit** | non calculé | **24** (*À confirmer*, si éligible L151-35) | 27 |
| Places | 10–12 | 10 (général, appliqué) · 12 (sous réduit) | **8** |
| Verdict global | À compléter (PPR) | **À compléter** (PPR rouge+bleue + prospect + éligibilité stationnement, tous À confirmer) | — |

**Lecture.** *Avant*, LABUSE plafonnait à ~12 logements : il appliquait le barème PLU générique (1/logt)
sans conscience du type, et le stationnement aérien saturait les 650 m² constructibles. *Après*, LABUSE
applique **toujours** la règle opposable (1/logt, 12 logts, base servie) MAIS affiche le **plafond
L151-35 (0,5, à confirmer)** sous lequel **24 logements** tiennent — rejoignant la fourchette de
l'architecte (22-27) **uniquement sous condition d'éligibilité**. LABUSE **ne reprend pas** le 1/3 de
l'architecte : ce n'est pas une règle de Saint-Denis, et le plafond national est 0,5 (non 1/3). La
différence réelle avec l'architecte n'est donc pas le calcul mais la **preuve** : LABUSE conditionne la
capacité haute à une éligibilité juridique à confirmer ; l'architecte l'a posée sans source.

## Livré
- **Backend** : 4 types acceptés (`_TYPES_PROJET`) ; `_stationnement_regimes` (général PLU + plafond
  L151-35, avec vérif TCSP `_tcsp_sous_800m`) ; capacité réduite = 2ᵉ passage moteur
  (`etudier_complet(stationnement_ratio=0,5)`), lancé **seulement si le stationnement plafonne**
  (sinon « sans effet », budget 30 s tenu). Route `POST /modules/etude/stationnement` (étape 2, sans moteur).
- **Frontend** : étape 2 affiche la règle réelle (générale + plafond L151-35 « À confirmer ») à la
  sélection du type ; le résultat porte un bloc stationnement (général appliqué + plafond à confirmer +
  capacité réduite). Le vrai `type_projet` est transmis au moteur.
- **États** : barème manquant → contrôle **À confirmer** (Lot B), étude **À compléter**.

## Vérifié
- **tsc 0 · vitest 286/286** (EtudeV6 8, dont étape-2 stationnement). **pytest** implantation 117 + Lot C
  3/3 (`test_etude_v6_stationnement`) — 1 échec `test_route_etude_*` **pré-existant**.
- **chasse_docs 20·0** · **chasse_donnees 23·0·2 SKIP** (cloche alignée q_v20 après merge ; SKIP = export 500 pré-existants).
- **Captures** `captures/lotC-01..03` : étape 2 règle générale, plafond L151-35, résultat régime réduit (24).

## Reste (Lot D, E)
- **Lot D** : lotissement = division-or sur l'assiette (aujourd'hui l'implantation reste collective).
- **Lot E** : PDF depuis le même study_id, carte Docs, bilan surfacique clos.
