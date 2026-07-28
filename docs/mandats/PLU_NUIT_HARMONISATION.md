# PLU-SÉRIE-NUIT — HARMONISATION DOCTRINES a + b (arbitrage Vic, 28/07/2026)

> Passe d'harmonisation OBLIGATOIRE avant phase 4, exécutée par la session A/C sur les
> branches `feat/plu-nuit-a`, `feat/plu-nuit-b` et `feat/plu-nuit-verif` (commits dédiés
> identiques dans l'intitulé, ce rapport identique sur les trois branches).
> Règle unique arbitrée : **la lecture la plus conservatrice gagne** (celle qui sous-estime
> la constructibilité). Elle tranche les deux doctrines en sens opposés.

## Doctrine a — % « espace vert et perméable » gravé dans pleine_terre_pct (A/C gagnent)

Graver `null` quand le règlement impose un % perméable revenait à ne poser aucune
contrainte (optimiste). **B se réaligne : le % est gravé, avec le libellé exact du
règlement en verbatim dans la source** (« espace vert et perméable », PAS « pleine
terre »). A et C rétro-annotent leurs sources de la même façon. Schéma v2 (plus tard) :
champ distinct `espace_permeable_pct`.

### Lot B — harmonisé par la SESSION B elle-même (79 zones, commit 7fd6244)

**Coordination constatée a posteriori** : la session B, ayant reçu le même arbitrage, a
poussé sa propre passe (79 zones sur 6 communes + doctrine b sur 13 zones Bras-Panon/
Trois-Bassins) pendant que je préparais la mienne. **Vérification croisée : les 79 valeurs
de B sont STRICTEMENT identiques à ma table dérivée indépendamment (0 écart)** — deuxième
convergence en aveugle de la nuit. Ma passe B (préparée sur l'ancienne tête) a été
abandonnée sans push ; la table ci-dessous reste le référentiel de contrôle croisé.

Deltas entre ma table (établie sur l'ancienne tête de B) et la passe de B — consignés,
AUCUNE retouche de ma part sur la branche B :
- **Cilaos (7 zones)** : B a laissé null DÉLIBÉRÉMENT — « espace vert paysager » où les
  stationnements peuvent compter, « jamais un % perméable » (en-tête + srcs du YAML B).
  Lecture défendable (le paysager n'est pas une contrainte de perméabilité) ; ma table
  aurait gravé 10/40 par prudence. → micro-arbitrage Vic : paysager-sans-perméable,
  graver ou non ?
- **Saint-Benoît (24 zones)** : ma table est CADUQUE — le YAML a été refondu (commit
  f55416a) suite à l'arbitrage matinal de Vic sur les hauteurs par secteurs graphiques
  (zones habitat-admis dé-calibrées, habitat-interdit en zones_au_st) ; les entrées visées
  n'existent plus.

### Table de contrôle croisé (établie indépendamment, validée 79/79 sur les communes gravées par B)

| Fichier | n | Détail zone ∅→valeur |
|---|---|---|
| bras_panon | 14 | Ua ∅→30 ; Ub ∅→30 ; Uba ∅→30 ; Uc ∅→30 ; Ud ∅→40 ; Udu ∅→40 ; Ue ∅→20 ; 1AUa ∅→30 ; 1AUb ∅→30 ; 1AUc ∅→30 ; 1AUd ∅→40 ; 1AUe ∅→20 ; 1AUec ∅→20 ; 1AUt ∅→30 |
| cilaos | 7 | Ua ∅→10 ; Uah ∅→10 ; Ub ∅→40 ; Ub1 ∅→40 ; AUb ∅→40 ; AUb1 ∅→40 ; AUb2 ∅→30 |
| la_plaine_des_palmistes | 9 | Ua ∅→20 ; Ub ∅→40 ; Uc ∅→50 ; Ur ∅→50 ; Ue ∅→25 ; AUb ∅→40 ; AUc ∅→50 ; AUr ∅→50 ; AUe ∅→25 |
| le_port | 5 | Ub ∅→10 ; Ud ∅→20 ; Uem ∅→20 ; Umi ∅→20 ; 1AUem ∅→20 |
| les_avirons | 19 | Ua ∅→15 ; Ub ∅→30 ; Ub1 ∅→30 ; Ub2 ∅→30 ; Ub3 ∅→30 ; Ub4 ∅→30 ; Uc ∅→30 ; Uc1 ∅→30 ; Uc3 ∅→40 ; Ud ∅→40 ; Ud1 ∅→40 ; Ud2 ∅→40 ; Ud3 ∅→40 ; Ue ∅→30 ; AUa ∅→15 ; AUc ∅→30 ; AUd ∅→40 ; AUec ∅→30 ; AUt ∅→30 |
| les_trois_bassins | 9 | Ua ∅→20 ; Uaa ∅→20 ; Ub ∅→30 ; Uc ∅→40 ; Ue ∅→25 ; 1AUa ∅→20 ; 1AUb ∅→30 ; 1AUc ∅→40 ; 1AUt ∅→30 |
| saint_benoit | 24 | Ua ∅→20 ; Uap ∅→20 ; Ub ∅→20 ; Ue ∅→20 ; Up ∅→20 ; Ut ∅→20 ; AUa5 ∅→20 ; AUa8 ∅→20 ; AUa9 ∅→20 ; AUa18 ∅→20 ; AUb2 ∅→20 ; AUb6 ∅→20 ; AUb7 ∅→20 ; AUb10 ∅→20 ; AUb11 ∅→20 ; AUb12 ∅→20 ; AUb13 ∅→20 ; AUb14 ∅→20 ; AUb15 ∅→20 ; AUb16 ∅→20 ; AUb17 ∅→20 ; AUb19 ∅→20 ; AUe3 ∅→20 ; AUp1 ∅→20 |
| saint_louis | 24 | UA ∅→15 ; UB ∅→20 ; UC ∅→25 ; UC1 ∅→25 ; UC2 ∅→25 ; UD ∅→30 ; UD1 ∅→35 ; UE ∅→15 ; US ∅→15 ; UZ ∅→25 ; 1AUa ∅→15 ; 1AUa oap1 ∅→15 ; 1AUa oap3 ∅→15 ; 1AUb1 ∅→20 ; 1AUb2 ∅→20 ; 1AUc ∅→25 ; 1AUc oap4 ∅→25 ; 1AUc oap5 ∅→25 ; 1AUc1 ∅→25 ; 1AUc2 ∅→25 ; 1AUd ∅→30 ; 1AUd1 ∅→35 ; 1AUe ∅→15 ; 1AUe oap1 ∅→15 |

Valeurs = celles des sources B (libellé + %), ou la zone U de renvoi ; tranches à tiroir
au plus conservateur (La Plaine Ue
25 % Bras des Calumets vs 10 % Pyramide → 25 ; Trois-Bassins Ua 20 hors dérogation ;
Bras-Panon 1AUec « 15 % planté ET 20 % perméable » → 20). Restent null À RAISON :
Saint-Louis UA1 (« il n'est pas fixé de règle »), Cilaos Uc (« aucun % d'espaces libres »).

**Extensions signalées** (libellés voisins mais non identiques à « perméable », gravés par
prudence, à confirmer si besoin) : Cilaos Ua/Uah/Ub/AUb* « espace vert paysager » ;
Le Port « éco-aménageable » (coefficient de biotope) ; Saint-Louis UZ « libres et
paysagés » ; La Possession UEm/AUEm « éco-aménageable » (lot A, valeur déjà gravée).

### Lot A + contre-extraction C — 131 rétro-annotations de source (valeurs inchangées)

Chaque `pleine_terre_src` visée porte désormais le libellé exact vérifié dans le texte :
saint_joseph 21 (« espace vert et perméable comprenant des plantations ») ; sainte_marie
10 (« La parcelle doit être perméable sur au moins » — liste 20/25/30 % p.24-25) ;
la_possession 20 (UA « soit planté intégralement en pleine terre, soit… » ; UB
« espace perméable » ; UT « espace perméable planté en pleine terre » = PLEINE TERRE
CONFIRMÉE ; UEm « éco-aménageable ») ; sainte_suzanne 12 ; l_etang_sale 11 (« Au moins
X % de la surface de la parcelle doit être perméable ») ; salazie 10 ; entre_deux 5 ;
sainte_rose 9 ; saint_paul 27 (« pourcentage minimal d'espaces libres perméables » ;
U2*/Usdu : + 50 % de la surface perméable en pleine terre, 3 strates). Contre-extraction C
(hors production) : mêmes annotations sur Saint-Louis et Les Avirons ; Petite-Île déjà
exacte (le règlement y dit « pleine terre » verbatim).

## Doctrine b — retraits « H/2 avec minimum » (B gagne)

Le retrait réel est **max(H/2 à la hauteur maximale autorisée de la zone, plancher)**.
Graver le plancher seul sous-estimait le retrait (optimiste). La friction n°5 du rapport A
était fausse — désavouée dans le rapport A. A et C se réalignent.
Le périmètre réel est **49 valeurs lot A** (pas 10 : les secteurs frères et les renvois
1AU partagent la règle avec des sources sans le mot-clé H/2 — d'où le sous-comptage de la
contre-preuve) **+ 10 valeurs contre-extraction C**. H = hauteur à l'égout gravée de la
zone ; à défaut (groupes « faîtage seul »), H = faîtage (conservateur, noté).

### Lot A — 49 valeurs corrigées (rl = recul limites séparatives, rv = recul voirie, m)

| Fichier | n | Détail zone champ ancien→nouveau |
|---|---|---|
| saint_joseph | 17 | U2 rl 3→5.5 ; U2a rl 3→5.5 ; U3 rl 3→5.5 ; U3a rl 3→4 ; U3ar rl 3→4 ; U4 rl 1.9→3 ; U5 rl 3→3.5 ; U5cv rl 3→3.5 ; U5cvd rl 3→5 ; U5ma rl 3→3.5 ; U6 rl 3→6 ; U6c rl 3→7.5 ; 1AU3 rl 3→5.5 ; 1AU3a rl 3→4 ; 1AU5 rl 3→3.5 ; 1AU6 rl 3→6 ; 1AU6c rl 3→7.5 (U5ru/U5vi/1AU5ru/1AU5vi : H/2 = 3 = plancher, inchangés) |
| sainte_marie | 9 | UA rl 3→7.5 ; UEa rl 4→12 ; UEc rl 4→7 ; UEm rl 4→8 ; UEp rl 4→8 ; UR rl 4→12 ; UT rl 4→5.5 ; UTp rl 4→5.5 ; 1AUep rl 4→8 (groupe activités : H = faîtage seul gravé, conservateur) |
| la_possession | 19 | UA rl 3→8 ; UAa rl 3→4.5 ; UAm rl 3→6 ; UApsfr2 rl 3→6 ; UB rl 3→4.5 ; UBa rl 3→3.5 ; UBb rl 3→3.5 ; UBc rl 3→3.5 ; UBpszc rl 3→3.5 ; UBpsfr2 rl 3→4.5 ; UE rl 3→6 ; UEm rl 3→6 ; UT rl 3→5 ; UTfr2 rl 3→5 ; AUB rl 3→4.5 ; AUBb rl 3→3.5 ; AUBpsfr2 rl 3→4.5 ; AUT rl 3→5 ; AUEm rl 3→6 |
| sainte_suzanne | 4 | UE rv 5→6 ; UE rl 4→6 ; 1AUe rv 5→6 ; 1AUe rl 4→6 |

**Non calculables (3, La Possession)** : UAv, AUAv, AUBm — hauteur `a_verifier` (îlots/
niveaux), H/2 incalculable ; plancher 3 m conservé avec note explicite, à recalculer quand
la hauteur sera arbitrée (micro-arbitrage du matin n°3).

### Contre-extraction C (hors production) — 10 valeurs corrigées (Saint-Louis)

UE rv 5→6, rl 4→6 ; US rv 5→6, rl 4→6 ; 1AUe rv 5→6, rl 4→6 ; 1AUe oap1 rv 5→6, rl 4→6 ;
UC1 rl 3→4.5 ; 1AUc1 rl 3→4.5 — alignées sur B (qui avait juste). Les 17 défauts de C
listés à la contre-preuve restent intacts (preuve d'honnêteté, décision Vic).

### Lot B doctrine b : Saint-Louis vérifié conforme dès l'extraction ; Bras-Panon (12) et
Trois-Bassins (Ue) corrigés par la session B dans sa propre passe (7fd6244).

## Correction incidente (découverte en vérifiant les libellés, hors doctrines)

- **Étang-Salé UBv : pleine_terre 35→50.** Verbatim UB 2.6 : « Au moins 35% de la surface
  de la parcelle doit être perméable. **En secteur UBv, ce seuil est porté 50%** » — le
  35 % gravé au lot A ignorait l'alinéa UBv. Sens conservateur, corrigée et sourcée.

## Remarques consignées (aucune action)

- Sainte-Marie UAz : l'exemption « il n'est pas fixé de règles » (p.24) vise la liste
  espaces libres ; la liste perméable ne cite pas UAz → le 20 % zone UA reste gravé
  (conservateur), signalé ici.
- Les 3 micro-questions de forme restent consignées avec verbatims à la contre-preuve §5
  (tiroir géographique voirie, UF-en-gel, « hauteur absolue ») — arbitrage Vic au matin.
- Impact moteur attendu : doctrine a NE change PAS les capacités calculées du lot A (déjà
  gravé ainsi) mais durcit le lot B ; doctrine b durcit lot A et C. La phase 4 mesurera
  sur base harmonisée unique.

— Session A/C, harmonisation exécutée dans la nuit du 27 au 28/07/2026. Base applicative
jamais touchée. Phase 4 non lancée.

## Post-arbitrages du matin (28/07, Vic réveillé)

- **Exhaustivité doctrine a VÉRIFIÉE** (exigence Vic) : le traitement n'a pas porté que
  sur les 32 cas signalés par la contre-preuve — lot A balayé fichier par fichier (toute
  `pleine_terre_src` sans libellé → 125 annotations, libellés vérifiés dans les textes) ;
  lot B balayé par trois filets complémentaires (% + mot-clé perméable/paysager ; null
  sans % ; % à libellé atypique « éco-aménageable ») puis re-balayé sur la tête après la
  passe de B : il ne restait que la classe « paysager » ci-dessous. C annoté. Aucun cas
  résiduel connu.
- **Classe « paysager » : GRAVER (arbitrage Vic)** — un % de parcelle sans bâti est une
  contrainte d'emprise réelle, stationnements compris ; laisser null sert plus généreux.
  Appliqué sur la branche B (commit dédié, session B informée par le commit) : Cilaos
  Ua/Uah ∅→10, Ub/Ub1/AUb/AUb1 ∅→40, AUb2 ∅→30 ; Saint-Louis UZ ∅→25 (« libres et
  paysagés »). Libellés verbatim en src, en-tête Cilaos mis à jour.
- **Étang-Salé UBv 35→50** : validée par Vic.
- Saint-Benoît : refonte (arbitrage hauteurs par secteurs graphiques) portée par la
  branche B — non touchée ici.

## Vérification élargie « he null » (demande Vic, 28/07 — AUCUNE correction appliquée)

**Le bug redouté n'existe pas, et mon argument n°2 d'hier était INVERSÉ** — correction
honnête : le repli générique 9 m (`he_defaut_generique_m`) ne s'applique QU'AUX zones
absentes du YAML (`plu_rules.py:210`, `calibree=False`). Pour une zone calibrée :
- `he` null + `hf` chiffré → le moteur estime les niveaux depuis hf par
  `max(1, (hf − 3) ÷ 3)` avec avertissement (`engine.py:236-242`) — PLUS conservateur
  que le calcul sur hé (hf 8 → 1 niveau, là où he 8 → 2 niveaux). La forme C sur Ub4
  était donc pessimiste par accident, pas optimiste. La convention he = hf reste juste
  (transcription exacte d'un plafond « en tout point ») mais elle AUGMENTE la capacité
  calculée vs la forme hf-seul — à savoir en lisant les mesures.
- `he` ET `hf` non chiffrés → « capacité non calculable », 0 logement (conservateur).

**Compte sur les 21 YAML** : 43 zones en classe « he null + hf chiffré » (dont ~14
plafonds uniques type « hauteur absolue/totale/fixée à N m sans précision » — candidates
à l'extension de la convention he = hf, décision Vic ; le reste = faîtage seul réellement
réglementé, forme correcte) ; 15 zones « he et hf a_verifier » (capacité non calculable —
attendues : îlots La Possession, Saint-Denis 10 zones AVAP/patrimoine, U1lec Saint-Paul,
AUdma Saint-Pierre). Liste détaillée remise à Vic en session.
