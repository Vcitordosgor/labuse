# CHASSE-2 — chasse aux erreurs sur les chiffres qui partent en production

Branche `audit/chasse-2` (base `origin/main` `4c6760e4`, VERROUS-FIX-1 mergé) · worktree
`~/Desktop/labuse-chasse2` · 2026-10-05 · LECTURE SEULE (écritures : `docs/audit-2026-10/CHASSE-2/`
et `scripts/chasse/` uniquement). État audité = exactement ce qui part sur le VPS :
résiduel **run 13 (q_v16)** servi, scoring **q_v16** basculé, bandes gravées (SCORING-9).

## Verdict en une ligne

**0 FAUX · 3 DISCORDANT (dont 1 bloquant : D05) · 4 TROMPEUR (dont 1 bloquant : D04) · 4 SALE —
pas de jackpot : 1 DISCORDANT bloquant (la palette carte des filtres rend 0 parcelle pendant que
le compteur dit N) et 1 TROMPEUR bloquant (71 252 parcelles « terrain_exigu » dont la raison n'est
jamais nommée au client).**

Les 45 écarts de CHASSE-1 : **0 réapparition** des 33 corrigés ; les 10 classés-avec-preuve se
re-observent à l'identique (c'est leur définition) ; les 2 arbitrages Vic restent ouverts.

## Top 10 (par gravité décroissante — détail et reproduction dans ECARTS.csv)

1. **D05 DISCORDANT bloquant — `/filtre?idus=1` rend `[]` pour tout filtre.** Le front envoie
   `source=q_v16` (binding vivant `/config/run`) ; le bloc `idus` de `/filtre` joint
   `dryrun_parcel_evaluations` sur ce run **brut** (app.py:2775) alors que la table s'arrête à
   `q_v13_sources1` — compteur, page et stats appliquent la résolution `_cascade_run` (C1), ce
   bloc non. À l'écran Analyse (critère hors-tuiles) : compteur « 42 », carte **0 parcelle
   peinte**, aucun drapeau. Régression silencieuse de la bascule q_v15→q_v16 (q_v11_m137
   peuplait la table : le banc CHASSE-1 passait, il casse aujourd'hui 28/33 combos).
2. **D04 TROMPEUR bloquant — terrain_exigu muet (71 252 parcelles, dont 8 637 nouvelles au
   run 13).** Invariant du mandat violé 70/70 : le client lit « Non retenue · aucune SDP
   résiduelle exploitable » ; ni « terrain exigu » ni la cause de fond (93 % des nouvelles =
   PPR rouge partiel, règle « 0 plutôt qu'incohérence ») n'apparaissent nulle part (`exigu` :
   0 occurrence dans le payload). Témoin parlant : 97409000AK0804, 34 707 m² de SDP au run 10
   → 0 au run 13, aucune explication servie. EXPLIQUE-RUN13 l'avait cadré « à corriger ».
3. **D03 DISCORDANT — la même fiche se contredit sur 71 225 parcelles bâties à cause** :
   bloc Potentiel « Marge SDP non calculée » (sdp ∅) vs Analyse LABUSE sdp = 0. Cause :
   `LEFT JOIN parcel_residuel … AND r.cause IS NULL` (app.py:5792) — le bloc ignore les
   lignes à cause au lieu de les lire.
4. **D07 DISCORDANT — « retirées (30 j) » : 101 et 1 sur le même écran marché.** RADAR-FIX-3
   a corrigé le bloc « Baisses/De retour » (exclusion de l'import initial en bloc) mais pas
   `retirees_30j` du bloc 4-chiffres (`_AGG`, pige/marche.py:36) : les deux s'affichent.
5. **D01 TROMPEUR — le cas AD0554 instruit et reproduit.** Flash ≠ Dossier transitoire =
   plan de situation best-effort sans retry : un 400 WMTS IGN transitoire fait tomber toute la
   carte d'UN rendu ; les tuiles réussies étant cachées sur disque, le rendu suivant est
   complet → l'écart « guérit » seul (c'est le solde-on-heal qu'a vu VERROUS-FIX-1). Reproduit
   du premier coup sur cache froid (`make -C scripts/chasse ad0554`), 400 réel observé.
   « API lancée » augmente la pression IGN mais n'est pas nécessaire. Un client Flash peut
   payer un PDF sans plan quand le Dossier l'a.
6. **D09 TROMPEUR — cibles invraisemblables en bande A** : poste électrique (97416000IA1697,
   score 90), cité résidentielle récente entière (97422000EM0261, « 22 401 m² restants »),
   parc public/château d'eau (97422000BY0569). Calculs conformes aux règles — c'est l'usage
   réel que le score ignore. Orthos dans raw/ortho/. Limite produit à arbitrer.
7. **D06 TROMPEUR — Densifier : puce « écartée » (étage 0) jamais allumée** depuis la bascule
   (même famille que D05 : jointure dryrun au run brut, app.py:6851).
8. **D02 SALE — le libellé d'écart de la recette exports ment** : « le nom commercial diverge »
   est émis pour tout diff pdftotext (la vraie différence d'AD0554 était le plan).
9. **D10 SALE — étages servis plafonnés à 3** (`parcel_filtre_bati.etage`, 59 % des lignes à 3)
   pendant que le run 13 mesure l'égout LiDAR (17/68 parcelles de l'échantillon à ≥ 2 niveaux
   d'écart, jusqu'à R+6 réels).
10. **D08 SALE — deux lecteurs du HARNAIS périmés (pas l'app)** : le décodeur de tuiles exige
    `frontend/node_modules` (absent des worktrees → 3 358 faux écarts DANS la baseline
    committée de CHASSE-1, 6 260 au premier rejeu, 231 vrais une fois le symlink posé) ; le
    compteur SQL `tiers_hauts` reste au vocabulaire q_v11 (`brulante+chaude`) alors que q_v16
    dit `priorite/a_suivre` (l'app, elle, mappe les deux : vérifié Bras-Panon 7 = 7).

(+ D11 SALE : data.geopf.fr instable en rafale, mesuré 24/68 échecs premier passage — le
service dont dépend D01.)

## Angle 0 — les 45 écarts de CHASSE-1 rejoués (état servi q_v16/run 13)

`make -C scripts/chasse chasse` rejoué intégralement (décodeur tuiles réparé — D08).

- **Corrigés (33) : 0 réapparition.** Verrous `tests/test_chasse_fix1.py` 7/7 verts ;
  C07 (protocole 2017-2025) vérifié au front ; C22/C23 : `COUVERTURE.csv` rejoué **identique
  octet pour octet** au committé (le « Non couvert par la source » tient sur les 4 couches,
  sans extension indue) ; C34 (50 pas) : l'invariant naïf passe même à 0 violation au run 13.
- **Classés avec preuve (10) : re-observés à l'identique**, preuves toujours vraies —
  C29 (7 086 doublons DVF amont, inchangé), C30 (19 728 emprises > surface, inchangé ;
  voir D10 pour la face « étages »), C31/C32/C33 (1 date future BODACC), C37, C44 (slivers :
  161 écarts d'arrondi d'affichage sur micro-parcelles du banc — déjà classé), C45.
- **Arbitrages Vic (2) toujours ouverts** : C26 (NULL ≠ 0 au tier — l'invariant `nc_jamais_0`
  que SCORING-8 a posé est VERT à l'île) ; C35 (propriétaires publics au top : 6 au run q_v16
  — Département et communes — contre 10 à q_v11 ; comportement produit inchangé).
- Banc filtres : 28/33 combos cassent compte-vs-liste — ce n'est PAS une réapparition d'un
  écart CHASSE-1, c'est la régression D05 née de la bascule.
- Copilote : **angle non jouable** — l'assistant répond « momentanément indisponible »
  (LLM coupé, plafond agent 0 €) ; le harnais classe l'indisponibilité en refus explicite.
  Rien de servi n'est faux (le client voit l'indisponibilité) ; CHASSE-1 reste la dernière
  mesure réelle (38 OK / 12 refus / 10 hors-fiche).

## Ce qui est prouvé juste (sur l'état exact du VPS)

- **Scoring q_v16 à l'île (431 663 parcelles) : 7/7 invariants neufs à 0 violation**
  (`INVARIANTS2.csv`) — bande = f(score) aux seuils gravés, NC jamais 0 (10 776 NC, toutes
  avec cause), 0 jamais D, bande « 0 » ⇔ SDP 0 ou cause, SDP du score gravé = run 13
  (hors NC, vocabulaire d'absence), couverture pleine 0 manquant/0 orphelin.
- **« Différé » : 39/40 parcelles AU bloquées le disent** (fiche : « zone AU fermée —
  capacité différée ») ; le seul silence (97409000AK0278) vient d'une cause `redhibitoire`
  qui prime — c'est la famille D04, pas une réapparition C06.
- **Étape 0** : circuit verrous 31/32 verts (G8 jaune budget = état connu du commit mergé),
  V6b vert (golden 7 témoins), `/sante/fraicheur` 0 cache périmé, manifeste aligné.
- **5 oracles externes rejoués** (`raw/oracles_rejoues.csv`) : **0 faux** — 67 vrai /
  73 non-vérifiable, soit la photo de la baseline committée de septembre (69/71) ; les
  non-vérifiables sont les mêmes familles (API Carto en timeout, sismicité/radon non servis
  sur la fiche, BAN sans résultat ponctuel).
- **Outils refondus RECETTE-1 (angle 5)** : Assemblage (surface union 2 420 = somme
  cadastrale ; SDP union cohérente), Étude de zone (surface 78 ha = π·0,5² ; permis 36 m
  **9 = 9** au recalcul SQL), Piscines (1 766 servies = total API ; 1 351 à confirmer = API),
  Permis 200 m (**17/40 = 17/40** contre `via_permits_geo`, même table que la fiche).
  Seule l'Évolution du marché casse (D07).
- **Angle 6** : matrice source×commune rejouée **identique** au committé — le correctif
  C22/C23 tient, pas d'extension indue du « Non couvert ».
- **Run 13 face au terrain (angle 3)** : sur les 20 montées 0→A + 50 bâties à forte hausse
  (68 orthos produites, `raw/ortho/`), AUCUN « A sur parcelle manifestement saturée » au sens
  des chiffres SERVIS du run (les taux > 100 % viennent du lecteur non clippé C30, le run
  servi est clippé) ; les montées vérifiées à l'œil sont des parcelles réellement peu bâties
  (ex. 97401000AP0923). Les réserves sont D09 (usage) et D10 (étages plafonnés).
- **Digests (angle 4)** : Radar dry-run → 0 bien du jour → 0 mail ; Veille dry-run → 8 comptes
  tous « ignoré » avec motif explicite — la règle « jamais vide, jamais silencieux » tient.
- **Bilan Excel : n'existe pas** (`_EXCEL_DISPONIBLE = set()` ; le front n'affiche le bouton
  que si l'export existe) — constaté, conforme au mandat.
- **Face-à-face lecteurs** : échantillon CHASSE-1 (627 parcelles, 14 566 comparaisons) =
  231 écarts, tous des familles déjà classées (C44 slivers, C34 labels 50 pas) ou du harnais
  (D08) ; échantillon CHASSE-2 : voir `ECARTS-LECTEURS2.csv` (section ci-dessous).

## Face-à-face sur l'échantillon neuf (718 parcelles)

Banc V6b complet (fiche / SQL / tuiles / contexte commune / croisements / déterminisme) :
**169 écarts (114 INCOHERENT · 55 TOLERABLE) — 0 nouvelle discordance produit**. Triage,
famille par famille, toutes déjà jugées :

- 76 surfaces = arrondi entier de la fiche sur micro-parcelles ≤ 8 m² (C44, classé) ;
- 40 `cinquante_pas` = flags bruts `parcel_flags` vs cascade arbitrée de la fiche — l'info
  EST servie ailleurs sur la fiche (vérifié 97409000AS0135 : « 50 pas » ×4, « pas
  géométriques » ×3, littoral ×7 dans prescriptions/zonage) — famille V6b pré-existante,
  triage CHASSE-1 reconduit ; idem 4 `ravine` ;
- 22 `tiers_hauts_n` = lecteur SQL du banc resté au vocabulaire q_v11 (D08b — l'app mappe
  les deux, Bras-Panon fiche 7 = SQL priorite+a_suivre 7) ;
- 10 `filiation_mere` = artefact du banc (multi-mères : la fiche sert LES DEUX, le banc
  compare meres[0] à une ligne arbitraire — innocenté par CHASSE-1, reconduit) ;
- 6 `zone_plu_lib` = libellé fiche enrichi du marqueur OAP (« 1AUa oap1 » vs « 1AUa ») ;
- 5 dénominations PM = millésime (fiche 2025, table du banc 2024 — la fiche a raison) ;
- 4 `prix_neuf` + 1 `taxe_amenagement` (14 % parcelle en secteur majoré vs 5 % part
  communale par défaut : deux notions, pas une contradiction) + 1 copro = familles
  pré-existantes de CHASSE-1, inchangées.

## Angles non joués (dits comme tels)

- **Copilote** : LLM indisponible (plafond 0 €) — voir angle 0.
- **Bascule structurelle** (`scripts/chasse/bascule.py`) : non rejouable — la base de test
  `labuse_chasse1` a été supprimée en fin de CHASSE-1 et sa recette de semis n'a pas été
  archivée. Couverture compensatoire : V3a vert (manifeste = servi), `/sante/fraicheur`
  0 périmé, G7 0 fuite — et surtout la bascule q_v15→q_v16 RÉELLE vient d'avoir lieu :
  D05/D06 sont précisément les lecteurs que le test de bascule de CHASSE-1 ne couvrait pas
  (le chemin `idus` n'y était pas). Leçon : ajouter `idus=1` au test de bascule quand il
  sera re-semé.
- **PDF sur les 718** : les 8 documents ne sont pas re-rendus par parcelle de l'échantillon
  (coût) ; ils restent couverts par la sonde exports (4 témoins, G7 = 0 fuite) et le verrou
  V6b ; D01/D02 sont les trouvailles PDF de cette chasse.
- **Sismicité/radon des oracles** : notion non servie sur la fiche (déjà le cas à ORACLE-1) —
  non vérifiable tant que la donnée n'est pas servie.
- **G8** : 92 sources vitrine sans contrôle > 7 j (agent sonde plafonné 0 €) — état connu,
  documenté au commit VERROUS-FIX-1, non rejouable ici.

## Échantillon et rejouabilité

`ECHANTILLON.csv` : **718 parcelles uniques** — 200 stratifiées (graine 0,77 ≠ CHASSE-1),
400 pièges (mêmes 20 classes que CHASSE-1, toutes pleines), 118 run 13 (20 montées 0→A de
`reports/scoring-9/`, 50 calculée→terrain_exigu les plus « perdues », 50 bâties à plus forte
hausse de SDP). Tout se rejoue : `make -C scripts/chasse chasse` (qui inclut désormais
`chasse2`) ; le cas AD0554 : `make -C scripts/chasse ad0554` (API lancée requise).
