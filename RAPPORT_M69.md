# RAPPORT M69 — Bug tri par surface (PART A) + alignement du vert de marque (PART B)

Branche `feat/m69-tri-et-vert` (depuis `main` = `39177412`, M61+M68 mergés). Mesures au runtime + audit
statique. **STOP** après diagnostic (PART A PHASE 0) et mesure (PART B) — arbitrage avant correction.

---

# PART A — Le tri par surface ne trie pas

## PHASE 0 — Diagnostic (mesuré)

### 1. Où le tri est-il appliqué ? → DEUX points, selon le mode
- **Mode ÎLE** (île entière ou ≥2 communes) : tri **CÔTÉ SERVEUR** (SQL), endpoint `/filtre`
  (`app.py:1555`) → `_q_v2_list` (`app.py:1911`). Le front n'y re-trie pas (`serverRows` = `.flat()`
  des pages, `ResultsSection.tsx:218`).
- **Mode COMMUNE** (une seule commune sélectionnée — **le cas du mandant : Saint-Paul**) : tri **CÔTÉ
  CLIENT**, `Array.sort` sur le GeoJSON (`ResultsSection.tsx:266-282`), données de `/map/parcels.geojson`.

→ Il y a donc **deux points de tri** (client mode-commune + serveur mode-île). Ils partagent la même
logique (groupement par tier, cf. ci-dessous) mais sont **deux implémentations** qui peuvent diverger.

### 2. Colonne / type — PAS un tri lexicographique
- Colonne = `parcels.surface_m2`, type DB = **Float / double precision** (`models.py:77`).
- Sérialisation JSON = `round(...)::int` → **int** (mesuré : `type(surface_m2[0]) = int`).
- Côté TS = `number | null` (`types.ts`). **Donc numérique de bout en bout** — l'hypothèse « surface en
  texte triée lexicographiquement » est **écartée** par la mesure.

### 3. Page ou jeu complet ?
- Mode commune : le GeoJSON charge **toutes** les parcelles (159 < cap 60000) ; tri client sur le jeu
  complet, puis slice d'affichage `CAP=200` (159 < 200 → tout affiché). **Pas un fragment de page.**
- Mode île : pagination serveur 200/page (non concerné ici).

### 4. Sens de la flèche ↓
`Surface ↓` → `sort=surface` (DESC). Re-clic → `surface_asc`. **Sens correct.**

### 5. La CAUSE (mesurée) — le GROUPEMENT PAR TIER
Quand l'**analyse LABUSE est active**, la liste est **groupée par tier D'ABORD**, le tri choisi
s'appliquant **DANS chaque groupe** (M55-H point 5, décision Vic) :
- Client (`ResultsSection.tsx:268-272`) : `if (analyse) { … GROUPE_ORDER(a) - GROUPE_ORDER(b) }` puis
  `if (sort==='surface') return (b.surface_m2 ?? -1) - (a.surface_m2 ?? -1)` (l.275).
- Serveur (`app.py:1923-1924`) : `if groupes: order = f"{_TIER_GROUPE_SQL}, {order}"` (préfixe tier).

Le comparateur de surface est **correct** (numérique décroissant) ; c'est le **préfixe de groupement par
tier** qui rend l'ordre non-global. Mesure LIVE `/filtre` (Saint-Paul, `limit=200`) :
- `sort=surface&groupes=1` → `[434, 434, 391, 380, …]` **tous brûlantes** — monotone global = **False**.
- `sort=surface&groupes=0` → `[218474, 59718, 59489, …]` tiers mélangés — monotone global = **True**.
- `sort=surface_asc&groupes=1` → `[106, 109, 148, 180, …]` brûlantes croissant — global = False.

Le « 148 · 2348 · 2302 » du mandant = son sous-ensemble filtré (159), groupé par tier : 148 = plus grande
surface de la première famille (brûlante), 2348/2302 = famille suivante (chaude), etc.

### 6. Les autres colonnes / listes
- **« Probabilité de vente » (rang)** : le rang est **corrélé au tier** → le groupement ne le désordonne
  pas → il *paraît* trié. C'est pourquoi le défaut ne se voit que sur les tris **non-rang** (surface).
- **CRM** (Kanban) = tableau par statut, aucun tri surface/proba. **Projets** (`ProjetsPanel.tsx:185`) =
  tri par activité (date), mécanisme distinct. **Comparateur** = aucun tri. → Le défaut est **spécifique
  à la liste de résultats** (tri non-rang en mode analyse).

**Conclusion PART A** : ce n'est pas un tri en double qui se contredit, ni un type texte, ni une
pagination — c'est le **groupement par tier** (voulu M55-H) qui prive le tri surface d'un ordre global.

## PHASE 1 — proposée (à valider en arbitrage)
Rendre le tri surface **global et monotone** (les deux sens) sur tout le jeu : **retirer le groupement
par tier quand une colonne explicite est triée** (surface / surface_asc), en le conservant pour le tri
par défaut (rang). Unifier client (mode commune) et serveur (mode île) sur ce comportement (un seul
comportement de tri). Test de non-régression : assertion de monotonie croissante ET décroissante sur les
159 (et sur l'île).

**ARBITRAGE demandé (PART A)** : M55-H point 5 (Vic) groupe volontairement par tier en mode analyse.
Rendre le tri surface global **abandonne ce groupement pour les tris colonne** (surface/surface_asc).
Option recommandée : garder le groupement pour le tri RANG (défaut), le lever pour surface/surface_asc.
Confirmer, ou préciser une autre lecture (ex. un sous-libellé « groupé par tier »).

---

# PART B — Un seul vert de marque

## Mesure — audit exhaustif des verts (346 occurrences, 40 fichiers)

### Vert canonique (référence) — conforme partout SAUF Copilote
`#4ADE80` = `--mint` (`tailwind.config.js:24`, `styles/index.css:20`, `lib/tokens.ts`). Correctement
utilisé (marque/action) dans : panneau/filtres, projets (Kanban/Tinder), rail, en-tête, boutons fiche,
loading/error, carte (bouton zoom). ✓

### ÉCART marque/action confirmé — **Copilote `cp-mint #63F2B8`**
`tailwind.config.js:38` `'cp-mint': '#63F2B8'` — **22 usages** dans `components/copilote/` (CopiloteView,
ui, Resultats, FilInstruction, Entonnoir) : titre « instruit », bouton **INSTRUIRE →**, onglets missions
actifs, contours de la zone de saisie, badges de rang, point d'état. C'est **exactement** l'écran nommé
par le mandat (« jamais reçu de passe DA »). → **À ALIGNER sur `--mint #4ADE80`** (via token).

### Verts SÉMANTIQUES — à CONSERVER (portent une information)
| Valeur | Usage | Statut |
|---|---|---|
| `#5CE6A1` | tier « chaude »/st-chaude, viabilité confirmée, équipements (école…), badges « Sourcé/Vérifiée », complétude | sémantique |
| `#4ADE96` | tier « à surveiller »/st-surveiller, ICD haute, potentiel transformation fort | sémantique |
| `#3FB56A` | zonage PLU « N — naturelle » | sémantique |
| `#2E7D52` | limites de communes (carte, mode clair) | sémantique |
| `#4ADE80` | **trait de côte** de la carte (M65 P8 — seul vert de marque autorisé sur carte, porte un sens) | sémantique-carte |
| `#2E6B4F` | `vizGreenDeep` (data-viz, constaté inutilisé) | sémantique |

### Valeurs en DUR marque/action (à passer par le token, sans changer la couleur)
- `LeftPanel.tsx:405` bouton accueil « Commencer » : `bg-[#4ADE80] text-[#06180E]` → `bg-mint …` (le
  #06180E est un mint-on introduit en M65, ≈ `--mint-on #06301A`).
- Copilote : textes sur vert `text-[#08130E]` (CopiloteView:210,340) — near-black sur cp-mint.

### CAS DOUTEUX — **à arbitrer avant de toucher** (non tranchés seuls)
1. **`#5fd0a8`** (`Fiche.tsx:1573,1586`) — filet gauche + flèche de la ligne « fréquence de vente ».
   En dur, aucun token. Accent d'UI (marque ?) ou nuance sémantique de la donnée fréquence ? → arbitrage.
2. **`hover:border-[#2E5A45]`** (`ResultsSection.tsx:41`) — vert sombre au survol d'une ligne de résultat.
   La ligne est interactive (marque) mais la valeur n'est ni `--mint` ni un sémantique connu. → aligner
   sur `border-mint/60` ou conserver ? arbitrage.
3. **Textes sur vert `#08130E` / `#06180E`** vs token `--mint-on #06301A` — trois near-black légèrement
   différents pour « texte sur bouton vert ». Aligner tous sur `--mint-on` ? (ce ne sont pas des « verts »
   à proprement parler mais la cohérence marque le demande.) → arbitrage.

## PART B — après arbitrage
Aligner Copilote `cp-mint` sur `--mint` (via token, zéro valeur en dur), traiter les valeurs en dur
`#4ADE80`/mint-on, trancher les 3 cas douteux. Report DA : tableau valeur/usage/statut (marque-action vs
sémantique) dans `docs/DA-LABUSE.html`. Captures avant/après Copilote + 2 écrans.

---

## Garde-fous (à la livraison, phases 1)
tsc 0 · vitest vert · build vert · console 0 · **test auto qui échoue si le tri redevient non monotone**
(assertion croissant/décroissant) · **aucune valeur verte marque/action en dur** restante.

**STOP — en attente d'arbitrage : (A) lever le groupement pour les tris colonne ? (B) les 3 cas douteux +
confirmation cp-mint→#4ADE80.**
