# M12 — LOT G · Finitions

Branche : `fix/m12-g-finitions` (worktree isolé). Ne pas merger. Zéro touche scoring.

## Résumé par point

| Point | Statut | Fichier(s) |
|-------|--------|-----------|
| G1 — Fausse erreur au misclic | **Fait** | `MapView.tsx`, `useApp.ts`, `Fiche.tsx` |
| G2 — Bouton « Zone » (GARDÉ, clarté) | **Fait** | `MapToolbar.tsx` |
| G3 — « 2000-2005 » sur deux lignes | **Fait** | `MapToolbar.tsx` |
| G4 — Retrait « Imprimer » (Sources) | **Fait** | `SourcesPage.tsx` |
| G5 — CRM colonnes rognées + compteur tronqué | **Fait** | `Kanban.tsx` |
| G6 — CRM colonnes vides ~800 px | **Fait** | `Kanban.tsx` |

---

## G1 — Fausse erreur au misclic

### Cause racine
Dans le handler de clic parcelle de `MapView.tsx`, l'idu était extrait par
`const idu = String(f.properties?.idu)`. Quand la feature cliquée n'a pas de propriété `idu`
(clic hors-parcelle, tuile vectorielle encore en chargement, trame « promues seulement »),
`f.properties?.idu` vaut `undefined` → `String(undefined)` produit la **chaîne littérale
`"undefined"`**. Cet idu bidon était passé à `select("undefined")`, ce qui :
1. ouvrait la fiche avec le titre `undefined` (le header affiche `{idu}` tel quel) ;
2. déclenchait `getFiche("undefined")` → 404, rendu par le bloc d'erreur générique qui
   affichait « Connexion au serveur impossible — vérifiez votre réseau » + « Parcelle undefined
   absente du run ». **Ce message MENTAIT** (ce n'était pas une panne réseau) et sa tonalité
   rouge « erreur » laissait croire que l'app était cassée.

### Correctif (3 niveaux, défense en profondeur)
1. **`MapView.tsx`** — le handler abandonne silencieusement le clic si `f.properties?.idu` est
   `null` / `''` / `'undefined'` : **la fiche ne s'ouvre plus du tout**. Le clic universel
   (`parcelAt`, plus bas) prend le relais si un point→parcelle est réellement résoluble (il
   gardait déjà `if (r.idu)`).
2. **`useApp.ts`** — filet global : `select('' | 'undefined')` → `selectedIdu: null` (ferme la
   fiche). Quel que soit l'appelant, un idu vide/`"undefined"` n'ouvre jamais la fiche.
3. **`Fiche.tsx`** — le bloc d'erreur distingue désormais un **404** (`ApiError.status === 404`,
   parcelle hors périmètre : copro non classée, hors run) d'une vraie panne réseau. Le 404
   affiche un message **neutre, sans style d'erreur** (`data-fiche-hors-run`, bordure/fond
   surface-2) : « Cette parcelle n'est pas dans le périmètre analysé. Sélectionnez une parcelle
   sur la carte… » + bouton « Fermer ». La tonalité rouge « serveur injoignable » est réservée
   aux vraies erreurs réseau / 5xx. Le titre `undefined` est éliminé à la source (guards 1 & 2).

### Comportement obtenu
- Clic hors-parcelle / carte en chargement → **rien ne s'ouvre** (pas de panneau fantôme).
- Fiche d'une parcelle hors run (404 légitime) → message **neutre**, invite à re-cliquer, aucun
  faux « réseau ».

## Observation (rapport uniquement — NON corrigé)
Le libellé de run servi affiché est **`q_v7_defisc`** (`frontend/src/lib/api.ts` :
`SOURCE = import.meta.env.VITE_RUN_LABEL ?? 'q_v7_defisc'`). Le mandat mentionnait `q_v6_m8`
comme run de référence. D'après l'historique (bascule Phase A-1 défisc, clôture A1), `q_v7_defisc`
est le run servi **intentionnel et courant**, aligné sur le backend `Q_A_RUN_LABEL`
(test `test_run_serving_coherence`) ; `q_v6_m8` est la cible de **rollback** documentée
(`A1_BASCULE_ROLLBACK.md`). La mention `q_v6_m8` du mandat semble donc dater d'avant la bascule.
**Aucune modification faite** — à confirmer par Vic si un rollback est souhaité.

## G2 — Bouton « Zone » (DÉCISION AUDIT A7 : GARDÉ)
Le bouton et sa fonction sont **conservés** (il est intentionnellement désactivé en vue « Toute
l'île » et fonctionne dès qu'une commune est choisie — `off = t.key==='zone' && ile`). Seule
amélioration de clarté de l'état désactivé (`MapToolbar.tsx`) :
- tooltip explicite au survol même à l'état off (avant : `title={off ? undefined …}` = aucun
  indice) → « Zone — disponible après avoir choisi une commune (sélecteur en haut) » ;
- curseur `cursor-help`, couleur inactive plus lisible (hover → st-creuser) ;
- petite pastille **🔒** en coin d'icône = affordance « verrouillé, une action le débloque » ;
- hint au clic reformulé pour **guider vers le sélecteur de commune** : « Choisissez d'abord une
  commune (sélecteur en haut) pour dessiner une zone ».
Bouton et logique inchangés. `aria-label` mis à jour en cohérence.

## G3 — « 2000-2005 » sur deux lignes
Les libellés d'années (« Actuelle / 2000-2005 / 1950-1965 ») sont rendus dans le bloc **« Remonter
le temps »** du sélecteur de fond de plan (`MapToolbar.tsx`), dans des boutons `flex-1` étroits.
Correctif : panneau élargi `w-56 → w-64`, boutons passés en `whitespace-nowrap` + `px-1.5`.
Chaque libellé tient désormais sur une seule ligne, alignés.
(NB : `TimeMachine.tsx` — cité par le mandat — utilise des `<select>` natifs qui ne wrappent pas ;
le symptôme décrit correspond au bloc « Remonter le temps » de la barre carte.)

## G4 — Retrait « Imprimer » (Sources)
`SourcesPage.tsx` : bouton `window.print()` de l'en-tête supprimé. La traçabilité passe par les
PDF Flash / Dossier / Banquier (mise en page maîtrisée). Rien d'autre touché sur la page.

## G5 — CRM colonnes rognées + compteur tronqué
`Kanban.tsx` :
- compteur « N étapes · défiler → » passé en `whitespace-nowrap` → ne se tronque plus (« 8 ét… »)
  quand l'en-tête est serré ;
- **cale de fin** (`div` `shrink-0` de fin de rangée) : dans un conteneur flex à défilement
  horizontal, le padding droit n'est pas honoré par tous les navigateurs et la dernière colonne
  était rognée → la 8e colonne est maintenant entièrement défilable ;
- fondu de bord droit réduit `w-12 → w-8` (moins masquant).

## G6 — CRM colonnes vides ~800 px
`Kanban.tsx` : rangée passée en `items-start` (les colonnes s'ajustent au contenu au lieu de
s'étirer sur toute la hauteur) ; chaque colonne reçoit `max-h-full` (une colonne pleine défile en
interne) ; corps de colonne `min-h-[72px]` (zone de dépôt confortable mais compacte). Une colonne
vide fait désormais quelques dizaines de px, plus ~800.

---

## Vérification
- **Build** : `cd frontend && npm run build` → **0 erreur TS**, build vite OK.
- **Golden** : API sur `:8024`, `qa/golden_check.py` → **116/116 PASS, 0 FAIL, 0 incohérence**.

### Note d'environnement (golden)
Au premier lancement, l'API restait bloquée en « Waiting for application startup » : empilement de
verrous (schema-heal `ALTER TABLE parcels …` en attente derrière une transaction `idle in
transaction` d'une autre instance) dû à **plusieurs instances API résiduelles** d'autres sessions
(ports 8010/8011/8021/8023). Après résolution de la contention (verrou advisory schema-heal libéré
par les autres instances), une instance propre sur `:8024` a démarré en ~8 s et le golden est passé
116/116. Aucune modification de schéma ni de scoring de mon fait.

## Reste à faire / non fait
- **Aucun point du lot laissé de côté** (G1–G6 tous faits).
- **q_v7_defisc vs q_v6_m8** : observation reportée, non corrigée (hors mandat, décision Vic).
