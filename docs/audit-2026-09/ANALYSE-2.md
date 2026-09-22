# ANALYSE-2 — Reprise de l'écran Analyse après recette Vic (22/09)

Branche `feat/analyse-1` (à la suite de `c6daed6f`, worktree `labuse-analyse`, ports 8145/5345). Non mergé, scoring servi inchangé.

⚠️ **Maquette absente** : `captures/analyse2/CIBLE-VIC.png` n'était pas jointe au mandat. Le §2 décrivant la structure en détail, l'écran a été reproduit **d'après le texte** ; les captures ci-dessous (cadrées sur le volet gauche) permettent la comparaison à la maquette de Vic.

Règle de preuve : **un point n'est coché qu'après constat à l'écran.** Captures : `captures/analyse2/`. « Avant » = l'état recetté par Vic = les captures ANALYSE-1 (`captures/analyse1-apres/`).

## 0. Étape 0 — VERTE
`pwd` = worktree `labuse-analyse`, branche `feat/analyse-1`, HEAD `c6daed6f`, arbre propre (hors `circuit-sources1` non lié).

---

## 1. Un seul bouton « Comprendre l'analyse » — FAIT (`08-comprendre-panneau.png`)
Les deux boutons « Info classement » / « Info scoring » sont retirés (`LeftPanel.tsx`). Un seul bouton **pleine largeur** sous le bandeau ouvre un panneau (`ComprendreAnalyse`) qui explique, en français client, dans l'ordre :
1. **Le classement LABUSE** — ce que mesure la bande (potentiel constructible réel : ce que le PLU autorise encore, contraintes retirées, faisabilité) ; les 6 catégories colorées (Excellente · Bonne · À étudier · Faible · **Non retenue** · Analyse incomplète) ; ce qui fait monter / descendre.
2. **Le signal de mutation** — des signes que la parcelle pourrait bouger dans les 12 mois (Fort / Moyen / Faible) ; un indice, pas une promesse ; il **ne change jamais la bande**.
3. **La logique de l'analyse** — filtres → Analyser → une liste par bande puis par signal ; relancer si la sélection change.

Vérifié au navigateur : le panneau contient les 3 sections, mentionne « relancez », et **ne contient aucun mot de l'ancien moteur ni chiffre de probabilité** (test `/Priorité|À suivre|Sans signal|Écartée|probabilit|1\/5|palier/` → **aucune occurrence**).

---

## 2. Structure de l'écran = la maquette — FAIT (`01-structure.png`)
Dans l'ordre, vérifié à l'écran :
bandeau « ✓ Analyse LABUSE affichée · commune · Retour » → **bouton « Comprendre l'analyse »** (pleine largeur) → titre **RÉSULTATS** → **encart** « LABUSE a analysé les N parcelles de votre sélection » + **5 compteurs** (Excellente · Bonne · À étudier · Faible · **Non retenue**) + **barre colorée** → bloc **CLASSEMENT LABUSE** (Excellente · Bonne · À étudier · Faible · Tous) → bloc **SIGNAL DE MUTATION** (Fort · Moyen · Faible · Tous) → ligne « **N parcelles correspondent à vos filtres** » + « **Trier par potentiel** » → cartes → pied « X / N constructibles · Voir 200 de plus → ».

Carte parcelle (inchangée depuis ANALYSE-1) : référence cadastrale courte · badge bande · badge Signal · pastille zone · adresse · surface · commune · ▲ ce qui monte / ▼ ce qui baisse (2-3 lignes) · clic → fiche.

**Décision de cadrage (à valider Vic)** : les **5 compteurs** de l'encart = 4 bandes + Non retenue ; « Analyse incomplète » (NC) n'est PAS un compteur (l'analyse n'a pas *conclu*) — elle vit dans son groupe de fin de liste. Le « N » de l'encart = somme des 5 (parcelles classées), pas NC.

---

## 3. Deux filtres qui MARCHENT — FAIT et PROUVÉ
**Classement** (bande de qualité, ou Tous) et **Signal** (ou Tous) sont deux groupes **indépendants et combinables (ET)**. « Tous » toujours **en dernier**, actif = vert opaque. Le compteur « N correspondent à vos filtres » ET le pied « X / N » dérivent d'un **crosstab unique** (`bandes_signal`, un seul `GROUP BY` serveur) → ils ne peuvent pas se contredire.

**Bug constaté (capture 1) corrigé.** « Signal = Fort seul → 0 / 2 216 » était, sur Entre-Deux, la **vraie donnée** (0 parcelle Fort) mais présentée de façon incohérente (dénominateur = tous les constructibles). Désormais :
- Le compteur reflète le filtre : Fort seul (île) → **62 / 62** (`02-signal-fort.png`), plus jamais « 0 / 2 216 ».
- Quand un couple ne matche personne, l'écran le **dit honnêtement** au lieu d'un vide muet : Entre-Deux + Fort → « Aucune parcelle constructible à signal fort dans cette sélection. Les parcelles Non retenue et Analyse incomplète restent consultables ci-dessous. » (`07-entredeux-fort-vide.png`).

### Tableau des 20 combinaisons (île entière, run candidat `q_v15`)
Source : le crosstab `bandes_signal` servi par `/filtre` — **exactement** ce que le front lit pour son compteur.

| Classement \ Signal | Fort | Moyen | Faible | **Tous** |
|---|---:|---:|---:|---:|
| Excellente | 7 | 19 | 5 054 | **5 080** |
| Bonne | 16 | 81 | 26 740 | **26 837** |
| À étudier | 19 | 82 | 39 121 | **39 222** |
| Faible | 20 | 103 | 74 168 | **74 291** |
| **Tous** | **62** | **285** | **145 083** | **145 430** |

**Invariants vérifiés (programmatiquement + à l'écran) :**
- Somme des 4 bandes (colonne Tous) = 5 080 + 26 837 + 39 222 + 74 291 = **145 430** = total constructibles. ✓
- Fort + Moyen + Faible (ligne Tous) = 62 + 285 + 145 083 = **145 430** = Tous/Tous. ✓

**Combinaisons confirmées au navigateur** (le front affiche le chiffre attendu du tableau) :
| Combinaison | Attendu | À l'écran | Capture |
|---|---:|---:|---|
| Tous · Tous | 145 430 | 145 430 | `01-structure.png` |
| Tous · Fort | 62 | 62 / 62 | `02-signal-fort.png` |
| Excellente · Fort | 7 | 7 / 7 | `03-excellente-fort.png` |
| Faible · Faible | 74 168 | 74 168 | `04-faible-faible.png` |
| Tous · Moyen | 285 | 285 | `05-tous-moyen.png` |
| Entre-Deux · Tous · Fort | 0 | 0 (vide honnête) | `07-entredeux-fort-vide.png` |

Quand un Classement précis (≠ Tous) est choisi, les groupes de fin (Non retenue / Analyse incomplète) sont masqués (ce ne sont pas cette bande) — vérifié (`endGroups=false` sur Excellente).

---

## 4. Vocabulaire — FAIT
« Sans potentiel constructible » → **« Non retenue »** partout : `status.ts` (`BANDE_META['0'].label`, source unique → liste, encart, fiche, panneau Comprendre) et `config/score_labuse.yaml` (`vocabulaire_client."0"`). La clé technique (bande `0`) est inchangée. Vérifié à l'écran : encart « … Non retenue » (`01-structure.png`), groupe de fin « Non retenue », panneau Comprendre « Non retenue — aucun droit à bâtir résiduel identifié ».

---

## 5. Portes
- `tsc -b` : **vert**.
- `vitest run` : 177 passés, **3 échecs PRÉ-EXISTANTS** (`admin/circuit/Detail.test.tsx` ×2, `admin/Donnees.test.tsx` snapshot), 0 nouveau — identiques à ANALYSE-1.
- `pytest` (labuse_test) : `test_m45_filtres` + `test_api_q_v2` + `test_etage0_filtre_dur` + `test_coherence_run_fiche` = **31 passés, 0 échec** (crosstab `bandes_signal` guardé : table absente de `labuse_test`).
- Navigateur : structure, 6 combinaisons, bug corrigé, panneau Comprendre, rename — vérifiés à l'écran.

---

## 6. Reste à trancher / signalé à Vic
1. **Maquette non fournie** : reproduction d'après le texte du §2. Merci de comparer les captures et de renvoyer `CIBLE-VIC.png` si un détail (espacement, ordre exact des blocs, présence de NC dans l'encart) diverge.
2. **NC hors des 5 compteurs** : « Analyse incomplète » n'est pas un compteur de l'encart (choix « 5 compteurs ») ; elle reste visible dans son groupe de fin. À confirmer.
3. **« Trier par potentiel »** : rendu comme un libellé (l'ordre de l'Analyse est fixe : bande puis signal), pas un menu déroulant. À confirmer si Vic voulait un vrai sélecteur.
4. **Groupes de fin masqués sous Classement précis** : quand on filtre sur une bande, Non retenue / Analyse incomplète disparaissent (cohérent, mais à valider).

## 7. Hors mandat (non touché)
Le moteur · les filtres globaux · la fiche parcelle au-delà du libellé « Non retenue » · merge · bascule.
