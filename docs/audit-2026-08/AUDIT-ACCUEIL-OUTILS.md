# AUDIT — Outils / raccourcis de la page d'accueil

**Date** : 2026-08-24 · **Branche** : `audit/accueil-outils` · **Type** : audit seul (aucun code modifié ; Postgres en lecture ; endpoint `/accueil/chiffres` sondé en `GET`).
**Périmètre** : les entrées « outils / raccourcis » de la page d'accueil et leurs chiffres.
**Méthode** : lecture du code (`LeftPanel.tsx` = `AccueilPreuves`, `AccueilCopilote.tsx`, `store/useApp.ts`, `api/accueil.py`, `outils/registry.ts`) croisée avec la base (run servi `q_v10_m129`) et les valeurs servies en direct.

> App laissée intacte (uvicorn:8000 + vite) : uniquement des `GET` et des `SELECT`.

---

## 0. Le compte : **3 raccourcis**, pas 5

La page d'accueil réelle est `AccueilPreuves` (`LeftPanel.tsx:428`, montée quand `!accueilVu`). Elle expose **3 « portes »** cliquables (composant `Porte`) — pas 5 :

1. **Explorer la carte** (verte) · 2. **Demander au Copilote** (IA) · 3. **Ouvrir un outil** (neutre).

Au-dessus : **3 chiffres** (parcelles / communes / sources), qui sont des *aperçus statistiques* (avec chaîne de données), pas des outils. Une seconde surface d'accueil existe — `AccueilCopilote` (vue Copilote) — mais elle n'a **aucun raccourci-outil cliquable** : un champ de saisie + 4 « capacités » en **texte non cliquable** (décision M133 : « le routeur comprend seul, rien à choisir »). Donc, quelle que soit la lecture, on ne trouve **pas 5 entrées outils** ; l'accueil principal en a **3**. (Le mandat anticipait cet écart — il est signalé ici.)

---

## 1. Tableau

| # | Entrée | Ce qu'elle ouvre (état initial) | Verdict | Constat |
|---|--------|--------------------------------|---------|---------|
| P1 | Porte **Explorer la carte** | `onCommencer` = `setAccueilVu()` + `openFiltres()` → panneau **Filtres** ouvert (`panneauSection='filtres'`, `accueilVu=true`) | ✓ | Entrée « je pars explorer ». ⚠ `openFiltres` ne diffuse PAS `CLOSE_OVERLAYS` (§2.3) — théorique (aucun overlay ouvert à l'accueil). |
| P2 | Porte **Demander au Copilote** | `setView('copilote')` → vue Copilote (`...CLOSE_OVERLAYS`, `outilsOpen=false`, `module=null`) | ⚠ | NE fait PAS `setAccueilVu()` → au retour en vue *cartes*, l'accueil **se ré-affiche** (incohérent avec P1/P3). §2.2. |
| P3 | Porte **Ouvrir un outil** | `setAccueilVu()` + `toggleOutils()` → **rail Outils** ouvert (`view='cartes'`, `module=null`, `...CLOSE_OVERLAYS`) | ✓ | Raccourci vers le MÊME rail Outils que l'en-tête — pas un doublon. Libellé « **13 outils** » = `MODULES.length` (dynamique, exact). |
| C1 | Chiffre **parcelles** = 431 663 | `count(*) parcel_p_score_v2 WHERE run_id=run servi` (cache 1 h) | ✓ | Exact vs carte/filtre (431 663). Animé (compteur 0→n). |
| C2 | Chiffre **communes** = 24 | `count(DISTINCT commune) FROM parcels` | ✓ | Exact (24). |
| C3 | Chiffre **sources** = 58 | `count(*) data_sources WHERE sources_catalog.WHERE_AFFICHEES` | ✓ | Point CANONIQUE partagé avec `/sources` (dynamique, jamais en dur). |
| — | Ligne de fraîcheur (pied) | texte « …Chaque chiffre porte sa date. » | ⚠ | Les 3 chiffres (CaseChiffre) n'affichent **aucune date** → la promesse ne se vérifie pas sur l'accueil. §2.1. |
| — | `AccueilCopilote` (vue Copilote) | champ + 4 capacités **texte** + brief + historique | ✓ | Pas de raccourci-outil ; brief en panneau (focus piégé, Échap, cleanup corrects). Hors « 5 outils ». |

**Cohérence refonte** : la refonte des 13 est **mergée** dans cette base (marqueurs présents : `TEMPS_MILLESIMES`, épingle `tempsPinIdu` ; bouton courrier `data-m02-courrier` retiré). `MODULES.length = 13` (programme, risques, plu, comparer, assemblage, patrimoine, courriers, communes, barometre, permis, promesses, renouvellement, temps) — le libellé « 13 outils » suit donc automatiquement la refonte.

---

## 2. Détail (là où il y a quelque chose à dire)

### 2.1 — « Chaque chiffre porte sa date » : promesse non tenue sur l'accueil ⚠ (faible)
Le pied de l'accueil (`LeftPanel.tsx:464`) affiche « Données à jour — cadastre, PLU, permis, ventes, risques. **Chaque chiffre porte sa date.** » Or `CaseChiffre` (`:396`) ne rend que **le nombre + un label**, sans date ni « i » sourcé. Une version antérieure portait un « i » par chiffre (M55-D stage 9) ; la simplification M87 l'a retiré sans retirer la phrase. Placée juste sous les 3 chiffres, elle se lit comme une promesse à leur sujet — qui n'est pas honorée ici (la date existe bien ailleurs : fiches, page Sources). Pas un faux chiffre (les valeurs sont exactes), mais une phrase qui sur-promet.

### 2.2 — Porte « Copilote » ne marque pas l'accueil comme vu ⚠ (faible)
P1 et P3 appellent `setAccueilVu()` ; P2 (`setView('copilote')`) **non**. `accueilVu` reste `false` → dès que l'utilisateur revient en vue *cartes*, `AccueilPreuves` se ré-affiche (`LeftPanel.tsx:354` `if (accueilVu) return null`). Comportement défendable (« il n'a pas commencé à explorer »), mais **incohérent** entre les trois portes : deux consomment l'accueil, une non.

### 2.3 — `openFiltres` sans `CLOSE_OVERLAYS` ⚠ (très faible / théorique)
`openFiltres` (`:449`) ne diffuse pas `CLOSE_OVERLAYS` (contrairement à `setView`, `toggleOutils`, etc.). À l'accueil, aucun overlay plein écran (Comparaison / table communes / Densifier) n'est ouvert — l'état est neuf — donc P1 ne peut pas laisser de résidu en pratique. Reste une asymétrie de contrat (les autres transitions ferment les overlays, pas celle-ci).

### 2.4 — Chaîne de données des 3 chiffres (RAS, vérifié)
Tous mesurés en base, cache 1 h, `null` → masqué (doctrine, `accueil.py:1-6`). Vérifié en direct : `parcelles=431 663` (= `parcel_p_score_v2` du run servi, identique à la carte/au filtre), `communes=24`, `sources=58` (= `WHERE_AFFICHEES`, identique à `/sources`). **Exactitude 3/3 vs l'outil complet.** La fraîcheur des chiffres suit le run servi (`q_v10_m129`) ; le compte de parcelles ne dépend pas du résiduel (donc insensible à la péremption des tuiles relevée dans AUDIT-CARTE-FOND).

### 2.5 — Doublons avec la bande Outils (RAS)
La porte « Ouvrir un outil » ouvre le **rail Outils** (les 13 modules), le même que l'en-tête — c'est un **raccourci**, pas un outil dupliqué. Les trois portes routent vers trois surfaces distinctes (Filtres / Copilote / rail Outils) ; aucun recouvrement entre elles. Aucun outil de l'accueil ne double un outil de la bande latérale.

### 2.6 — Cycle de vie (RAS)
`toggleOutils` (ouverture) et `setView` diffusent `...CLOSE_OVERLAYS` + réinitialisent `module`/`parcours`/`openProjet`/`iaRestitution` → pas de résidu. Le panneau « brief » de `AccueilCopilote` piège le focus, ferme sur Échap/clic-dehors et nettoie ses écouteurs (`removeEventListener`, `clearTimeout`, restaure le focus).

---

## 3. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Faible** | A1 | Pied « Chaque chiffre porte sa date » alors que les 3 chiffres n'affichent pas de date (§2.1) | Sur-promesse d'honnêteté sous des chiffres pourtant exacts. |
| **Faible** | A2 | Porte Copilote ne fait pas `setAccueilVu` → accueil ré-affiché au retour (§2.2) | Incohérence entre les 3 portes ; friction mineure. |
| **Très faible** | A3 | `openFiltres` sans `CLOSE_OVERLAYS` (§2.3) | Asymétrie de contrat ; non atteignable depuis l'accueil neuf. |
| **Info** | A4 | La page d'accueil a **3** raccourcis, pas 5 (§0) | Le mandat en attendait 5. |

Aucun raccourci cassé, aucun chiffre faux ou périmé, aucun doublon avec la bande Outils, aucun résidu au cycle de vie. Les 3 chiffres sont exacts et dynamiques, la refonte des 13 est reflétée par un compte dynamique.

---

## 4. Correctifs candidats à mandater (non faits)

1. **A1** — Réconcilier le pied : soit **réafficher une date/« i » par chiffre** (comme M55-D stage 9), soit **reformuler** la phrase pour qu'elle ne porte pas sur les 3 chiffres (« chaque donnée de l'app porte sa date », ou retirer la 2ᵉ phrase).
2. **A2** — Ajouter `setAccueilVu()` à la porte « Demander au Copilote » (aligner les 3 portes), OU documenter le ré-affichage comme voulu.
3. **A3** — Faire diffuser `CLOSE_OVERLAYS` par `openFiltres` (cohérence défensive avec les autres transitions).
4. **A4** — Si « 5 raccourcis » est la cible produit, décider quelles 2 entrées ajouter (ou entériner 3) ; sinon, RAS.

---

## 5. Synthèse

La page d'accueil (`AccueilPreuves`) expose **3 raccourcis** (Explorer la carte / Copilote / Ouvrir un outil) et **3 chiffres** (parcelles 431 663 · communes 24 · sources 58) — **pas 5 outils**. La tuyauterie est **saine** : chiffres mesurés, dynamiques, exacts au chiffre près vs la carte/le filtre/`/sources`, cache 1 h, `null` masqué ; les portes ferment les overlays (P2/P3) et le compte « 13 outils » suit la refonte via `MODULES.length` ; aucun doublon avec la bande Outils. **Trois écarts faibles** : le pied sur-promet une date que les chiffres n'affichent pas, la porte Copilote ne consomme pas l'accueil (ré-affichage), et `openFiltres` ne ferme pas les overlays (théorique). Rien de cassé — de l'étiquetage et de la cohérence de transition, pas des faux chiffres.
