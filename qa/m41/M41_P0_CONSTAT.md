# M41 — PHASE 0 · CONSTAT (Radar Procédures PLU, 24 communes)

**Branche** `m41-radar-procedures-plu` · base `main` ec0aef91 (M40 mergé) · **STOP obligatoire :
Vic + Claude valident le tableau initial ENSEMBLE.** Le clone PROPOSE, il ne fige pas.
**Nature : LECTURE SEULE.** Zéro écriture DB/run/config/src. Seuls fichiers nouveaux : `qa/m41/*`.

Tout est **vérifié sur pièces** : dataset Sudocuh téléchargé (data.gouv.fr, Licence Ouverte 2.0,
millésime **31/12/2024**), croisé au run servi `q_v8_calibre` et à `config/plu_millesimes.yaml` (M40).

---

## 1. Sudocuh réel — couverture 974

Dataset **« Planification nationale des documents d'urbanisme (PLU/PLUi/CC/RNU) — SuDocUH — état
au 31/12/2024 »** (Ministère Cohésion des territoires). Fichier commune : `sudocuh_3.xlsx`, feuille
`ListeCommunes` (SHA256 `f0b8e928…0139a`). **Les 24 communes de La Réunion y sont** (extrait :
`qa/m41/sudocuh_974_p0.csv`).

Champs utiles (23 colonnes) : `Code INSEE`, `DU_Opposable` (PLU/CC/RNU), `id DU opp`, `DU_en_cours`
(type de procédure en cours, ou « Aucun »), `Etat détaillé`, `Approbation DU en vigueur` (date de
l'opposable), **`Prescription proc en cours`** (date de prescription de la procédure).

**Limites capitales (constat, pas reproche)** :
- **Sudocuh donne le TYPE + la PRESCRIPTION, PAS le STADE.** Aucune colonne « débat PADD / projet
  arrêté / enquête publique / approbation ». Or le sursis dépend du STADE (§3). → **Le stade est
  ABSENT pour les 24 communes** ; c'est précisément ce que la « chair » (registre curaté) doit
  ajouter, depuis les délibérations. Confirme l'architecture : Sudocuh = squelette, registre = chair.
- **Sudocuh (commune) ne trace que révision/élaboration, PAS les modifications** (aucune commune 974
  n'affiche « modification »). Les modifs de Saint-Benoît (M40) sont invisibles ici — cohérent, et
  sans enjeu sursis (§3 : le sursis L.153-11 ne vise pas la modification).
- **Sudocuh est périmé d'un an+ (31/12/2024).** Décisif (§2).

## 2. État des lieux 24 communes — Sudocuh vs sources en main (le constat central)

Sudocuh liste **11 communes « en cours »** (10 révision PLU + Saint-Philippe élaboration). MAIS
croisé au millésime M40 (`plu_millesimes.yaml`, mis à jour 2025-2026 par la campagne M32), **7 de ces
11 ont vu leur révision APPROUVÉE depuis** — Sudocuh (figé fin 2024) est simplement en retard.
Règle de réconciliation appliquée (sur pièces) : *si l'opposable M40 est POSTÉRIEUR à la prescription
Sudocuh, la révision a été approuvée depuis → clôturée*.

**→ 4 CIBLES radar genuine** (opposable M40 antérieur à la prescription, ou RNU) — table
`qa/m41/tableau_initial_p0.csv` :

| INSEE | commune | type | prescrite le | opposable réel | stade | confiance |
|---|---|---|---|---|---|---|
| 97409 | Saint-André | révision PLU | 2022-06-22 | 2019-02-28 | **ABSENT** | haute (opp 2019 < prescr 2022) |
| 97413 | Saint-Leu | révision PLU | 2022-05-17 | 2007-02-26 | **ABSENT** | haute (opp 2007 < prescr 2022) |
| 97417 | Saint-Philippe | élaboration PLU | 2002-08-30 | RNU (aucun) | **ABSENT** | haute (RNU, élaboration longue) |
| 97423 | Les Trois-Bassins | révision PLU | 2022-06-02 | **2017-02-21** | **ABSENT** | haute — ⚠ voir bug M40 |

**⚠ Contradiction constatée (doctrine M40 : une note config est une affirmation, pas une source)** :
pour **Trois-Bassins**, M40 `date_mairie = 2022-06-02` (idurba `97423_PLU_20220602`) est en réalité
la **date de PRESCRIPTION de la révision** (Sudocuh), PAS l'approbation de l'opposable (**2017-02-21**).
M40 a pris une prescription pour une approbation. À corriger (hors périmètre M41 — consigné pour Vic).

**7 « clôturées probables »** (Sudocuh périmé, M40 montre une approbation 2025-2026) : Étang-Salé,
Plaine-des-Palmistes, Saint-Denis, Saint-Louis, Saint-Paul, Sainte-Marie, Sainte-Suzanne. **À
confirmer** à la curation — ne PAS afficher « révision en cours » pour elles (ce serait faux).

**13 sans procédure** (Sudocuh « Aucun ») : Les Avirons, Bras-Panon, Entre-Deux, Petite-Île, Le Port,
La Possession, Saint-Benoît, Saint-Joseph, Saint-Pierre, Sainte-Rose, Salazie, Le Tampon, Cilaos.
(Saint-Benoît : modifs éventuelles hors Sudocuh — l'absence de procédure LOURDE est datée, les modifs
restent à confirmer mairie, M40.)

Tous les stades sont **ABSENT** : Sudocuh ne les donne pas ; ils seront curés (délibérations).

## 3. Le sursis à statuer — base légale exacte

**Article L.153-11 du Code de l'urbanisme** (verbatim, Légifrance/Doctrine) :
> « L'autorité compétente peut décider de surseoir à statuer, dans les conditions et délai prévus à
> l'article L. 424-1, sur les demandes d'autorisation concernant des constructions, installations ou
> opérations qui seraient de nature à compromettre ou à rendre plus onéreuse l'exécution du futur plan
> **dès lors qu'a eu lieu le débat sur les orientations générales du projet d'aménagement et de
> développement durable**. »

**Précision qui corrige le cadrage du mandat** : le seuil légal n'est **PAS « projet arrêté »**, c'est
le **débat sur le PADD** (antérieur à l'arrêt du projet). Deux conditions cumulatives : (1) le projet
compromettrait/renchérirait le futur plan ; (2) le débat PADD a eu lieu. **Durée max 2 ans**
(L.424-1). Décision motivée, contrôlée par le juge.

**Régimes par type de procédure** :
- **Élaboration / révision (générale)** : sursis L.153-11 possible **dès le débat PADD**. ← nos cibles.
- **Modification / modification simplifiée** : **PAS de débat PADD → sursis L.153-11 indisponible**
  (le Conseil d'État a tranché le sort du sursis opposé en cours de modification). C'est pourquoi
  Sudocuh (qui ne trace pas les modifs) suffit au périmètre sursis.
- **Révision allégée** : à traiter au cas par cas à la curation.

**Conséquence pour le radar** : la vigilance sursis ne peut s'allumer que si le **débat PADD** est
constaté (date + délib.) — donnée ABSENTE de Sudocuh, **à curer par cible**. Tant qu'elle est absente,
le radar dit « révision en cours (prescrite le X) — sursis possible SI le débat PADD a eu lieu, à
vérifier en mairie », jamais « sursis applicable ».

## 4. Population d'impact

**Bornes hautes** (les 11 communes Sudocuh « en cours », avant réconciliation) : **601 têtes**
(brûlante+chaude) · **1 220 déclassées** zone-fermée/AU (veille AU).

**Après réconciliation — les 4 cibles genuine** :

| commune | têtes (brûlante+chaude) | déclassées AU/zone-fermée (veille AU) |
|---|---|---|
| Saint-André | 30 | 217 |
| Saint-Leu | 82 | 119 |
| Saint-Philippe | 2 | 0 (RNU, aucune AU) |
| Les Trois-Bassins | 9 | 75 |
| **TOTAL** | **123** | **411** |

**Sursis-possible : indéterminable aujourd'hui** — dépend du stade « débat PADD » (ABSENT). Les 123
têtes sont la population POTENTIELLE de la vigilance sursis ; le sous-ensemble réel se fixe à la
curation (quelles cibles ont passé le débat PADD). La **veille AU** (411 déclassées) est, elle,
mesurable dès qu'une commune est confirmée en procédure — c'est le signal « ouverture possible à
terme, à suivre » (aucun tier remonté).

## 5. STOP — validation conjointe du tableau initial

Le mandat l'exige : **la première curation est humaine.** Ce que je propose, à valider ensemble :

- **A. Les 4 cibles genuine** (Saint-André, Saint-Leu, Saint-Philippe, Trois-Bassins) — d'accord ?
- **B. Les 7 « clôturées probables »** : confirmes-tu qu'elles sont approuvées (2025-2026) et donc
  HORS radar ? (Sinon, lesquelles rouvrent une nouvelle procédure ?)
- **C. Le stade** : pour chaque cible, il faut la date du **débat PADD** (délib.) pour armer la
  vigilance sursis. Les as-tu, ou faut-il les chercher (portail commune) à la curation ?
- **D. Le bug M40 Trois-Bassins** (date_mairie = prescription, pas approbation ; opposable réel
  2017-02-21) : je le consigne ; correction dans un geste M40-bis séparé ou ici ?
- **E. Seuil de fraîcheur** du geste trimestriel : 90 jours (mandat) confirmé ?

**Ma recommandation** : registre initial = les 4 cibles + les 13 « aucune » datées + les 7
« clôturées à confirmer » marquées explicitement ; stade ABSENT partout tant que le débat PADD n'est
pas curé ; le radar reste au conditionnel (« sursis possible SI débat PADD ») jusque-là. Le doute ne
profite jamais au classement : une procédure en cours n'ouvre ni ne ferme aucun tier.

**Note — addendum Phase 2.6** reçu (outil « Vérif procédure » dans le module Outils, entrée IDU →
procédure OUI/NON datée + conséquences ; lit le radar, ne calcule rien) : intégré au plan Phase 2,
même point de calcul et mêmes libellés que la fiche. Sera construit après ce feu vert.

---

## Annexes
- `qa/m41/sudocuh_974_p0.csv` — les 24 communes, données Sudocuh brutes (type, prescription, dates).
- `qa/m41/tableau_initial_p0.csv` — tableau réconcilié proposé (Sudocuh × M40, cible_radar, stade
  ABSENT, proposition par commune).
- `qa/m41/_global.txt` — provenance (URLs data.gouv.fr, SHA256 source) + SHA digests.
- Aucune écriture servie. Golden / re-mesures / vigilances M37 : non touchés (lecture seule).
