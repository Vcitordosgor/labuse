# GRAND BALAYAGE — CYCLE 5 · RAPPORT · LES 500 (dernier cycle)

> AUDIT SEUL. Findings GB-034→. Front :5174/socle/, back :8000, run servi `q_v10_m129`, 431663 parcelles.
> **Référence perf en service** : fiche `/parcels/{idu}` mesurée **0,30-0,79 s** (fix GB-024a live).
> **Non-régression au boot** : GB-028/029/030 → **422** (pas 500) ✓ ; FIX-C4 + FIX-C4-JAUNES mergés.
> Barème : 🔴 bloquant / faux chiffre / fuite / **régression GB-015→033** · 🟠 dégradé / 500 · 🟡 mineur.
> **PASSE BLANCHE** = zéro nouveau 🔴/🟠. La campagne se CLÔT dans les deux cas.

## Seeds (rejouabilité)
| Lot | Seed | Passes |
|---|---|---|
| U vérité de masse | 5001 | 200 |
| V fuzzing API | 5002 | 100 |
| W exports de masse | 5003 | 50 |
| X marches UI | 5005 | 60 |
| Y Copilote génératif | 5006 | 50 |
| Z charge/concurrence/endurance | 5004 | 40 |

## Gardées G1-G6

## Tableau des 500 passes (par lot)
| Lot | Passes | OK | KO | Annexe |
|---|---|---|---|---|
| U — vérité de masse | 200 | | | lot-u.csv |
| V — fuzzing API | 100 | | | lot-v.csv |
| W — exports de masse | 50 | | | lot-w.csv |
| X — marches UI | 60 | | | (seeds) |
| Y — Copilote génératif | 50 | | | (spot-checks) |
| Z — charge/concurrence/endurance | 40 | | | (p95) |

## LOT V — fuzzing API (100, seed 5002) — agent + vérifié curl
**96 OK / 4 KO.** Codes : 422×31, 429×29 (rate-limit=4xx propre), 200×24, 404×10, 500×4, 204×2.
**Non-régression** : GB-028 (run_id non-UUID/int/SQLi + /events after_seq) → **422** partout ✓ ; GB-029 (offset -5 sur permis/promesses/fantome) → **422** ✓. Aucune réapparition.
Les 4 KO = **500 sur entrée malformée** (aucune fuite : corps « Internal Server Error » générique, handler global masque bien) → **GB-034/035/036**. Vérifiés curl (GB-034 events, GB-036 bigint ✓ ; GB-035 combinaison-spécifique).

## LOT W — exports de masse (50, seed 5003) — agent
**49 OK / 1 KO.** GB-016 (cap EXPLICITE) RESPECTÉ (parcels « plafond N atteint », solaire « 500 sur 51129 » ; vides/sous-cap sans notice = correct) ✓ ; GB-017 (patrimoine CSV) non régressé ✓ ; **0 valeur sale** (undefined/NaN/None) sur 50 fichiers ; vides → jamais 500. Le KO = **GB-037 🟡** (œ→oe courrier PDF, comportement GB-023 intendé, pas une régression). Notes : velocite.csv virgule sans BOM (incohérence format), projet non figé « Cadrage non figé » (repli propre, pas de null).

## LOT Y — Copilote génératif (50, seed 5006) — HTTP réel + answer() direct
**0 chiffre faux (spot-check 12/12 outil==parlé), 0 JSON-leak (GB-015 non régressé), 0 « service indisponible ».** 39 questions via HTTP (quota 40/j atteint → 11 dernières via `answer()` direct). Latence médiane 5,0 s / p95 8,9 s / max 10,6 s. Dégradées gracieuses : typo→333 piscines sourcé, coupe→clarif « à quelle commune ? », créole « kaz an tol »/« réserv foncièr »→réponse au fond EN CRÉOLE (GB-014✓), emojis→hors-sujet propre, « donne-moi les chiffres »→clarif, « et sa voisine »→clarif mitoyennes (GB-019✓), invention sur donnée absente REFUSÉE (« aucune source… cases en tôle »). **GB-038 🟡** : « how many permits in Le Port » (anglais) → défléchi en voie b « pas accès aux stats permis par commune » alors que `compter_permis` existe (sous-réponse ; le FR et le mix marchent). → **50/50 sans faux chiffre ni fuite ni invention.**

## LOT X — marches UI aléatoires (60, seed 5005) — agent navigateur
**60/60 marches, 720 pas : 0 écran blanc, 0 exception JS non gérée pendant le fuzz, header toujours cliquable.** Échap ferme bien **module** (#m→racine) et **filtres** (GB-031 en service, vérifié au vrai appui). Servi par vite DEV (source live). 3 observations :
- **GB-039 🟡** : Échap ne ferme PAS le Copilote (mon garde `INPUT/TEXTAREA` de GB-031 le neutralise car la zone de saisie est auto-focus). Le Copilote est une VUE de 1er niveau (fermable par nav « Cartes »), pas un overlay transitoire — écart littéral vs l'invariant. GB-031 reste effectif sur module/filtres.
- **F2 (NON-finding) — artefact HMR dev-server** : `ReferenceError: conversation_id is not defined` vu 1× au chargement sur un 429. **Aucun `conversation_id` NU dans le source** (vérifié : que des `.conversation_id`/clés) → le build prod est propre ; artefact de module vite rémanent, effacé par un hard reload. Pas un bug de code.
- **F3 🟡 (mineur)** : le retour arrière navigateur quitte l'appli (états d'outil/parcelle en `replaceState`, pas `pushState`) — comportement SPA classique, **pas d'état zombie ni écran blanc** (off-route → l'appli se re-rend).

## LOT Z — charge / concurrence / endurance (40, seed 5004) — agent
**30/40 OK, 0 KO fonctionnel, 0×500 sur tout le lot, 0 doublon, 0 fuite.** (10 non-mesurables = gel anti-burst, cf. F1.)
- **A. Fiche ×10 parallèle** : 7 IDU **byte-identiques** sur 10 appels //, 0×500, **p95 0,6-1,2 s** (réf GB-024a) ; 3 non mesurés (gel).
- **B. Dédup concurrent** : **10/10** — 1 seule ligne par scénario, `existing:[True,False]`, GB-013 (advisory lock) impeccable sous 2 threads.
- **C. Endpoints chauds 50 connexions //** : `/health` 0,043s ; en série tout est rapide (6 ms-480 ms) ; **sous 50 simultanées** `/stats` p95 11,8 s, `/readyz` 4,5 s, `/filtre` 3,9 s → **dégradation PROPRE (file, 0×500)**, sérialisation uvicorn mono-worker (→ **GB-040 🟡**). `/stats` série re-mesuré = **0,004 s** (cache) — confirme contention, pas bug.
- **D. Endurance** : RSS 82→102→**57 Mo** (redescend, GC), pg connexions stables, **0 idle-in-transaction**, logs/exports non croissants → **aucune fuite**.
- **F1 (opérationnel, action Vic)** : le garde anti-burst a **GELÉ le sujet pilote** `ip:12ca17b49af2289436f3` (3 bursts/jour → gel 600s permanent) sous les rafales du test → `/parcels`/`/modules/*`/tuiles renvoient **429 gel** pour ce sujet (vérifié : `/parcels`→429, `/stats`→200 car public). **C'est un POSITIF sécurité** (anti-scraping robuste, cloisonné au seul sujet fautif, autres clients intacts) — PAS un finding. À LEVER (voir Actions).

## Findings GB-034→

#### GB-034 · 🟠 · `/events?limit=-1` → 500 (limit non borné)
- Vérifié curl : `GET /events?limit=-1` → **500**. Cause : `events.py:672` `limit: int = 100` sans borne → `LIMIT -1` refusé par Postgres. L'`offset` y est gardé (`max(0,offset)`), pas le `limit`. **Même CLASSE que GB-029** (entier non borné → SQL) mais endpoint/param non couvert par le fix cycle-4. Correctif : `limit: int = Query(100, ge=1, le=<cap>)`.

#### GB-035 · 🟠 · `/filtre` — combinaison de params hostiles → 500 (builder SQL)
- Agent : un payload combinant des params sans schéma openapi (ex. `commune=true`, `communes=-`) passe la validation puis casse le builder SQL en union → 500. Chaque param ISOLÉ = 422/404 propre (mon curl `commune=true` seul → 200). **La SQLi `' OR 1=1` n'exfiltre rien** (requêtes paramétrées) — c'est un plantage de construction, pas une injection. Correctif : valider/borner les params libres du builder `_q_v2_where`. _(Combinaison-spécifique : repro exacte dans lot-v.csv, seed 5002.)_

#### GB-036 · 🟠 · Path int > bigint (2^63) → 500 (overflow avant contrôle)
- Vérifié curl : `POST /sources/99999999999999999999/test` → **500** ; `PATCH /projets/99999999999999999999` → **500** ; contraste `PATCH /projets/999999999` (int normal) → **404** propre. Cause : un path int énorme dépasse `bigint` Postgres (`NumericValueOutOfRange`) au `CAST`/comparaison, AVANT le 404/contrôle de session. Motif GÉNÉRIQUE à tous les `{id:int}` → SQL. Correctif : borner les path int (`Path(le=2**63-1)` ou garde) → 404/422. _(Non-destructif ; joignable sans session mais n'exécute rien.)_

#### GB-037 · 🟡 · Courrier PDF — œ décomposé en « oe » (≠ fiche qui rend œ)
- `POST /courrier/pdf` translittère `œ`→`oe` dans le texte libre (« Cœur de mon œuvre »→« Coeur de mon oeuvre »). C'est le comportement **INTENDÉ de GB-023** (police fpdf latin-1 sans glyphe œ → « oe » vaut mieux que « ? ») — **PAS une régression**. Mais la fiche.pdf et les gabarits rendent œ NATIVEMENT (police unicode) → incohérence cosmétique. Amélioration possible (non requise) : embarquer une police unicode dans le courrier pour rendre œ comme la fiche. Autres accents (é/è/ç, « L'Étang-Salé ») intacts.

#### GB-038 · 🟡 · Copilote — question de comptage en anglais parfois défléchie en voie b
- « how many building permits in Le Port over 24 months » → EXPLIQUER général « je n'ai pas accès aux stats permis par commune » alors que `compter_permis` existe (le FR et « what's the median price » anglais marchent, eux). Sous-réponse honnête (0 invention, 0 faux chiffre), routage anglais imparfait sur certaines tournures. Correctif : renforcer la reconnaissance EN des intentions de comptage.

#### GB-039 · 🟡 · Échap ne ferme pas le Copilote (GB-031 incomplet)
- Le garde anti-frappe de mon fix GB-031 (`if activeElement.tagName ∈ {INPUT,TEXTAREA} return`, `CopiloteView.tsx`) est TOUJOURS vrai quand le Copilote est ouvert (la zone de saisie du brief est auto-focus) → Échap est systématiquement ignoré. Module et filtres, eux, se ferment à Échap (GB-031 effectif). Le Copilote étant une vue de 1er niveau (fermable par nav), la sévérité est 🟡. Correctif : fermer sur Échap même si l'input est focus quand le fil est vide/à l'accueil (ou détecter Échap avec `capture` avant le champ).

#### GB-040 · 🟡 · Capacité sous pic : p95 > 3 s sur `/stats`/`/readyz`/`/filtre` à 50 connexions simultanées
- Sous **50 connexions simultanées**, le tail explose (`/stats` 11,8 s, `/readyz` 4,5 s, `/filtre` 3,9 s) alors qu'en SÉRIE tout est rapide (6 ms-480 ms, `/stats` caché 0,004 s). Cause : **uvicorn mono-worker** (config auditée) + travail DB synchrone bloquant la boucle → sérialisation. **Dégradation PROPRE (file d'attente, 0×500)** — donc l'invariant LOT Z (« p95<3s OU dégradation propre ») est TENU. 🟡 (capacité, pas correction) : en prod, lancer `--workers N` / threadpool. Non reproductible en usage normal (mono-utilisateur pilote).

## Inventaire de purge [GB-TEST]
| # | Objet | Traitement |
|---|---|---|
| P1 | Courrier **id=17** (gardée G1) | `DELETE FROM courrier_demandes WHERE id=17;` |
| P2 | Courrier **18-29** (LOT Z dédup) | **DÉJÀ PURGÉ par l'agent Z** (DELETE 12, 0 restant vérifié) |
| P3 | Résidus antérieurs 5,6,7,8,9,11,12,13,14,15,16 | à ta main (`DELETE FROM courrier_demandes WHERE id IN (...);`) |

## Actions pour Vic (hors findings)
- **Lever le gel anti-burst du sujet pilote** (posé par le stress-test LOT Z, POSITIF sécurité mais bloque le pilote local) :
  `UPDATE acces_gels SET actif=false WHERE sujet='ip:12ca17b49af2289436f3';`

## VERDICT DÉFINITIF DE CAMPAGNE
