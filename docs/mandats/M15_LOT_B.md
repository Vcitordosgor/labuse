# M15 — LOT B : plafonds levés (« voir plus »)

**Branche** `fix/m15-b-plafonds` (base `main` d24a27d) · prouvé, **non mergé**.
Outils concernés : **14 Radar permis** (M03), **15 Promesses mortes** (M04), **4 Foncier fantôme** (M07).

## Décision Vic appliquée
- **Outil 14** — plafond liste levé avec « voir plus » ; **carte = tous les géocodés** ; mention
  « X permis sans localisation précise » pour expliquer l'écart au client.
- **Outil 15** — plafond monté, « voir plus » **par paquets de 2000**, **pas de dump complet** ;
  tous géocodés donc mappables au fil du chargement.
- **Outil 4** — même traitement « voir plus » (plafond 600 → paginé).

## Ce qui a changé

### Backend (`src/labuse/api/modules.py`)
Les trois endpoints étaient plafonnés en dur dans le SQL (`LIMIT 2000 / 500 / 600`) **sans pagination**.
Ajout de `limit` + `offset` sur `/permis`, `/promesses`, `/fantome` :
- **`/permis`** : liste paginée (paquets de 300) ; **`carte`** = TOUS les géocodés (une requête légère
  `geom` seul, servie **une seule fois** en page 0, plafond de sécurité 8000) ; compteurs
  `geocodes` + `sans_localisation` = `total − geocodes`. Sur l'île, 24 mois : **4 980 permis,
  4 464 géocodés, 516 sans localisation précise**.
- **`/promesses`** : paquets de 2000 (décision Vic). Le comptage `COUNT(DISTINCT)` (~4 s) ne tourne
  **qu'en page 0** ; les pages suivantes déduisent `has_more` du remplissage.
- **`/fantome`** : paquets de 300. Le `count` est maintenant **exact** (il inclut le filtre verrou
  réel — avant il surcomptait au-delà de 600).

### Perf — deux pièges corrigés au passage (sinon « voir plus » = 32 s)
1. **`ST_AsGeoJSON` mort** dans `/promesses` et `/fantome** : la carte de ces deux outils est pilotée
   par **IDU** (`module-hl`), pas par géométrie. La géométrie transmise n'était jamais lue côté front.
   Retirée → payload promesses **1,4 Mo → 0,43 Mo**.
2. **Pathologie `LIMIT … OFFSET 0`** sur `/promesses` : le planner PostgreSQL choisissait un plan
   « fast-start » sur l'index date, catastrophique pour la jointure latérale (**28 s** en page 0,
   contre 4,7 s en page 1 — même volume). Parade = **CTE `MATERIALIZED`** qui calcule la jointure en
   bloc (hash joins) avant le tri+plafond. Page 0 **32 s → 10 s** (≈ 5 s lignes + 4 s comptage,
   masqués par le spinner) ; « voir plus » ≈ 5 s.

### Frontend (`ModulePanel.tsx`, `lib/api.ts`)
- `modPermis / modPromesses / modFantome` prennent `limit, offset`.
- M03 / M04 / M07 passent en **`useInfiniteQuery`** ; bouton partagé **`MoreButton`**
  (`data-more`, « Voir plus — X / Y chargés »). La liste n'est plus tronquée (M03 coupait à 150 en dur).
- M03 : carte = `head.carte` (tous les géocodés, filtrée par la zone dessinée si active) ;
  mention `data-permis-sansloc` « X sans localisation précise » (absente si zone active, où le compte
  devient « X permis dans la zone »).

## Preuve (app en marche `:8060`, `qa/m15/B/prove.mjs`)
| Outil | page 0 | après « voir plus » |
|---|---|---|
| 14 Radar permis | 300 lignes · **516 sans localisation précise** · 4 464 sur la carte · `Voir plus — 300 / 4 980` | **600 lignes** · `Voir plus — 600 / 4 980` |
| 15 Promesses mortes | `9 141 promesses mortes · 2 000 affichées` · `Voir plus — 2 000 / 9 141` | `… · 4 000 affichées` · `Voir plus — 4 000 / 9 141` |
| 4 Foncier fantôme | `6 261 parcelles gelées · 300 affichées` · `Voir plus — 300 / 6 261` | `… · 600 affichées` · `Voir plus — 600 / 6 261` |

Captures : `14a/14b`, `15a/15b`, `04a/04b`. La carte permis montre bien **tous les géocodés** (couverture
violette dense sur toute l'île), pas seulement la page chargée.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=http://127.0.0.1:8060`). Aucune touche scoring.
⚠ le défaut `:8010` du harnais pointe un serveur STALE → 84/116 trompeur ; toujours cibler l'instance testée.

## Addendum perf Promesses (décision Vic « rapide qui s'étoffe > 10 s »)
Trois leviers, cumulés → **1re page 10 s → ~2 s** :
1. **1re page réduite** 2000 → **1000** (le reste en « voir plus » ; le total connu dès l'abord).
2. **Comptage découplé** : le `COUNT(DISTINCT)` (~4 s) sort du chemin des lignes — appel
   `?count_only=true` **en parallèle**. La liste s'affiche sans l'attendre ; le total « 9 141
   promesses mortes » se remplit seul (« … » en attendant).
3. **Index partiel** `ix_dryrun_cascade_bati_exclude` (mirroir de `…_evenement`) : le `NOT EXISTS`
   « déjà bâti » coûtait **~3,6 s** (filtre layer/result sur le tas) → **~0,6 s** (probe pur). C'était
   le vrai plancher (pas la taille de page ni le comptage). `create_all` **n'ajoute pas** un index sur
   une table déjà existante → helper explicite **`ensure_promesses_index`** (CREATE INDEX IF NOT
   EXISTS, idempotent, ~3,7 s au 1er boot puis instantané) branché dans `ensure_schema`. ⚠ **déploiement :
   le 1er boot construit l'index (lock table cascade quelques secondes, une seule fois).**

Résultat mesuré (`:8060`, index en place) : lignes page 0 (1000) **2,07 s** · `count_only` **1,3 s** (‖) ·
« voir plus » ~2 s. Preuve `qa/m15/B/15a/15b` : « 9 141 promesses mortes · 1 000 affichées » → 2 000.

## Note / réserve
- ⚠ **conflit attendu avec LOT G** sur M07 (Foncier fantôme) : G coupe l'héritage commune. G est
  **empilée sur B** (merger B puis G) → composition propre, pas de conflit à la main.
