# RECETTE-12 — la recette de RECETTE-11 (15 travaux)

Branche `fix/recette-12` depuis `fix/recette-11` · worktree `~/Desktop/labuse-recette6`.
Artefacts : `docs/audit-2026-09/captures-recette-12/`. Un commit par travail, poussé à chaque lot.

**La règle de preuve, durcie.** RECETTE-11 avait déclaré « vérifiés » trois travaux qui ne l'étaient
pas (garde Financier, pagination, lignes permis/assainissement) — parce qu'ils avaient été jugés sur le
code, pas sur l'artefact. Ici, **une preuve = une capture d'un vrai navigateur (Playwright sur `:5199`
branché à `:8031`) OU le `pdftotext` du PDF régénéré**. Un test unitaire n'est PAS une preuve (c'est un
garde de régression). Chaque travail porte le chemin de sa preuve.

**Suite.** vitest 207/207 · tsc 0 · pytest : les tests RECETTE-12 verts (spec Apporteur 3, D5 4,
exports2_lot6 réaligné 12) ; **fails PRÉ-EXISTANTS** `test_api::test_m136_exports_ne_crashent_pas` et
`test_dossier::test_pdf_genere_avec_mention` = table `commune_zonage_abc` absente de la base de test
(prouvé identiques sur la base, avant mes changements). 0 régression.

---

## Lot A — Financier

**A1 — la garde bloque vraiment. FAIT.** Cause trouvée en VRAI navigateur (là où RECETTE-11 s'était
trompée en jugeant sur le moteur) : le garde vivait SEULEMENT côté serveur et `gardeBloque` l'avalait
sur panne (`catch → false` = laisse passer) → une 401/coupure ouvrait « Questionnaire enregistré » avec
« Ouvrir le Dossier financier » actif. Correctif : un **garde CLIENT proactif** (`horsMarcheClient`,
mêmes bornes que `financier_bilan._hors_marche` : 20000/8000/12000 €/m² puis bailleur > libre). Sur
l'écran qui porte le champ : « Continuer » **désactivé**, champ surligné, message SOUS le champ,
accordéon « Affiner » ouvert ; « Enregistrer » désactivé dès qu'une valeur (n'importe quel écran) est
hors marché → on ne peut ni atteindre l'écran final ni ouvrir le Financier. Libellé : la valeur « est
incohérente », jamais « elle manque ». Le serveur reste la défense du PDF (422).
**A2 — preuve (EL0157).** `captures-recette-12/A-bloque-5500.png` (bailleur 5 500 → Enregistrer
*disabled*, message « incohérent » sous le champ) et `A-final-3800.png` (3 800 → « Questionnaire
enregistré », bouton doc actif). Script `scripts/_recette12_A_financier.mjs` (restaure 5 500 en fin).

---

## Lot B — Carte et listes

**B1 — la carte grise. FAIT.** Révise l'arbitrage RECETTE-2 S11 (« opacité uniforme 0,72 en analyse »)
pour Sans signal / Écartée : `opinionOpacityExpr` peint SEULES Priorité + À suivre ; tout le reste a une
opacité NULLE (plus d'aplat gris pour ~284 000 parcelles). Contour discret des non-promues au ZOOM seul
(couches `parcels-muet` / `ile-muet`, minzoom 15). *Arbitrage :* le mandat parlait de « 212 parcelles »
sur un sous-ensemble ; à l'échelle île le panneau lit 111 priorité · 1367 à suivre · 284303 sans signal.
**Preuve** (vue île, analyse, Saint-Denis) : `B1-saint-denis-analyse.png` (seules Priorité rouge + À
suivre ambre peintes, le reste noir) et `B1-saint-denis-zoom16.png` (contours discrets au zoom).

**B2 — « 9 sur 72 ». FAIT.** L'API pagine désormais PAR SEGMENT : `/filtre?segment=…` (prédicat
identique aux compteurs `_q_v2_stats`, jamais deux règles), jusqu'à 200 par segment dès le 1er appel ;
`AnalyseSegment` charge ses propres lignes (200/page). **Preuve + temps À CHAUD** (Saint-Denis) :
`B2-permis-pro-63.png` « 63 sur 63 affichées » (ouverture **468 ms**) ; `B2-terrain-nu-200.png`
« 200 sur 6 809 » (**762 ms**) ; `B2-terrain-nu-400.png` « voir 200 de plus » → « 400 sur 6 809 »
(**586 ms**). Tous < 2 s. *Note :* les ~5-6 s observés étaient la 1re requête après REDÉMARRAGE (cache
OS/PG froid, payé par n'importe quelle requête) ; à chaud 0,5-1 s. API vérifiée : 200 lignes/segment,
100 % pures.

**B3 — la phrase du modèle en français. FAIT.** `backtest.phrase_client` : virgule décimale, une
décimale, date JJ/MM/AAAA → « Sur 12 mois de ventes DVF (au **10/08/2026**), les parcelles « À suivre »
se sont vendues **13,3×** … (…: **1,2 %**). » Preuve `B3-phrase-fr.png`. **« 200 à suivre » = SEUIL
VOULU, pas une troncature** : le palier « À suivre » est défini par une PROBABILITÉ
(`config/scoring_client.yaml` : 0,10 ≤ p < 0,20), son compte est un COUNT(*) exact (1 367 sur l'île,
jamais plafonné) ; le seul « 200 » est la fenêtre de page partagée, désormais par segment (B2). Rien à
corriger.

---

## Lot C — LiDAR

**C1 — finir le batch. FAIT.** Batch reprenable relancé sur les 83 dalles restantes → **2 665 / 2 665
dalles**, 0 restante, **aucun échec**. 303 432 mesures par dalle ; 303 452 / 303 452 mesures avec date
de survol (aucune mesure sans date).

**C2 — visible dans la fiche. FAIT.** La hauteur mesurée remonte dans le RÉSUMÉ REPLIÉ du tiroir « Le
bien » (là où la fiche parle du bâti existant, à zéro ouverture) : « …bâti détecté… · faîtage 7 m mesuré
(LiDAR HD, survol septembre 2023) » ; détail complet (faîtage + égout + survol) dans le tiroir ouvert.
Preuve : `C2-le-bien-resume.png` + `C2-le-bien-ouvert.png`.

**C3 — checks parcelle en vrai navigateur. FAIT.**
- `EL0157` : « 7 m au faîtage · 3 m à l'égout — LiDAR HD (survol de septembre 2023) » (`C2-le-bien-ouvert.png`).
  **6,9 → 7,0 m** : RECETTE-10 mesurait par PARCELLE (grille recentrée) ; RECETTE-11 par DALLE sur la
  grille NATIVE IGN 1 km → le p99 diffère du décalage de grille. Validation A1 : Δ faîtage médian 0,10 m
  / max 0,40 m, 50/50 sous ±0,5 m. +0,1 m ici, dans la tolérance ; rendu arrondi au 0,1 m.
- SANS mesure — `97407000AK1074` : « 3,9 m — BD TOPO » (nature ESTIMÉ), AUCUNE mention LiDAR
  (`C3-sans-mesure-AK1074.png`).
- PERMIS postérieur au survol — `97411000BP0788` : Constructibilité › « Marge en hauteur … mesuré au
  LiDAR HD, survol de septembre 2023 ; antérieur au permis du 09/01/2025, **possiblement dépassé** »
  (`C3-permis-posterieur-BP0788.png`).

---

## Lot D — Dossier (EL0157). Preuve = `captures-recette-12/D-dossier-EL0157.txt` (pdftotext).

**D1. FAIT.** §5 : « **22 permis autorisés dans un rayon de 500 m, sur les 24 derniers mois** »
(définition Q7). Compte géolocalisé (`nearby_permits`, `sitadel_permits.geom`, ST_DWithin ; couverture
~98 %). Rayon ET fenêtre écrits.

**D2. FAIT.** §6 : la donnée IRIS s'écrit « **Quartier : X % des logements en assainissement non
collectif (INSEE RP2022)** » — prouvé sur `97411000AB0018` (« Quartier — 9 %… », `D2-dossier-AB0018-iris.pdf`).
*Arbitrage EL0157 :* son ANC vient du **zonage réglementaire GPU** (`zone_anc`, statut='source',
vérifié) — « Assainissement non collectif » est un vrai fait de PARCELLE, ce n'est PAS de l'IRIS.

**D3. FAIT.** §3, la hauteur SUR UNE LIGNE : « Égout 3,0 m mesuré (règle 7,0 m, marge 4,0 m) · Faîtage
7,0 m mesuré (règle 10,0 m, marge 3,0 m) — contrainte qui mord : le faîtage (mesuré au LiDAR HD, survol
de septembre 2023) ». La date n'apparaît plus que **DEUX fois** (ligne de hauteur §3 + sources §10) — 4
avant. *(Cosmétique : le formateur rend « 7,0 m », le mandat écrivait « 7 m ».)*

**D4. FAIT.** §10 : la ligne « Sources : BD TOPO… CoSIA… » (pied) imprimée après les mentions légales est
RETIRÉE (le §10 porte déjà sa liste « Sources et millésimes »). Le §10 se termine sur les mentions.

**D5. FAIT.** Libellés de sources : nettoyeur par MOTIFS (dates variables) + `composer` qui ne fabrique
plus de note client quand le millésime amont manque (cellule vide). **0 occurrence** de « (sentinelle) »,
« typeinf 04 — partiel, non-publiées listées », « proxy », « ENS dép. non public », « passe 05/07/2026 »,
« date d'ingestion… » sur EL0157 ET AB0018 (pdftotext). Garde `tests/test_recette12_d5_sources.py`.

**D6. FAIT.** §9 : « scénario » retiré de la liste (supprimé en RECETTE-10) — 0 occurrence.

---

## Lot E — Apporteur (reconstruit sur une spec fermée)

**E1. FAIT.** `docs/audit-2026-09/EXPORTS/APPORTEUR-SPEC.md` = la liste FERMÉE des lignes autorisées.
Test `tests/test_recette12_apporteur_spec.py` : compare le pdftotext à la spec — toute ligne hors liste
échoue, tout motif INTERDIT échoue (vérifié discriminant : 7 lignes interdites injectées sont bien
rejetées). **Page 1 ajouté** : l'émetteur nommé (nom + téléphone + e-mail), « c'est à cet émetteur que
vous renvoyez vos réponses et vos photos ». **Page 1 retiré** : « Ce qu'on peut y bâtir », « Prix du
secteur », la hauteur LiDAR de « Sur place ». **Questionnaire** : TROIS « L'ESSENTIEL » (prix, bail,
voisines) ; le contact redevient le 1er champ « (obligatoire) » sans étiquette ; « Si loué : sous quel
bail ? » ; photos + « Votre retour » à l'émetteur nommé (plus de « n'imprimez rien »).
*Dernière vente & voisines sur EL0157 :* absentes par **donnée inconnue** (0 mutation DVF ; propriétaire
personne physique → pas de cluster de voisines), pas par branchement manquant.
**E2 — preuve.** `E-apporteur-EL0157.pdf` + `.txt` (pdftotext, émetteur = compte 30 « SCCV Horizon
Austral · 0262 00 00 00 »), page 1 `E-apporteur-page1.png`, test de spec au vert (82 lignes, 0 hors
liste, 0 interdit, 3 L'ESSENTIEL).

---

## Non-merge

Aucun critère de non-merge n'est atteint : la garde Financier bloque (A, prouvé navigateur), la carte
n'est plus grise (B1, prouvé navigateur), aucun segment sous 200 n'est tronqué (B2, prouvé navigateur +
API), l'Apporteur n'imprime aucune ligne hors spec (E, test de spec au vert). **« Ne merge pas. »**
