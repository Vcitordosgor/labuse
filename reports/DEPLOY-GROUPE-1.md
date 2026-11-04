# DEPLOY-GROUPE-1 — mise en prod du groupe (JOHN-TAYLOR-2 · COPILOTE-5 · ECARTS-ZERO-1 · CARTE-TRAITS-1 · SILENCE-1)

Lancé le **2026-11-04** (soir, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`, VPS `vps-5563949c`). Go de Vic pour écrire en prod, dans les seules
limites du mandat. Mêmes règles que `reports/DEPLOY-JOHN-COPILOTE4.md`. Périmètre : avancer la prod de
**`59ce629db`** (DEPLOY-JOHN-COPILOTE4) à **`7fa4d1b1c`** — c.-à-d. `main`, qui porte déjà les cinq
merges (`feat/john-taylor-2`, `fix/ecarts-zero-1`, `fix/carte-traits-1`, `fix/copilote-5`,
`fix/silence-1`) plus le straggler de test COPILOTE-5. Déploiement hors de la fenêtre 01 h–05 h
(q_v21 reprend à 02 h 00) : poussé à **~22 h 15**, tous les gestes prod finis **avant 01 h 00**.

---

## ★ Pour Vic — ce qui t'attend demain matin

> **Le résumé du matin (`resume-matin`, 07 h 30) partira en [INFO], pas en [URGENT].**
> Au moment du déploiement : **0 incident d'exploitation ouvert**, **0 job en échec**, les 4 sources
> veillées repassées « à jour », `/readyz` 200, served run **q_v20** inchangé. L'accueil de John le dit
> déjà mot pour mot : *« Bonjour Vic. Tout tourne : rien n'attend ta décision. »*
>
> **[INFO] et non [URGENT]** parce que le mail du matin se déclenche sur les incidents `ops_incidents`
> et les jobs en retard/échec — il n'y en a aucun. Les trois passes de nuit (injection-nuit 01 h,
> calcul-nuit 02 h **sous `PROMEUT=0`** — calcule + contrôle + mail, **pas de bascule**, coherence-banc
> 03 h 45) tournent comme d'habitude ; seul un échec de l'une d'elles ferait basculer le mail en
> [URGENT].
>
> **Deux choses à regarder (ni l'une ni l'autre n'est urgente ni nouvelle) :**
> 1. **Le Tableau de bord porte une carte rouge « 2 contrôles de sécurité échouent ».** C'est la vieille
>    histoire des **verrous** (`circuit_verrous`, cf. AUTONOMIE-2 / DEPLOY-AUTONOMIE-2) : 2 verrous
>    hors liste d'avertissement au dernier passage journalisé. **Pré-existant, pas introduit par ce
>    déploiement** ; réel (ça demande du code/ops, pas un clic). Pour voir lesquels : `labuse verrous`.
> 2. **La 1ʳᵉ promotion de q_v21 reste devant toi.** La gate `LABUSE_CALCUL_NUIT_PROMEUT=0` est
>    conservée : le calcul de nuit chiffre et contrôle q_v21 mais ne le sert pas. La bascule est ta
>    décision (carnet de John).
>
> **Bonne nouvelle visible au Tableau** : une carte grise *« Dernière restauration : vérifiée
> (2026-11-04) »* — le test de restauration de contrôle a tourné pour de vrai ce soir (§PROD P4).

---

## 0. Note de branche — « sur main »

`main` **est** la ligne de travail : elle porte les cinq merges par-dessus la base prod `59ce629db`.
La prod **ne suit pas `main` par git** : elle est déployée par **rsync de la copie de travail**
(`deploy_app.sh`) ; le SHA servi est écrit dans `config/deploiement.json`. Le HEAD servi est
**`7fa4d1b1c`**. Ce rapport est commité **sur `main`** et poussé sur `origin/main`.

Les cinq commits de tête vérifiés présents sur `main` avant déploiement :
`e25cf7e11` (JOHN-TAYLOR-2), `dd7c1c6c0` (ECARTS-ZERO-1), `7ac42dcea` (CARTE-TRAITS-1),
`d6d594130`+`08ce0de7e` (COPILOTE-5), `14a7e4db1` (SILENCE-1).

---

## 1. Étape 0 — pré-vol (garde-fou)

- **Fenêtre OK.** Déploiement à ~22 h 15 Réunion, hors de 01 h–05 h. Aucune sauvegarde / dump / rsync /
  passe Radar / calcul-nuit / injection en cours (`pgrep` à blanc). `/readyz` 200, `/healthz` 200,
  `NRestarts=0`. Disque **24 G libres / 75 %**. Sauvegarde < 24 h présente :
  `labuse-labuse-20261104-133003.dump` (6,5 Go, 13 h 48).
- Cible : prod **`59ce629db`** (ancêtre strict de `7fa4d1b1c`), served run **q_v20** (433 229 lignes).

### Filets (`cp -al`, hardlinks ≈ 0 octet — disque inchangé)
- `/opt/labuse/app` → **`app-avant-groupe1`** (inode partagé 4517014 vérifié sur `cli.py`).
- `/opt/labuse/venv` → **`venv-avant-groupe1`**.
- `/etc/labuse/labuse.env` → **`labuse.env.avant-groupe1`** (640 root:labuse) ;
  `/etc/caddy/Caddyfile` → **`Caddyfile.avant-groupe1`**.

---

## 2. Schéma — aucune migration requise (vérifié)

**Constat.** Diff `59ce629db..7fa4d1b1c` sur `src/**/*.py` : **0 `CREATE TABLE` / `ALTER TABLE` /
`ADD COLUMN` / `CREATE INDEX`** (grep à blanc). Les cinq lots ne touchent pas le schéma :
- **JOHN-TAYLOR-2** réutilise les 7 tables John posées par la migration tracée de DEPLOY-JOHN-COPILOTE4
  (les `ensure(db)` ajoutés sont des `CREATE TABLE IF NOT EXISTS` idempotents sur ces tables).
- **COPILOTE-5** (resolveur, couverture, routage, Opus) est en lecture.
- **ECARTS-ZERO-1** durcit le banc et corrige `tiles.py` à la source (matérialisation, pas DDL).
- **CARTE-TRAITS-1** est côté front (`basemaps.ts`).
- **SILENCE-1** touche veille/incidents/oracle/sentinelle (code), pas de table neuve.

**Vérifié en prod** : les 7 tables `john_*` + `copilote_*` présentes et **owner = `labuse`**.
**→ Aucune migration à poser.**

---

## 3. Déploiement

`deploy/scripts/deploy_app.sh labuse-vps` : rsync copie de travail (état servi exclu du transfert),
venv + `requirements.lock`, import-smoke de la chaîne de démarrage **OK**, deps calcul-nuit **OK**,
front bâti sur le VPS, unit systemd AUTONOMIE-2, **crontab reposé == registre** (tz reunion, 0 écart),
`deploiement.json = 7fa4d1b1c`, `fiche_cache` vidé, restart, **`/readyz` 200 STABLE (25/25, 33
essais)**, réchauffage `fiche-commune-cache` détaché.

- **Served run q_v20 intact** (garde manifeste : 433 229 lignes en prod avant ET après).
- **`LABUSE_CALCUL_NUIT_PROMEUT=0` conservé** (présent avant/après) ; **`LABUSE_JOHN_PLAFOND_EUR=50`**
  déjà posé. Clé `ANTHROPIC_API_KEY` présente (jamais affichée).
- **`NRestarts=0`** après stabilisation. Réchauffage attendu jusqu'à sa fin (749 s, `ok`) **avant** le
  premier geste lourd — leçon du flap DEPLOY-JOHN-COPILOTE4 tenue (pas de contention de verrou).
- L'état servi (`served_run.txt` / `served_manifest.json`) est **exclu du rsync** : la modification
  locale de commentaire (self-heal SILENCE-1, run inchangé q_v20) n'est pas partie en prod.

---

## 4. Gestes prod (go Vic)

### 4.1 `build-mvt` — tuiles reconstruites ✓ (avec une réserve honnête sur un post-step)
`labuse build-mvt` sur le run servi **q_v20** : **`mvt_parcels` reconstruite = 433 229 parcelles**
(île entière), **committée**. C'est la cible du mandat (c'est sur ces tuiles que porte le correctif
SDP-tuile d'ECARTS-ZERO-1).

**Réserve (non bloquante).** `build-mvt` enchaîne un **post-step opportuniste** (rafraîchissement des
intersections de servitudes `parcel_couche_intersection`, quand `couche_intersection._inter_fraiche`
juge les sources changées). Ce rebuild a **buté sur sa toute première tranche** (parcelles id 1..4001)
pendant **~44 min à 80 % CPU sans produire de ligne** — plan de jointure spatiale pathologique
(géométrie communale très lourde / plan sous-optimal dans `couche_intersection.build`, **code
pré-existant, non touché par ce déploiement**). Pour protéger la fenêtre d'avant 02 h, j'ai **annulé
cette tranche** (`pg_cancel_backend`, geste réversible). **Aucun dégât** : la table servie
`parcel_couche_intersection` est **intacte** (le `RENAME` de bascule n'a jamais eu lieu ;
`serv_version` inchangée au 12/10), la table de staging vide a été droppée. **Cela n'affecte ni le banc
(tous les lecteurs lisent la même table live intacte) ni le correctif SDP-tuile (qui vit dans
`mvt_parcels` + `tiles.py`, pas dans les servitudes).**
→ **Dette** : rejouer le rafraîchissement des servitudes en fenêtre de maintenance, et instruire la
lenteur de la 1ʳᵉ tranche de `couche_intersection.build`.

### 4.2 Banc de cohérence complet — **0 écart, 0 toléré** ✓
`labuse jobs run coherence-banc` (le banc nocturne canonique, en-process) — **947 s, `ok`** :

| Volet | Résultat |
|---|---|
| **Banc île** (`coherence_runs`, mode `ile`) | **n_ecarts=0 · tolerable=0 · incoherent=0 · faux_client=0 · erreurs_lecteur=0** |
| Chasse (25 gardes) | 21 ok · 4 skip · **0 écart** · 0 nouveau |
| banc2 (867 invariants générés, mode nuit) | 863 ok · 3 skip · **1 écart** |

Le **153/87 → 0/0** d'ECARTS-ZERO-1 est atteint (avant déploiement, le dernier passage nocturne
montrait n_ecarts=**153**, tolerable=**87**). Le **1 écart banc2 est PRÉ-EXISTANT et stable** (`1 écart /
3 skip` à chaque passage depuis ≥ le 02/11, avant la base de ce déploiement) — réserve honnête, pas une
régression.

### 4.3 §PROD de SILENCE-1
| Point | Geste | Résultat |
|---|---|---|
| **P1** | `source-acquitter` × 3 | Annuaire / Population INSEE / Zones EnR OFB → **`ok`** (les 3 cartes « nouvelle version » disparaissent). |
| **P5** | `seed-sources` (130 sources) + reprobe BODACC `sentinelle.passer(forcer)` | BODACC repasse **`ok`, échecs 0** (endpoint `/records` re-semé ; était `illisible`, 3 échecs). |
| **P6** | `ops_alertes.resoudre` × 2 | **`verite-sources`** + **`escalade:ancien:verite-sources`** résolus (incident de 20 j fermé). |
| **P4** | restauration de contrôle, base à part | **restauration RÉELLE** dans `labuse_restore_ctrl` : **323 tables, 434 582 parcelles, 556 s**, base jetable droppée. Marqueur `.restore-test.json` écrit (`ok`), **incident `restore-test-ancien` résolu**. |
| **P4b** | `john-veille` (plafond 50 €) | **`ok` en 15 s**, `pause:false`, `n_items:0` (rien de neuf à signaler). Coût du mois John : **5,41 € / 50 €**. |

> **Note P4 — pourquoi la restauration a été jouée « à la main » (en superuser `postgres`).** Le job
> `restore-test` en mode réel (`LABUSE_RESTORE_TEST_REEL=1`) délègue à `restore_test_base.sh`, qui crée
> la base jetable et l'extension PostGIS **en `postgres`** ; or le `.pgpass` du rôle applicatif `labuse`
> ne porte **que** l'entrée `labuse` (pas `postgres`), et `CREATE EXTENSION postgis` exige un superuser.
> Lancé tel quel sous `labuse`, le job aurait écrit un marqueur **KO**. J'ai donc joué la restauration
> réelle **en `postgres`** (auth peer, qui fonctionne), puis **enregistré le résultat par le chemin
> sanctionné** (`_ecrire_marqueur_restore`) et résolu l'incident. Le mandat (« test de restauration
> dans une base à part et l'enregistrer ») est rempli **pour de vrai**. *Dette : donner au job de quoi
> s'authentifier en superuser sur le VPS, ou lui passer un rôle `createdb`+PostGIS-capable.*

### 4.4 Incident transitoire (ouvert et refermé par moi)
La restauration réelle (base de 6 Go) a fait franchir **transitoirement** 85 % à `/` (pic à 94,7 %), ce
qui a ouvert l'incident `disque` au `healthcheck` de 00 h 15 — **exactement ce que la garde 4× du job
prévient**. Base jetable droppée, disque **revenu à 75 %** ; `healthcheck` relancé → disque re-mesuré <
seuil → **incident résolu**. **`✓ aucun incident ouvert`** après coup.

---

## 5. Fumée (les points du mandat)

Lecture **en-process authentifiée** (TestClient FastAPI + session banc signée = admin de fait), le même
chemin que le banc — pas d'API publique, auth active. (Réserve, comme DEPLOY-JOHN-COPILOTE4 : le rendu
**client dans un navigateur** exige la 2FA nominative de Vic ; pas de compte client partagé depuis
POST-DEPLOY-1. Les correctifs front sont vérifiés dans le **bundle bâti déployé**.)

### Tableau de bord — « une carte = une vraie décision »
`GET /admin/circuit` → **200**. **2 cartes** :
1. *« Dernière restauration : vérifiée (2026-11-04) »* (gris) — reflet honnête du test P4 de ce soir.
2. *« 2 contrôles de sécurité échouent »* (rouge) — les **verrous cassés** (pré-existant, réel, cf. §★).

**Les 3 cartes « source en nouvelle version » et les cartes `verite-sources` ont disparu** (sources
acquittées, incident résolu). **« Est-ce que tout tourne ? »** : 35 postes · **29 vert · echec = 0** · 3
à l'arrêt (≠ échec) · 3 pas-encore-dû ; tuiles Livraisons / Contrôle-nuit / Courrier **vert**, Veille
des sources **ambre non bloquante** (miroirs Overpass hors-ligne, connu). **→ ne compte que les vrais
échecs : 0.** ✓

> **Bug trouvé ET corrigé pendant la fumée.** Mon marqueur `.restore-test.json` écrivait `tables=323`
> (un `int`, comme le fait le job réel sanctionné). Or `cockpit_resume._carte_restore_test` fait
> `(rt.get("tables") or {}).items()` — il attend un **dict** (format du marqueur Mac). Résultat :
> `/admin/circuit` (tout le Tableau) répondait **500** (`AttributeError: 'int' object has no attribute
> 'items'`). **Corrigé** en réécrivant le marqueur avec `tables=null` (le compte 323 reste dans le
> `message`) → Tableau de nouveau **200**. **C'est une incompatibilité LATENTE du produit** (le marqueur
> réel côté serveur = `tables:int` ferait planter le cockpit ; il ne s'est jamais déclenché parce que le
> job retombe toujours sur la lisibilité, `tables:null`). **Dette code** : tolérer `tables:int` dans
> `_carte_restore_test` (une ligne).

### John — page admin conversationnelle
- **Page depuis le rail admin** : bundle `AdminView-*.js` déployé, routes `/admin/john*` derrière
  `exiger_admin`. ✓
- **L'accueil parle** : `GET /admin/john` → *« Bonjour Vic. Tout tourne : rien n'attend ta décision. »*
  (`attentes:0`, 3 suggestions). Coût du mois affiché : **5,41 € / 50 €**, `en_pause:false`. ✓
- **Une question sourcée** : *« Quelle est la dernière sauvegarde et le dernier test de restauration ? »*
  → réponse **200**, `erreur:None`, **2 sources** (`lire_sauvegardes` / `lire_jobs`), cite le dump
  `labuse-labuse-20261104-133003.dump` 6 541,9 Mo. ✓
- **Une erreur rendue en phrase** : `chat` avec un `conversation_id` inexistant → **HTTP 200**, phrase
  (aucun 500, aucun identifiant technique). ✓

> **Réserve honnête (pas une régression).** Dans cette réponse, John dit aussi *« aucun test de
> restauration n'a encore tourné »* : son narratif lit le marqueur **`.copie-externe.json`** (flux Mac
> mensuel + copie hors-site), **pas** le `.restore-test.json` serveur que je viens d'écrire (c'est
> `ops_alertes` qui lit celui-là — d'où l'incident `restore-test-ancien` bien fermé). Deux notions de
> « test de restauration » cohabitent ; John parle de la Mac, qui n'a effectivement pas tourné. Nuance
> produit pré-existante.

### Copilote — l'app entière, points mauves
- **Points mauves** : accent `cp-ia` présent dans le bundle `AdminView-*.js` déployé. ✓
- **« Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La Montagne »** →
  **la fiche** de **`97411000BZ1065`** (intent `QUESTION`, `erreur:None`) : *« Parcelle 97411000BZ1065
  à Saint-Denis — Surface 1 567 m² · Zone PLU U · Pente 13,8° … »*. Le resolveur COPILOTE-5 a résolu
  l'adresse en parcelle. ✓
- **Question de risques = même valeur que l'écran** : Copilote → *« PPR inondation et mouvement de
  terrain — zone bleue sur 100 % de la parcelle : constructible SOUS PRESCRIPTIONS »*, **identique au
  mot près** à `fiche.aleas.liste[0].libelle` de `GET /parcels/97411000BZ1065` (même robinet). ✓
- **Question d'outil (Faisabilité) = même valeur que l'écran** : l'écran `GET /modules/faisabilite/{idu}`
  répond 200 (clés `capacite/bilan/prix_sortie/fiscal/rtaa`) ; Copilote donne **« Surface : 1 567 m² »**,
  la même surface que la fiche et l'Étude. ✓

### Carte — plus aucun trait de parcelle du fond IGN au zoom max
`basemaps.ts` déployé ligne 60 : `'bm-plan': { … maxzoom: 18 }` (commentaire CARTE-TRAITS-1) ; le bundle
bâti `index-*.js` contient `maxzoom:18`. Au z19 (zoom maximal) MapLibre n'affiche plus le parcellaire
du Plan IGN v2 (il ne sur-zoome plus au-delà de z18) → **un seul tracé de cadastre à l'écran (celui de
LABUSE)**. ✓ (vérifié dans l'artefact déployé ; rendu navigateur = réserve 2FA.)

### 10 minutes de journaux
Fenêtre de **30 min** sur le service final (`7fa4d1b1c`), journal systemd `labuse` : **0 Traceback /
Exception / ERROR / CRITICAL / 5xx / permission denied / lock timeout / heal failed / readyz 503**.
`/readyz` et `/healthz` **200**, **`NRestarts=0`**. (Le service a surtout journalisé des sondes
`/readyz`·`/health` : la fumée ci-dessus est passée **en-process**, elle n'a donc pas sollicité le port
servi — pas de pollution.) ✓

---

## 6. État final prod

Served run **q_v20** · SHA **`7fa4d1b1c`** · `NRestarts=0` · `/readyz` 200 stable · gate
`PROMEUT=0` · plafond John **50 €** · **0 incident d'exploitation ouvert**. **Filets conservés** :
`app-avant-groupe1`, `venv-avant-groupe1`, `Caddyfile.avant-groupe1`, `labuse.env.avant-groupe1` + dump
`labuse-labuse-20261104-133003.dump`. **Aucun retour arrière.**

---

## 7. Réserves honnêtes & dette

1. **Post-step servitudes de `build-mvt` annulé** (§4.1) — 1ʳᵉ tranche pathologique de
   `couche_intersection.build` (~44 min). Tuiles `mvt_parcels` OK ; servitudes live intactes. *Dette :
   rejouer le rafraîchissement en maintenance + instruire le plan de jointure.*
2. **Bug cockpit `_carte_restore_test`** (§5, Tableau) — intolérant à `tables:int` (marqueur réel
   serveur). Mitigé par `tables:null`. *Dette : une ligne dans `cockpit_resume.py`.*
3. **Job `restore-test` réel pas auto-suffisant sur le VPS** (§4.3 note P4) — pas de superuser dans le
   `.pgpass` de `labuse`. Joué en `postgres` à la main ce soir. *Dette : rôle/credential dédié.*
4. **1 écart banc2 pré-existant** (§4.2) — stable depuis ≥ 02/11, non lié à ce déploiement. À instruire.
5. **2 verrous cassés** (carte rouge Tableau) — pré-existant (saga verrous), réel, demande code/ops.
6. **Rendus navigateur** (Copilote mobile, carte, points mauves à l'écran) non re-rendus en prod (2FA
   nominative, pas de compte client partagé) — vérifiés dans le bundle déployé + recettes pré-merge.
7. **Crédit API Anthropic** : John + Copilote consomment Opus/Haiku ; John à 5,41 €/50 € ce mois.
8. **Dette de la Mac restore-test** : John lira « test de restauration OK » quand le flux Mac mensuel
   (`.copie-externe.json`) tournera ; indépendant du contrôle serveur joué ce soir.

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-groupe1  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-groupe1 /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-groupe1 /etc/labuse/labuse.env
sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload && sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Aucune donnée client touchée. Les tuiles mvt_parcels restent reconstruites (inoffensif).
```
