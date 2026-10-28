# DEPLOY-1028c — `fix/donnees-etat-fix-2` : **déjà en production, aucun geste prod**

Lancé le 28/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps`.
Périmètre demandé : mise en prod du seul correctif `fix/donnees-etat-fix-2` — commit `1dd03ee17`
(« la bascule ne lance plus de recalcul détaché »), mergé dans `main` par `29c3d3e60`
(« Merge branch 'fix/donnees-etat-fix-2' »), sans déclencher aucune bascule de run.

Mêmes règles que `reports/DEPLOY-1028b.md` : sauvegarde, `deploy_app.sh`, doctor vert, retour arrière prêt.

## Verdict : **RIEN À DÉPLOYER** — le correctif est déjà live en prod

Vérification faite **avant** tout geste : le code que ce mandat demande de pousser **tourne déjà en
production**. Il a été expédié plus tôt aujourd'hui par **DEPLOY-1028b** (déploiement de `main` entier,
code == `5810551f3`, marqueur prod `18e5c6a8` posé le **2026-10-28T13:23:29Z**). Le commit `1dd03ee17`
nommé par le mandat est le **deuxième parent** du merge `29c3d3e60` — un **re-merge** d'un correctif déjà
présent : son jumeau `7850374f3` (même message, même diff sur `src/labuse/bascule_flux.py`) était déjà
dans `5810551f3`.

Conformément aux règles d'exploitation (un geste prod outward-facing/irréversible ne se fait pas quand le
constat contredit l'énoncé), **aucun déploiement, aucun restart, aucune bascule, aucune sauvegarde** n'a
été exécuté. Prod est restée intacte et saine. Décision validée en séance (Vic) : **ne pas redéployer**,
sous réserve d'apporter au rapport les deux preuves ci-dessous.

---

## Preuve 1 — le delta code/config/front/deploy entre le code servi et `main` est **VIDE**

Le code servi en prod == `5810551f3` (cf. DEPLOY-1028b : `docs/` est exclu du rsync ; marqueur `18e5c6a8`
dont le code est identique octet pour octet à `5810551f3`). Diff vers le tip de `main` `29c3d3e60` :

```
$ git diff --stat 5810551f3 29c3d3e60 -- src/ deploy/ frontend/ config/
$            # (aucune sortie — exit 0)
```

**Vide.** Le seul delta `5810551f3 → 29c3d3e60` sur tout l'arbre est de la **documentation** :

```
$ git diff --stat 5810551f3 29c3d3e60
 docs/audit-2026-10/donnees-etat-2/CE-QUI-SE-PASSE.md        |  91 +++
 docs/audit-2026-10/donnees-etat-2/ECARTS.md                 |  29 ++
 docs/audit-2026-10/radar-etat-1/CE-QUI-SE-PASSE-RADAR.md    | 129 +++
 docs/audit-2026-10/radar-etat-1/ECARTS.md                   |  26 ++
 docs/audit-2026-10/radar-etat-1/RELANCE.md                  |  20 ++
 5 files changed, 295 insertions(+)
```

Donc `deploy_app.sh` rsyncerait un arbre de code **identique** (docs exclus de toute façon) ; le seul
effet matériel serait d'avancer le marqueur `deploiement.json` et d'imposer un restart à froid — pour
**zéro changement de code**, au prix du flap `/readyz` documenté en 1028b. Sans objet.

## Preuve 2 — `src/labuse/bascule_flux.py` en prod est **identique** à celui de `main`

```
main  (29c3d3e60)  sha256 = a5ae68a925ecfd3529b61c2fc929c6adaa1fd43737e486833d345ac9107d341e   (37844 octets)
          == 5810551f3  sha256 = a5ae68a925ecfd3529b61c2fc929c6adaa1fd43737e486833d345ac9107d341e
PROD  /opt/labuse/app/src/labuse/bascule_flux.py
                     sha256 = a5ae68a925ecfd3529b61c2fc929c6adaa1fd43737e486833d345ac9107d341e   (37844 octets)
```

**MATCH exact** (même sha256, même taille). Le correctif est visible à la lecture directe du fichier
prod — `bascule_flux.py:505` :

> `DONNEES-ETAT-FIX-2 (correctif) — on NE spawn PLUS de `labuse rebuild` détaché ici : ce sous-processus`
> `héritait de `LABUSE_DATABASE_URL`… Le rafraîchi des caches reste porté par la purge ci-dessus + le`
> `build-mvt détaché existant.`

C'est exactement le comportement voulu par `1dd03ee17` : **la bascule ne lance plus de recalcul détaché.**

---

## État prod constaté (lecture seule, aucun geste)

| Contrôle | Valeur |
|---|---|
| Service `labuse` | **active** |
| `/readyz` (local) | **200** |
| Marqueur `config/deploiement.json` | `sha = 18e5c6a8…`, déployé **2026-10-28T13:23:29Z** (= DEPLOY-1028b) |
| `config/served_manifest.json` | scoring **q_v20** · cascade **q_v19_sources** · mvt **q_v20** · division **q_v19** · résiduel_seq **17** (inchangé) |
| `config/served_run.txt` | **q_v20** |
| `bascule_flux.py` prod vs main | **sha256 identique** (Preuve 2) |

Aucune bascule, aucun run, aucune migration : conforme au « ne déclenche aucune bascule de run ».

---

## Note pour un mandat suivant — correctif **durable** du blocage du heal (vu en 1028b)

Le mandat 1028c demandait, pour éviter le blocage du heal observé en 1028b, de **redémarrer à froid,
attendre `/readyz` 200 stable (25/25), puis seulement lancer le réchauffage**. Ici **aucun restart n'a été
nécessaire** (rien à déployer, prod déjà à 200). La séquence « restart froid → attendre readyz → réchauffer »
reste la bonne **parade opérationnelle** et correspond exactement à la piste (b) ci-dessous. Pour fiabiliser
durablement (hors mandat), le code appelle deux corrections ciblées :

**Racine du flap (rappel 1028b).** Au boot, le heal de schéma par-worker (`pige` → `ALTER TABLE pige_biens
ADD COLUMN IF NOT EXISTS retiree_le`) peut entrer en conflit de verrous avec le gros job
`fiche-commune-cache` lancé par `deploy_app.sh` **étape 6** autour du restart. Or `_run_heal_steps`
(`src/labuse/api/app.py:91`) exécute chaque step **sans `lock_timeout` et sans nouvel essai** : un simple
conflit de verrous **transitoire** devient un `heal_failed` **définitif** → le worker renvoie `/readyz` 503
(honnête : `app.state.schema_heal`, FIX-GB-011, `app.py:921-929`) → flap ~40 % tant qu'on ne redémarre pas.

**(a) `lock_timeout` court + nouvel essai sur les steps DDL du heal.** Encapsuler les steps (au moins ceux
qui font du DDL, dont `pige`) avec `SET lock_timeout = '…s'` et **1–2 retries** bornés, pour qu'un conflit
de verrous passager **échoue vite puis réussisse au ré-essai** au lieu de devenir un échec permanent.
L'idiome existe déjà dans le dépôt — à réutiliser : `cli.py:1383` / `cli.py:1517` (`SET lock_timeout='30s'`),
`couche_intersection.py:98-157` (`'5s'`), `fraicheur_caches.py:417`. C'est le correctif de fond.

**(b) Ne lancer le job d'étape 6 qu'APRÈS le `start` + heal convergé.** Dans `deploy/scripts/deploy_app.sh`
(étape 6, l.154-165), différer le `labuse jobs run fiche-commune-cache` jusqu'à ce que le service soit
redémarré et que `/readyz` soit 200 stable — pour que le gros job et le heil DDL ne se disputent jamais les
verrous. C'est la parade que 1028c demandait d'appliquer manuellement ; la graver dans le script la rend
systématique.

**(c) Fallback déjà adopté.** À défaut de (a)/(b), le **restart propre à froid** (système idle, job terminé)
en fin de déploiement reste le geste documenté qui ramène `/readyz` à 200 stable (fait et prouvé en 1028b).

---

## Synthèse

**Aucun déploiement 1028c.** Le correctif `fix/donnees-etat-fix-2` (`1dd03ee17`, re-merge `29c3d3e60`) est
**déjà en production** depuis DEPLOY-1028b (marqueur `18e5c6a8`, 2026-10-28T13:23:29Z). Prouvé par :
(1) `git diff --stat 5810551f3 29c3d3e60 -- src/ deploy/ frontend/ config/` **vide** ; (2) `bascule_flux.py`
prod **sha256-identique** à `main`. Prod saine et inchangée : `/readyz` 200, service active, servi **q_v20**
(manifeste intact). Aucune sauvegarde, aucun restart, aucune bascule n'a été nécessaire — donc aucun retour
arrière à prévoir. Correctif durable du heal (lock_timeout+retry, ou réchauffage après démarrage) noté
ci-dessus pour un mandat suivant.
