# VITESSE-3 — Accélérer sans toucher à la qualité

**Branche** `fix/vitesse-3` · worktree `~/Desktop/labuse-vitesse3` · ports 9190/6390 · base locale réelle `labuse` (run servi `q_v20`). Pas de merge, aucun accès prod. N'a touché ni l'implantation ni `pige/` (sessions FAISA / RADAR-4 en //).

## Contrainte de Vic (le fil rouge)

> Plus vite sans toucher à la qualité : **chaque réponse accélérée est identique à l'octet près à l'avant, prouvé.**

Méthode appliquée partout : (1) **mesurer** le vrai coût (EXPLAIN / profil par sous-appel) avant de toucher quoi que ce soit ; (2) accélérer par une **clé de fraîcheur** (`empreinte_attendue` = run servi + cascade + résiduel + millésimes sources + version du code — la même clé que le cache de fiche commune) ou par **matérialisation équivalente** ; (3) **prouver l'identité** octet pour octet entre l'avant et l'après.

Doctrine réutilisée (déjà en place dans LA BUSE) : mémos in-process à TTL/clé (`circuit_garanties.noms_vides_caches`, `stripe_lecture._CACHE`), cache de fiche commune `commune_contexte_cache`, réchauffage worker démon `_rechauffer_worker` (ne bloque jamais le boot). Rien d'exotique introduit : un seul petit module neuf, `perf_cache.MemoLRU` (mémo borné thread-safe à clé de fraîcheur).

---

## Résultats — temps AVANT / APRÈS (base locale réelle, `curl -w %{time_total}`)

| Point | Endpoint | AVANT froid | AVANT chaud | APRÈS 1ᵉʳ client (préchauffé) | APRÈS chaud | Preuve d'identité |
|---|---|---|---|---|---|---|
| **B-004** | `GET /api/recherche/suggest?q=rue` | 2,56 s | 2,56 s | **0,21 s** | **0,14 s** | 27 jetons : 0 écart colonne↔expression |
| **B-004** | `…?q=saint` | 4,27 s | 4,27 s | **0,14 s** | **0,14 s** | idem (ordre rendu TOTAL) |
| **F-006** | `GET /sources` | 14,8 s¹ | 6,5 → 0,8 s¹ | **0,15 s** | **0,039 s** | `/sources` #1==#2 identique ; `etat_sources` force==cache |
| **D-018** | `GET /modules/successions?commune=Saint-Denis` | 8,7 s¹ | 1,68 s | **0,23 s** | **0,013 s** | mémo==calcul frais (total 6256, n 200) |
| **C-003** | `GET /communes/Saint-Denis/contexte` | 18,7 s¹ (33,5 s mesuré, cache périmé) | 0,04 s | **0,008 s** (après préchauffage) | 0,04 s | payload (hors `cache_calcule_le`) identique préchauffé↔recompute |
| **C-003** | `POST /outils/etude-zone` (rayon 1 km) | 6,57 s¹ | 5,51 s¹ | 7,7 s² | **0,028 s** | mémo==calcul frais, stable |
| **F-005** | `GET /admin/pilotage` (Stripe) | **88 s**¹ (prod) | <1 s (cache 5 min) | **jamais bloquant** | <1 s | `apercu_affichage`==`apercu` (cache chaud), sert le cache daté |

¹ chiffre de l'audit NU-1 (prod / base froide 44 Go) — non reproductible tel quel sur le Mac (base chaude, pas de clé Stripe restreinte). ² l'étude de zone part d'un polygone/rayon à **cardinalité ouverte** : impossible de préchauffer toutes les zones ; le 1ᵉʳ usage d'UNE zone donnée paie encore, chaque usage SUIVANT est instantané (la plainte « > 5 s à **chaque** usage » est levée).

**Toutes les mesures « après chaud » sont < 2 s** (objectif du mandat pour les outils à usage répété), la plupart < 100 ms.

---

## Par point : le vrai coût mesuré, le correctif, la preuve

### B-004 — Autocomplétion « rue » / « saint » : 2,6 s → 0,14 s (×43 au SQL)
**Mesure (EXPLAIN ANALYZE, `q=rue`).** L'index trigram trouve les **137 765 candidats en 5 ms** ; le *Bitmap Heap Scan* **ré-évalue l'expression de normalisation** (translate/replace/regexp imbriqués sur numéro+rep+voie+CP+commune) sur CHACUNE des 137 k lignes au recheck ET au tri → **2 242 ms**. Ce n'est ni l'index ni le réseau : c'est le recalcul de l'expression par ligne.

**Correctif.** Colonne **générée STORED** `adresses.suggest_norm` = `GENERATED ALWAYS AS (<l'expression exacte>) STORED`, + index GIN trigram sur cette colonne. `_sugg_adresse` lit la colonne quand elle existe (sinon repli sur l'expression). La valeur de la colonne EST, par construction, exactement l'expression → recheck et tri la **lisent** au lieu de la recalculer. Posée au **heal** (avant que le worker serve ; existence vérifiée ; `SET LOCAL lock_timeout='20s'` + retry pour franchir un drain de connexions transitoire), jamais sous trafic. Mesuré : `EXPLAIN` **2 288 ms → 53 ms**.

**Ordre rendu TOTAL.** L'`ORDER BY` du suggest n'était pas un ordre total : des lignes aux clés de tri identiques (plusieurs « 2 Chemin Go » n° 2, « 1 Rue Moka » dans deux communes) sortaient dans un ordre **arbitraire dépendant du plan** (parallélisme, tri non stable) — instable d'un plan à l'autre, donc sans « avant » stable à égaler. On ajoute `idu` en ultime départage sur **les deux chemins** : l'autocomplétion devient déterministe ET le chemin colonne devient **identique à l'octet** au chemin expression.

**Preuve.** 27 jetons (« rue », « saint », « chemin », « 1 rue », « rue de », « 2 rue moka »…) → **0 différence** entre chemin colonne et chemin expression (`label/sub/idu/lon/lat` + ordre).

### F-006 — Page Sources : 14,8 s → 0,04 s
**Mesure (profil par sous-appel, à chaud).** `fraicheur.etat_sources` **1,72 s** (11 `max(date)` sur les tables sources de 44 Go) + `etats_sources.lister_etats` **1,44 s** dont `noms_vides_caches` **1,20 s**. Le reste (sélection `data_sources`, `ingestion_runs`, `source_checks`, radar) < 30 ms.

**Correctif.** On **ne cache PAS la réponse** (un premier jet mémoïsé figeait la *visibilité* des sources → une désactivation admin ne se voyait plus : 2 tests rouges l'ont prouvé, correctif abandonné). On cache les **deux sous-appels coûteux**, qui ne bougent qu'aux ingestions. `noms_vides_caches` a déjà son cache 5 min (pré-existant, inchangé — ~1,2 s après inactivité, < 2 s). On pose sur `fraicheur.etat_sources` un cache à **CLÉ DE FRAÎCHEUR** (pas un TTL arbitraire) : clé = jour Réunion + `max(last_sync_at)` + `max(ingestion_runs.finished_at)`. Comme M84 garantit que **toute ingestion laisse une trace dans `ingestion_runs`** (`trace_ingestion`), la clé change exactement quand la sortie peut changer → le cache reste **chaud entre deux ingestions** (pas de péremption à 5 min, donc pas de re-paiement du 1,7 s après une période d'inactivité). Les gardes qui exigent le live (`derniers_en_retard`, rebuild) passent par `etat_sources(force=True)`. La **sélection des sources affichées reste calculée en direct** → identité de visibilité préservée.

**Preuve.** `etat_sources(force)` == `etat_sources(clé)` (données inchangées), stable ; `/sources` #1 == #2 octet pour octet ; les 2 tests de visibilité redeviennent verts.

### D-018 — Successions : 8,7 s → 0,013 s (et la cause réelle n'était PAS celle supposée)
**Mesure (EXPLAIN ANALYZE, Saint-Denis).** La sous-requête corrélée `dirigeant_nom` que l'audit soupçonnait coûte **32 ms** (déjà indexée `ix_pm_dirigeant_siren`) — **pas** le goulot. Le coût réel : la jointure **île entière** `parcel_veille_succession (6 256) → parcels` filtrée **tard** par commune (**6 256 sondes `parcels`** à froid, `read=1750` blocs) + le **seq-scan de `parcelle_personne_morale` (82 701 lignes)**.

**Correctif.** `parcel_veille_succession` est un **snapshot mono-run** : la réponse ne bouge qu'au recalcul Score V / à la bascule. Mémo par clé de fraîcheur (`empreinte` + `max(computed_at)` veille + `max(last_sync_at)` RNE + paramètres). Aucun risque de « cache menteur » : la clé embarque exactement ce dont dépend la réponse.

**Preuve.** mémo == calcul frais (`total=6256`, `n=200`), déterministe et stable. *Note d'honnêteté : correctif différent de celui proposé par l'audit, parce que la mesure a redirigé vers le vrai coût.*

### C-003 (a) — Fiche commune : 6–18 s à froid après chaque déploiement → 0,008 s
**Mesure.** Le cache `commune_contexte_cache` existe (job nocturne) mais sa **clé de fraîcheur embarque la version du code** : à chaque déploiement, les 24 entrées deviennent périmées → le **1ᵉʳ client de chaque commune** paie le recalcul (18,7 s mesuré St-Denis, cache périmé).

**Correctif.** Le **réchauffage worker** (démon, ne bloque pas le boot) recalcule, via `rafraichir_contexte_cache` (LE point d'écriture unique, identique au job nocturne et à la recompute du 1ᵉʳ client), **uniquement les communes dont la clé est périmée**. Un seul worker via **verrou consultatif** (pas de double calcul). Déjà fraîches → `0/0` recalculée (idempotent, aucun gaspillage).

**Preuve.** payload servi (hors `cache_calcule_le`, l'horodatage honnête du calcul) **identique** que le cache ait été rempli par le réchauffage, le job nocturne ou la recompute du 1ᵉʳ client — même fonction, même état de données. Démonstration bout-en-bout : 2 communes forcées périmées → préchauffage **17,3 s en fond** → `GET …/Cilaos/contexte` **0,008 s**.

### C-003 (b) — Étude de zone : > 5 s à chaque usage → 0,028 s dès le 2ᵉ usage
**Mesure.** Aucun cache de résultat : recalcul intégral (`ST_Union`/`ST_Intersects` sur `spatial_layers`, SIRENE, Filosofi, DVF) à chaque ouverture — et le PDF ré-appelle l'endpoint.

**Correctif.** Mémo par clé de fraîcheur (`empreinte` + hash des entrées normalisées : idu/point/polygone, rayon, minutes, mode, NAF, sous-destination, titre). Borné (LRU 256) car `geom` est à cardinalité ouverte. Déterministe à état de données figé.

**Preuve.** mémo == calcul frais, stable. *Réserve honnête : le PDF d'étude de zone s'exécute dans un PROCESSUS séparé (ETUDE-ASYNC-1) — il ne partage pas ce mémo in-process ; c'est l'ÉCRAN (la plainte « à chaque usage ») qui est corrigé.*

### F-005 — Pilotage : 88 s à froid (Stripe synchrone) → jamais bloquant
**Mesure.** `apercu()` fait des appels réseau Stripe **synchrones dans le thread de requête** (`subscriptions.list(...).auto_paging_iter()` + `invoices.list()`) → 88 s au premier chargement de la journée (prod). *Non reproductible sur le Mac (pas de clé restreinte) — c'est le `type` d'incident ETUDE-ASYNC-1.*

**Correctif.** `apercu_affichage()` (chemin de la page) : sert **le dernier cache daté immédiatement** et déclenche le rafraîchissement **en tâche de fond** (un seul fetch en vol, verrou non bloquant). Cache jamais encore rempli → marqueur `en_cours` (le front affiche « — », jamais un « 0 € » trompeur). Préchauffé au boot (réchauffage worker, hors requête). `/admin/stripe?force=true` = geste admin explicite « rafraîchir maintenant » (bloque, volontairement). Pilotage et Licences passent au chemin non bloquant.

**Preuve.** cache chaud → `apercu_affichage()` renvoie `_CACHE["data"]`, **octet pour octet** ce que renvoyait `apercu()` (`maj` servie telle quelle = « affiché avec son heure »). Seul le MOMENT du fetch change (fond, hors requête). Le cache 5 min existait déjà avant VITESSE-3 → aucune fraîcheur perdue.

---

## Recette — tests

- **Hook pre-push (famille sans base)** : scan secrets **vert** · front `tsc -b` **OK** · `vitest` **305/305** · pytest unitaires **2796 passed, 48 skipped, 0 échec**.
- **Tests base (zones touchées : recherche/suggest/successions/sources/stripe/dashboard/contexte/étude-zone/fraîcheur/pilotage)** : **290 passed, 3 skipped, 1 échec** — l'échec (`test_sources_fix::test_selection_sql_egale_predicat_python`, 115 vs 116) est **PRÉ-EXISTANT sur la base** (prouvé par `git stash` : il tombe à l'identique sans mes changements — artefact de données `labuse_test`, cf. « Mac ≠ prod »), sans rapport avec VITESSE-3.
- **Préchauffage** : le réchauffage worker journalise `caches Sources chauds`, `mémo Successions chaud`, `aperçu Stripe chaud`, `contexte N/N communes` — sans erreur, sans bloquer le boot.

## Fichiers touchés

- `src/labuse/perf_cache.py` (neuf) — `MemoLRU` à clé de fraîcheur.
- `src/labuse/stripe_lecture.py` — `apercu_affichage()` + rafraîchissement de fond (NU-F-005).
- `src/labuse/api/dashboard.py` — Pilotage/Licences/`/admin/stripe` non bloquants.
- `src/labuse/api/recherche.py` — colonne générée `suggest_norm` au heal + lecture + ordre total `idu` (NU-B-004).
- `src/labuse/ingestion/fraicheur.py` — cache 5 min de `etat_sources` (NU-F-006).
- `src/labuse/api/modules.py` — mémo Successions (NU-D-018).
- `src/labuse/api/app.py` — mémo Étude de zone (NU-C-003), réchauffage worker étendu (Sources/Successions/Stripe/contexte 24 communes).
- `frontend/src/lib/api.ts`, `frontend/src/components/admin/AdminView.tsx` — `en_cours` Stripe (« — » transitoire, rétro-compatible).

## Notes de déploiement (pour Vic)

1. **Colonne `adresses.suggest_norm`** : au 1ᵉʳ boot après ce déploiement, le heal la crée (réécriture de table ~10–30 s, UNE fois, avant que le worker serve). Si un verrou la bloque après retries → repli silencieux sur l'expression (autocomplétion correcte, juste lente) jusqu'au boot suivant. Elle se reconstruit d'elle-même après une ré-ingestion BAN (qui recrée `adresses`).
2. **Réchauffage contexte (24 communes)** : au 1ᵉʳ boot après déploiement, les 24 fiches sont périmées (code changé) → ~8 min de recalcul EN FOND sur un worker (verrou consultatif). Le job nocturne `fiche-commune-cache` fait déjà exactement cela ; ici c'est joué plus tôt. Les clients servis entre-temps paient encore le recalcul inline par commune (comme avant), de moins en moins au fil du réchauffage.
3. Aucune DDL hors `adresses.suggest_norm` + son index. Aucun nouveau table de cache. Aucune bascule de run.
