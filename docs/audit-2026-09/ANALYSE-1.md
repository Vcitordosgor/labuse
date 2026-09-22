# ANALYSE-1 — L'écran de l'Analyse LABUSE pour le nouveau moteur

Branche `feat/analyse-1` (base main après merge `feat/scoring-6`, worktree `labuse-analyse`, ports 8145/5345). Non mergé.
Le scoring **servi** reste `q_v11_m137` ; l'écran Analyse lit la table `score_labuse` du **run candidat `q_v15`** (431 663 lignes), pas le servi.

Règle de preuve : **un point n'est coché qu'après constat à l'écran** (vrai navigateur), pas dans le code. Captures dans `captures/analyse1-avant/` et `captures/analyse1-apres/`.

---

## 0. Étape 0 — VERTE
- `pwd` = worktree `labuse-analyse`, branche `feat/analyse-1`, arbre propre.
- Base = commit de merge `feat/scoring-6` → moteur présent (`src/labuse/scoring/score_labuse.py`, `config/score_labuse.yaml`).
- Table `score_labuse` peuplée : run **`q_v15` = 431 663** lignes exactement.
- Le moteur produit DÉJÀ tout le vocabulaire cible : bandes `A/B/C/D/0/NC`, `signal_niveau` (fort/moyen/faible), `contributions` (`[{sens,libelle}]` FR), `cause` (NC). **Recouvrement 1:1 vérifié** : 431 663 parcelles du run servi ont toutes une ligne `q_v15` (0 sans).

Ventilation île entière (hors slivers <2 m²) : A 5 080 · B 26 837 · C 39 222 · D 74 291 · **0** 270 660 · NC 14 723.

---

## 1. Le parcours cible — FAIT

| # | Point | État | Preuve |
|---|-------|------|--------|
| 1 | Filtres globaux inchangés (chantier FILTRES à part) | ✓ non touchés | — |
| 2 | Bandeau « N parcelles correspondent… » + bouton **« Analyser avec LABUSE »** | ✓ | `avant/…` → `apres/07` |
| 3 | UNE liste unique, classée par **bande** puis **Signal** (lexicographique, jamais un mélange chiffré) | ✓ | `apres/01`, `apres/03` |
| 4 | Filtre propre à l'analyse : **Signal de mutation** Fort / Moyen / Faible (+ Tous en dernier) | ✓ | `apres/04` |
| 5 | Filtres changés après analyse → obsolescence « Votre sélection a changé. Relancez l'Analyse LABUSE. » + **Relancer** | ✓ | `apres/08` |
|   | Écran 1 (récapitulatif « LABUSE a analysé les N parcelles ») **CONSERVÉ** (décision Vic 08/09) | ✓ | `apres/07`, `apres/09` |

**Avant** (`avant/`) : la liste parlait Priorité / À suivre / Sans signal / Écartée, organisée en 4 segments (permis pro / terrain nu / bâti densifier / reste), fraction « 1/10 sous 1 an ».
**Après** (`apres/`) : une liste unique par bande, l'ancien vocabulaire disparu.

---

## 2. Le vocabulaire client (gravé) — FAIT
`frontend/src/lib/status.ts` → `BANDE_META` / `SIGNAL_META` :
- **Excellente** (A) · **Bonne** (B) · **À étudier** (C) · **Faible** (D)
- **Sans potentiel constructible** (bande `0`) — catégorie à part, couleur neutre distincte, jamais confondue avec Faible.
- **Analyse incomplète** (NC) + la cause en français (`apres/10` : « Analyse incomplète — zone non résolue. »).
- Signal de mutation en **badge secondaire** (contour, teinte braise), jamais au même poids visuel que la bande.
- Aucun chiffre brut de score ni de probabilité affiché. Les anciens mots (Priorité / À suivre / Sans signal / Écartée) ont disparu de la liste, du récapitulatif de révélation ET de la fiche parcelle.

---

## 3. Ce que chaque ligne montre — FAIT (`apres/03`)
Référence courte + commune · **bande** (mot + couleur, dominante) · **badge Signal** · surface · **zone** (U/AU/A/N, `parcel_zone_plu`) · les **2-3 contributions FR** les plus fortes (▲ ce qui monte / ▼ ce qui baisse, produites par le moteur).
Fiche parcelle (`apres/11`) : la **bande**, le **Signal**, et les **contributions en entier** (bloc « Analyse LABUSE » à la demande). L'ancienne carte verdict (tier servi) est masquée dès que le nouveau moteur porte un verdict → plus aucun ancien mot sur la fiche.

---

## 4. Règles de DA respectées
- Actif = vert opaque (pills Signal) ; « Tous » **toujours en dernier** dans le groupe Signal.
- Pagination : tout sous 200, puis « Voir 200 de plus » (liste de qualité ET groupes NC / Sans potentiel — `apres/06`, `apres/10`).
- Couleurs **franches**, jamais de camaïeu entre les bandes (vert / bleu / ambre / terracotta ; 0 et NC en gris neutres distincts).
- Le score ne s'affiche **QUE** sur la fiche parcelle et dans l'Analyse ; **jamais dans les 17 outils** (aucun outil touché).

---

## 5. Garde-fous respectés
- **Aucun quota, aucun rang, aucun percentile côté écran** : la bande vient du moteur, servie telle quelle (comptes bruts).
- **Même parcelle = même bande** quels que soient les filtres (la bande est lue sur `score_labuse`, indépendante des filtres).
- **« Analyse incomplète »** ne descend jamais tout en bas comme si elle était mauvaise : groupe dédié **au-dessus** de « Sans potentiel », signalé comme incomplet avec sa cause (`apres/10`).
- **« Sans potentiel constructible »** (peut être très élevé, 270 660 sur l'île) : jamais masqué, groupé en **fin de liste** avec son compte (`apres/05`).

---

## 6. Ce qui a été fait, techniquement

### Backend (`src/labuse/api/app.py`)
- `SCORE_LABUSE_RUN` (env `LABUSE_SCORE_RUN`, défaut `q_v15`) — le run candidat lu par l'écran.
- Tri `labuse` (lexicographique) : `_BANDE_RANG_SQL` (A>B>C>D>NC>0) puis `signal_p` décroissant puis SDP puis IDU (ordre **total**), dans `_Q_V2_ORDERS` + `_Q_V2_ORDERS_PAGE`.
- `_q_v2_list` : jointures `score_labuse` + `parcel_zone_plu` (**conditionnelles** via `_score_labuse_ready`/`_zone_plu_ready` → NULL typé sur base nue) ; colonnes bande/signal/contributions/cause/zone servies ; filtres **propres à l'Analyse** `signal` (fort/moyen/faible) et `bande` (qualite/nc/zero, ce dernier lève l'exclusion étage 0 du run servi pour ne jamais masquer « Sans potentiel »).
- `_q_v2_stats` : ventilation par **bande** (`bandes`, `bande_total`) sur la trame entière — guardée.
- `/filtre` : params `sort=labuse`, `signal`, `bande`.
- `/parcels/{idu}` : `analyse_labuse` (bande/signal/contributions/cause) attaché à la fiche — guardé (`db is None` + table absente).

### Front
- `status.ts` : `BANDE_META`, `SIGNAL_META`, `BANDE_ORDER`, helpers.
- `api.ts` : `SortKey` +`labuse`, `FiltreReponse.bandes`, `getAnalyse(filters, bande, {signal})` (sans filtre tier de l'ancien classement), `getAnalyseStats`.
- `filters.ts` / `types.ts` : nouveaux champs `ParcelProps` / `Fiche.analyse_labuse`.
- `ResultsSection.tsx` : mode analyse ré-écrit — récapitulatif par bande + barre, filtre Signal, liste unique (en-têtes de bande A→D), groupes repliables « Analyse incomplète » puis « Sans potentiel constructible ». Segments (permis pro / terrain nu…) retirés de l'écran Analyse. `AnalyseCard` / `AnalyseBandeGroup` / `ContributionsRow` / `BandeHeader` ajoutés.
- `FiltreLabuse.tsx` : récapitulatif de révélation en bandes (lu sur la trame `freshTrame.bandes`) ; ancienne ventilation tier + `on`/`fresh`/`defTip` retirés.
- `strings.ts` : « Analyser avec LABUSE », obsolescence « Votre sélection a changé. Relancez l'Analyse LABUSE. ».
- `Fiche.tsx` : carte « Analyse LABUSE » (bande + Signal + contributions en entier) ; ancienne carte verdict masquée quand le nouveau moteur est là.

### Portes
- `tsc -b` : **vert**.
- `vitest run` : 177 passés, **3 échecs PRÉ-EXISTANTS** (`admin/circuit/Detail.test.tsx` ×2, `admin/Donnees.test.tsx` snapshot) — **confirmés identiques sur la base stashée**, 0 nouveau, aucun rapport avec ANALYSE-1.
- `pytest` (labuse_test) : `test_m45_filtres` + `test_api_q_v2` + `test_etage0_filtre_dur` + fiche/verdict = **48 passés, 0 échec** (jointures `score_labuse` guardées : la table est absente de `labuse_test`).
- Navigateur : parcours complet vérifié à l'écran (captures avant/après).

---

## 7. Reste à trancher par Vic
1. **Placement de « Analyse incomplète » (NC)** : rendu **entre Faible et Sans potentiel** (garde-fou « jamais tout en bas comme si mauvaise » respecté, car 0 est en dessous). À valider : certains préféreront peut-être NC **en tête** (à traiter) plutôt qu'en fin. Réversible en une ligne (`_BANDE_RANG_SQL`).
2. **Périmètre de l'Analyse vs étage 0 du run servi** : le groupe de bande lève l'exclusion étage 0 (sinon les ~145 k écartées du run servi disparaîtraient). Conséquence : l'Analyse montre TOUTE la bande du candidat (dont « Sans potentiel » = 270 660 sur l'île). Conforme au mandat (« ne pas masquer »), mais à confirmer.
3. **Compteur « X / Y constructibles » sous filtre Signal** : le dénominateur Y reste le total constructible non filtré (X = ceux qui matchent le Signal). Lisible (« 5 sur 1 857 »), à valider.
4. **Carte verdict de l'ancien moteur sur la fiche** : masquée dès qu'`analyse_labuse` existe. Ses sous-blocs (réglette « ×N vs moyenne », fréquence par tier, « pourquoi ce score ») étaient de l'ancien moteur et **tombent avec elle** — à re-brancher sur le nouveau moteur si souhaité (hors mandat ANALYSE-1).
5. **Couleurs des bandes** (`BANDE_META`) : A menthe #5CE6A1 · B bleu #46A0E0 · C ambre #E8B23A · D terracotta #C4653C · 0 gris-vert #5C7268 · NC gris-bleu #8A8FA0. Franches et distinctes ; à valider par la DA.
6. **Run candidat** : `q_v15` en dur (env `LABUSE_SCORE_RUN`). À figer/versionner au moment de la bascule.

## Hors mandat (non touché)
Le moteur (score/seuils/cascade), les filtres globaux (chantier FILTRES), `golden promote`, la bascule, le déploiement, les exports PDF.
