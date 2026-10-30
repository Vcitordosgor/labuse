# ETUDE-ASYNC-1 — une étude lourde ne bloque plus les autres requêtes, et un calcul abandonné s'arrête vraiment

**Branche** `feat/etude-async-1` · **worktree** `~/Desktop/labuse-etudeasync` · **ports** API 9020 / front 6220
**Base** `labuse` (Mac, lecture/écriture locale) · **aucun accès prod** · **pas de merge** (geste de Vic)
**Ne touche pas** `src/labuse/pige/` ni l'estimation (session parallèle) — ces endpoints sont seulement
*appelés* en lecture pendant la recette.

---

## 1. Le constat (DEPLOY-1029b)

Une Étude d'assemblage lourde, à froid, atteignait la borne de 60 s et renvoyait un **503**. Pire : le
calcul abandonné à la borne **continuait dans un thread** et affamait l'unique boucle de l'API — pendant
ce temps les autres requêtes de tous les clients ralentissaient ou tombaient en **504**.

Deux défauts dans l'ancien `_etudier_borne` (`api/modules.py`) :

```python
ex = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="etude")
fut = ex.submit(_run)
try:
    return fut.result(timeout=_ETUDE_TIMEOUT_S)
except concurrent.futures.TimeoutError:
    raise HTTPException(503, detail=_ETUDE_TROP_LOURDE)
finally:
    ex.shutdown(wait=False)   # on ABANDONNE — mais le thread continue
```

1. **Un thread Python n'est pas tuable.** `shutdown(wait=False)` n'arrête rien : le thread finissait son
   calcul en arrière-plan. Le moteur d'implantation fait du travail géométrique CPU (shapely) qui **tient
   le GIL** ; tant qu'il tourne, la boucle de l'API et son pool de threads ne peuvent plus servir
   personne → fiche/carte en 504. Le thread fantôme gardait aussi sa connexion Postgres ouverte.
2. Le client recevait un 503 « assiette trop lourde, contactez-nous » **sans proposition de relancer**,
   alors que l'échec est souvent transitoire (données lentes **à froid**).

---

## 2. La solution retenue — calcul dans un processus séparé tuable

> **Choix justifié.** Le mandat laisse trois pistes. Retenu : **le calcul dans un processus séparé
> tuable**. C'est la plus simple qui *tient* les deux exigences à la fois, sans nouvelle infrastructure.

| Piste | Tue le calcul abandonné ? | Débloque les autres requêtes ? | Coût |
|---|---|---|---|
| **Plusieurs workers uvicorn** | ❌ non (le thread fantôme survit dans son worker) | partiellement (dilue le rayon de blast sur N workers, mais un worker reste affamé et garde sa connexion DB) | nul, mais **insuffisant** : ne répond pas au mandat « s'arrête vraiment » |
| **Tâche de fond + suivi (lancer → statut → résultat)** | ❌ pas en soi (il faut *quand même* un substrat d'exécution tuable dessous) | oui | **lourd** : magasin de jobs, polling côté front, états — surdimensionné pour une interaction synchrone mono-utilisateur |
| **✅ Processus séparé tuable** | ✅ **oui** : SIGTERM → SIGKILL, le calcul s'arrête, le GIL de l'API se libère, la connexion Postgres se referme (Postgres annule la requête en cours à la déconnexion) | ✅ oui | **minimal** : `multiprocessing` (stdlib), zéro broker, zéro table, zéro polling |

**Pourquoi ça ne bloque plus.** L'endpoint `POST /modules/etude` est un `def` **synchrone** : FastAPI
l'exécute dans son pool de threads. Pendant qu'on **attend** le processus enfant (`queue.get`, attente au
niveau C → **GIL relâché**), la boucle et les autres threads du pool servent normalement fiche, carte et
Analyser une annonce. Le travail CPU lourd est désormais dans un **autre interpréteur, avec son propre
GIL** : l'API n'en porte plus rien.

**Pourquoi ça s'arrête vraiment.** À la borne, on **tue** l'enfant :

```python
def _tuer_processus(p):
    if p.is_alive():
        p.terminate(); p.join(1.0)   # SIGTERM
    if p.is_alive():
        p.kill(); p.join(1.0)        # SIGKILL
```

**« spawn », jamais « fork ».** On force `multiprocessing.get_context("spawn")` : `fork` depuis un
process multi-thread (uvicorn) peut interbloquer (verrous tenus par d'autres threads au moment du fork)
et hériterait du **pool SQLAlchemy du parent** — dangereux. `spawn` repart d'un interpréteur neuf :
l'enfant recrée son engine/sa session à la demande, sans rien hériter. Surcoût **mesuré ≈ 1 s** (import
de l'app dans l'enfant), négligeable devant un calcul de plusieurs dizaines de secondes. Le lanceur de
prod (`uvicorn` en console-script, avec garde `if __name__ == "__main__"`) est compatible spawn.

### Ce qui a changé (code)

- `config.py` — nouvelle borne **réglable** `etude_timeout_s = 60.0` (env `LABUSE_ETUDE_TIMEOUT_S`). Une
  valeur basse force un dépassement (recette) sans toucher au code.
- `api/modules.py` :
  - `_dans_processus(fn, args)` — exécute `fn` en « spawn », borné ; 503 à la borne **après** avoir tué
    l'enfant ; ré-élève l'exception de l'enfant (ValueError → 400, autre → géré par la route).
  - `_worker_etude` — calcul **+** enrichissements (`_attach_*`) dans l'enfant, session DB fraîche.
  - `_worker_etude_pdf` — **tout l'export PDF** dans l'enfant : calcul + enrichissements + rendu
    WeasyPrint (lui aussi gourmand en CPU et porteur du GIL). Le parent ne fait plus que l'archivage
    (un INSERT instantané). Même message de borne, même mise à mort.
  - Les deux routes `/modules/etude` et `/modules/etude/pdf` passent par ce chemin.
- **Résultats inchangés** (`src/labuse/implantation/` **non modifié**) : seul le *lieu* d'exécution
  change. Prouvé byte-à-byte (§4).

### Côté écran (front)

- Le calcul affiche l'indicateur unique de l'app — les **trois points verts** (`Chargement`, déjà en
  place : « Calcul en cours, jusqu'à une minute »). Inchangé.
- Au-delà de la borne : **message propre qui propose de relancer, jamais un code**. Helpers partagés dans
  `lib/api.ts` :
  - `messageEtudeErreur(e)` — toujours une phrase FR (jamais un HTTP, jamais un message d'abort réseau) ;
  - `etudeRelancable(e)` — relance proposée **sauf** entrée refusée (400 : relancer une assiette invalide
    échouerait pareil). Le 503 de borne redevient **relançable** (une assiette lourde aboutit souvent au
    2ᵉ essai, données plus lentes à froid).
  - `EtudeV6` (outil) : message propre + le bouton « Analyser mon projet → » reste cliquable.
  - `M22Programme` (« Par critères ») : `ErrorState` avec bouton **Réessayer** sur 503/panne, sans bouton
    sur 400.
- **Export PDF** : même traitement. `useOuvrirDocument` remonte déjà le message `detail` du serveur
  (« relancez ») et laisse le bouton cliquable — rien à changer, vérifié.

---

## 3. Recette (serveur réel sur :9020, base `labuse`)

### 3.1 Une étude lourde ne bloque pas les autres requêtes

Assiette lourde de recette : **4 parcelles Étang-Salé** `97404000AW0099/0451/0624/0625`. On lance l'étude
et, pendant qu'elle tourne, on **martèle** fiche + carte + Analyser une annonce (35 tours en ~10,5 s).

```
=== ÉTUDE LOURDE 4 parcelles (pendant qu'on martèle les autres routes) ===
  statut HTTP = 200 ; durée = 12.60s
  processus enfants du serveur pendant l'étude : min=2 max=2 (repos=0 ; l'étude = +1)

=== RÉPONSES CONCURRENTES PENDANT L'ÉTUDE (35 tours) ===
  fiche    n=35  p50=   3.8ms  max=  28.3ms
  carte    n=35  p50=   2.5ms  max=   6.9ms
  annonce  n=35  p50=   8.7ms  max=  70.6ms
```

Latences **au niveau du repos** (baseline idle : fiche 6–17 ms, carte ~5 ms, annonce ~10 ms) pendant
toute la durée du calcul lourd. **Aucun blocage, aucun 504.** (Les « 2 enfants » = le worker de calcul
`spawn_main` **+** le `resource_tracker` de `multiprocessing`, un helper de comptabilité ; voir 3.2.)

### 3.2 Un calcul qui dépasse la borne est réellement tué (pas de thread/processus fantôme)

Serveur relancé avec `LABUSE_ETUDE_TIMEOUT_S=3`. On lance l'étude lourde (qui prend ~12 s) et on observe
les processus enfants du serveur, classés par leur ligne de commande :

```
AVANT        : 1 enfant(s) {'93547': 'resource_tracker'} → calcul d'étude = 0
PENDANT(1,5s): 2 enfant(s) {'93547': 'resource_tracker', '93698': 'etude(spawn_main)'} → calcul d'étude = 1 ['93698']

RÉPONSE      : HTTP 503 en 3.02s · erreur=etude_trop_lourde

APRÈS borne  : 1 enfant(s) {'93547': 'resource_tracker'} → calcul d'étude = 0
  ✅ PROCESSUS DE CALCUL TUÉ (aucun fantôme)
```

Le processus de calcul **93698 apparaît** le temps de l'étude et **disparaît** à la borne : il est **tué**
(SIGTERM→SIGKILL), pas abandonné. Le seul survivant est le `resource_tracker` (helper permanent, zéro
CPU). Le message servi est propre :

> « L'étude n'a pas pu être calculée dans le temps imparti. Elle peut aboutir en relançant (les données
> sont parfois plus lentes à froid) ; sur une assiette très lourde, essayez moins de parcelles. »

Et le serveur **répond encore** immédiatement après la mise à mort :
`fiche juste après la mise à mort : HTTP 200 en 29.1ms (serveur vivant)`.

### 3.3 L'export PDF : même offload, même borne, même mise à mort — et rend bien

- **Borne (serveur à 3 s)** : le PDF offloade calcul **+ rendu WeasyPrint** dans l'enfant.
  ```
  PENDANT : processus de calcul PDF = 1 ['93779']
  RÉPONSE PDF : HTTP 503 en 3.02s · erreur=etude_trop_lourde
  APRÈS borne : processus de calcul PDF = 0 → TUÉ
  ```
- **Succès (serveur borne défaut 60 s)** : `POST /modules/etude/pdf` sur la même assiette →
  **HTTP 200, `application/pdf`, 114 878 octets (PDF v1.7)** en 12,85 s, nom
  `EF-7d56bb5b.pdf`. Le rendu a bien eu lieu **dans le processus enfant** et les octets sont revenus
  au parent.

---

## 4. Mêmes chiffres qu'avant

- **Identité byte-à-byte** sur l'assiette lourde : payload du processus séparé == payload du calcul direct
  (`json.dumps(sort_keys=True)`), **350 662 octets identiques**. C'est le test `reel`
  `test_memes_chiffres_subprocess_vs_direct` (joué ici sur `labuse`, rejoué au banc de nuit).
- **Suite étude-v6 inchangée** : `test_etude_v6_capacite + bilan + 8_pdf` → **36 passed** (dont le PDF).
  `src/labuse/implantation/` n'est pas touché.

---

## 5. Tests & filet (hook vert)

| Vérif | Résultat |
|---|---|
| Scan de secrets | ✅ rien trouvé |
| Front `tsc -b` | ✅ 0 erreur |
| Front `vitest run` | ✅ **301** passed (63 fichiers) |
| Python unitaires `-m "not db and not local and not reel and not network"` | ✅ **2743 passed**, 48 skipped |
| Étude-v6 (banc réel, same-numbers) | ✅ 36 passed |

Nouveau fichier `tests/test_etude_async.py` (famille **sans base**, donc dans le filet pre-push) — exerce
la mécanique de `_dans_processus` avec de faux workers :

1. `test_borne_tue_le_processus_et_ne_laisse_pas_de_fantome` — borne 0,3 s sur un worker de 10 s → 503
   sous 4 s, **`multiprocessing.active_children()` vide** (aucun fantôme).
2. `test_resultat_traverse_le_processus` — le résultat revient par la file.
3. `test_valueerror_remonte_pour_un_400` / `test_autre_erreur_remonte_pour_un_500` — les exceptions de
   l'enfant remontent au bon code HTTP.
4. `test_memes_chiffres_subprocess_vs_direct` (`reel`) — identité du payload (§4).

> Note d'environnement : un worktree sans `.env` fait `pytest` se rabattre sur le rôle DB `labuse`
> (inexistant sur ce Mac), ce qui faisait *errorer* 2 tests non liés (`test_donnees_etat_fix1`). Copie du
> `.env` du dépôt principal (rôle `openclaw`, gitignoré) → **0 erreur, 2743 passed**. Ces tests passent
> sans mon changement (prouvé).

---

## 6. Déploiement (geste de Vic — pas fait ici)

- **Rien de nouveau côté infra.** `multiprocessing` est stdlib ; aucun broker, aucune table, aucun cron.
- Borne réglable : `LABUSE_ETUDE_TIMEOUT_S` (défaut 60) dans `labuse.env` si besoin.
- Les marges déjà en place restent valables (Caddy `read_timeout 90s`, uvicorn `--timeout-keep-alive 75`,
  fetch front 90 s) : la borne de 60 s renvoie le 503 **avant** elles.
- `--workers 5` (prod) reste pertinent et **complémentaire** : le fix supprime le fantôme et l'affamement
  *dans chaque worker* ; plusieurs workers restent utiles pour la concurrence générale.
- **Merge + déploiement = gestes de Vic.** Branche non mergée, rien en prod.

---

## 7. Fichiers touchés

```
src/labuse/config.py                              + etude_timeout_s (réglable)
src/labuse/api/modules.py                         processus séparé tuable (calcul & PDF), routes
frontend/src/lib/api.ts                           + messageEtudeErreur / etudeRelancable
frontend/src/components/outils/EtudeV6.tsx        message propre, relance via bouton Analyser
frontend/src/components/outils/M22Programme.tsx   message propre + Réessayer (503/panne), pas sur 400
tests/test_etude_async.py                         (nouveau) mécanique kill/no-ghost + same-numbers
docs/audit-2026-10/etude-async-1/RAPPORT.md       (ce document)
```
