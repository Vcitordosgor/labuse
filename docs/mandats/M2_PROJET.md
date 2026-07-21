# M2 — REFONTE « PROJET » (fenêtre pré-M7)

**Branche `fenetre/m2-projet`.** Un STOP maquette (ci-dessous) + un STOP final après implémentation.
**Vic merge — je ne merge pas.** Zéro touche scoring / runs servis / golden — la refonte réorganise
l'affichage et le flux, elle ne recalcule rien.

---

## 0. Pré-vol

### 0.1 PJ1 (fix cadrage `niveaux`) — ✅ présent dans main
`tests/test_cadrage_niveaux.py` (**7/7 verts**) verrouille le contrat : `niveaux` (gabarit R+n) est
**relocalisé** dans `ampleur.niveaux` au lieu de la racine (que `additionalProperties:false` rejetait), et
`prune_to_schema` retire un champ inattendu au lieu de faire tomber tout l'entretien. On refond donc sur un
entretien de cadrage sain — pas besoin d'en faire le premier commit.

### 0.2 Audit factuel des deux mondes (constat, pas opinion)

**« Ouvrir » (monde A — restitution figée).** Ouvrir un projet déclenche la **re-restitution** : le modèle
`Projet` (`fiche`/`filtres`/`programme` JSONB, `models.py:635`) est rejoué à chaque vue — `POST
/projets/{pid}/rejouer` horodate, `POST /projets/apercu` **ré-exécute** les filtres/programme sur les données
courantes (M22 `faisabilite_sens2` si programme, sinon `q_v2_list` sur `q_v7_defisc`). Affichage :
`ProjetsPanel.tsx` (fiche + chips de critères + mini-compteurs) et `ProjetEntretien.tsx` (entretien copilote
qui construit la fiche). **Aucun statut** n'y est stocké — c'est une lecture recalculée (« rejouer les critères »).

**« Trier les parcelles » (monde B — parcours à statuts).** Le tri vit dans la table **`projet_parcelles`**
(`models.py:665` : `statut` ∈ {proposee, retenue, ecartee, a_analyser}, `rang`, `proposee_at`, unicité
(projet, parcelle)). `POST /projets/{pid}/proposer` remplit en `proposee` (UPSERT, ne réécrit jamais une
décision) ; **`PATCH /projets/{pid}/parcelle/{idu}`** mute le statut et **synchronise le CRM** (`_sync_crm_retenue`
`projets.py:440` : `retenue` → `pipeline_entries` « contact_a_preparer », sinon suppression). Front :
`ProjetKanban.tsx` (déjà **3 colonnes** à trier/retenues/écartées, drag + boutons) et `ParcoursTinder.tsx`
(carte de décision au-dessus de la carte, Retenir/Écarter/À analyser, « chercher plus »).

**La dédup manque (à moitié).** À la création, `_find_doublon` (`projets.py:349`) compare `filtres` (égalité de
dict) OU le nom en minuscules et renvoie l'existant — **soft, jamais bloquant**. Mais **aucun outil de fusion**
des doublons déjà en base, aucune balayage. Cas réel : **4 « Résidence étudiante Ouest »** (ids 15-18, créés le
08/07 entre 19:49 et 19:56, **même hash de filtres**, 0 parcelle triée) ont passé le garde-fou (créés en
quelques secondes / comparaison de dict fragile). Le projet **13 « Résidence étudiante Saint-Paul »** (49
proposées, 8 retenues) est, lui, unique et riche — matière du Kanban.

---

## 1. LA MAQUETTE — 🛑 STOP (validation visuelle Vic avant tout code branché)

**Fichier autonome, ouvrable tel quel** : **`docs/mockups/m2_projet_maquette.html`** (HTML/CSS statiques, JS
seulement pour naviguer entre les écrans). DA existante (`tailwind.config.js` : dark `#060A08`, mint `#5CE6A1`,
**violet premium `#B497F0`**, Inter, couleurs de tier). **Données réelles** (projets 13 + 15-18) — les 4
doublons « Ouest » illustrent la dédup, les parcelles du projet Saint-Paul peuplent le Kanban.

Ce que la maquette montre (4 écrans, barre de nav en haut) :
1. **Liste des projets en cartes** — nom, nb de parcelles par statut, dernière activité ; **dédup visible** :
   les 4 « Ouest » regroupés avec bandeau « doublons détectés » + action **Fusionner** (union parcelles +
   statuts, confirmation explicite, jamais de suppression silencieuse).
2. **Vue projet unifiée — variante A (Kanban plein)** : header projet (nom, cadrage résumé en chips, éditer,
   **Rejouer les critères**, Exporter/CRM) + **mini-Kanban 3 colonnes** (proposées / retenues / écartées) en
   cartes parcelles compactes (vignette IGN, commune, tier, **badges défisc / PC caduc**, surface, mini-actions).
   Bouton **« Trier les parcelles »** = action de la vue.
3. **Vue projet — variante B (colonnes compactes + liste dense)** : le vrai choix à trancher (A = visuel/cartes
   vs B = densité/liste triée par rang).
4. **« Trier » (swipe)** : le parcours Tinder **repositionné** en action de la vue (on ne le réécrit pas) —
   une carte swipée rejoint sa colonne ; même source `projet_parcelles`.

**Convergence** : « Ouvrir » et « Trier » ne sont plus deux mondes — ouvrir un projet = arriver sur cette vue ;
les anciennes recommandations figées peuplent la colonne **proposées**.

**Deux variantes maximum** (A vs B), là où un vrai choix existe. **Aucune implémentation avant ton retour.**

---

## 2. Implémentation — ✅ LIVRÉE (selon la maquette validée + décisions déléguées)

**Convergence** : la vue unifiée (`ProjetKanban`) EST déjà la route projet (« Ouvrir » y mène, PJ3) — la
restitution figée séparée n'existe plus. La refonte porte le **layout hybride**, l'« à analyser », le rejeu
non-perte, la fusion, les vignettes lazy.

**Layout HYBRIDE** (décision Vic) — `ProjetKanban.tsx` :
- **Proposées = variante B** (`ProposeeRow`, liste dense triée par rang) — file de travail qui encaisse 52+
  parcelles ; les items **« à analyser » remontent EN TÊTE** (badge ◑) avec un **filtre rapide dédié**
  (`data-kanban-filtre-analyse`) — **pas de 4ᵉ colonne**.
- **Retenues / Écartées = variante A** (`KanbanCard`, cartes visuelles + **vignette IGN**) — décisions peu
  nombreuses du client. *Aucune incohérence visuelle insoluble → pas de repli sur B-partout.*

**Rejeu non-perte** — `projet_proposer` : au rejeu, une **retenue/à-analyser hors des critères du jour RESTE**
(jamais évincée), marquée **`hors_criteres`** (badge « hors critères actuels », `data-badge-hors`) ; celle qui
rematche est nettoyée. Colonne DB additive `hors_criteres`.

**Fusion des doublons** — `POST /projets/fusionner` + `DedupBanner` (liste projets) : détection par nom
normalisé (≥ 2), **union parcelles + statuts**, règle de conflit **retenue > écartée > à analyser > proposée**,
**conflits SIGNALÉS** dans le résultat (jamais résolus en silence), sources **ARCHIVÉES** (jamais supprimées →
réversible). Cas réel : les **4 « Résidence étudiante Ouest »**.

**Vignettes IGN en LAZY LOADING** — `Vignette` : `<img loading="lazy">` ortho Géoplateforme (WMS
`HR.ORTHOIMAGERY.ORTHOPHOTOS`) centrée sur la parcelle ; placeholder si pas de centre.

**Migration** — `scripts/m2_projet_migration.sql` : `ALTER TABLE projet_parcelles ADD COLUMN IF NOT EXISTS
hors_criteres` — **ADDITIVE et RÉVERSIBLE** (rollback : `DROP COLUMN`), aucun statut touché. Appliquée base
réelle **et** `labuse_test`. **Comptes de statuts IDENTIQUES avant/après** (ecartee 13 · proposee 40 ·
retenue 20) — non-perte prouvée.

**Vocabulaire client** : la vue projet n'affiche **aucun chiffre in-sample en vitrine** (tier + « qualité
X/100 » avec tooltip distinguant P de la complétude). Les tooltips PJ5 `×N` vivent dans le **panneau de
résultats (liste île)** — surface du **Mandat 1**, NON touchée ici (décision de périmètre, pas de scope creep).

### Écarts à la maquette (notés, non improvisés)
- Hybride A/B au lieu d'une variante unique — **conforme à ta décision déléguée**, pas un écart.
- « Trier » : bouton simplifié (label « Trier » au lieu de « Trier les N ») pour l'homogénéité de la tête de
  colonne dense. Cosmétique.

## 3. STOP final

- **Avant/après** : « avant » = deux mondes (§0.2) ; « après » = maquette validée
  `docs/mockups/m2_projet_maquette.html` (design de référence, rendu vérifié). Captures **live** = validation
  visuelle en local (le front `npm run build` passe : bundle `dist/` régénéré).
- **Migration comptée** : statuts identiques avant/après (ci-dessus).
- **Dédup démontrée** sur le cas réel (4 « Ouest ») + cas synthétique **avec conflit** (test).
- **Tests** : suite complète **985 passed / 0 failed** ; **non-perte** + **fusion conflit** (`test_projet_m2`,
  4) ; **contrat cadrage** (`test_cadrage_niveaux`, 7) ; **affichage refonte** (`test_front_m2`, 6). Front
  `tsc -b && vite build` OK.
- **Garde-fous** : zéro touche scoring / runs servis / golden ; écritures DB **additives** (`hors_criteres`,
  archivage jamais suppression). Aucun bug hors périmètre découvert.

**Vic valide visuellement en local, puis merge.** Je ne merge pas.
