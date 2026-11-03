# DEPLOY-TABLEAU-1 — mise en prod de TABLEAU-1 (`3ec35e7bf` → `fcd545595`)

Lancé le **2026-11-03** (soir, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`, VPS `vps-5563949c`). Go de Vic pour écrire en prod, dans les seules
limites du mandat. Mêmes règles que `reports/DEPLOY-OPS-NUIT-2.md`. Périmètre : avancer la prod de
**`3ec35e7bf`** (OPS-NUIT-2, déployé ce soir 20:56) à **`fcd545595`** (merge de `fix/tableau-1` dans
`fix/ops-nuit-1` — TABLEAU-1 : le tableau ne montre que les vraies décisions), puis appliquer les deux
décisions de Vic (retrait BDNB, injection FRR). À lire d'abord :
`docs/audit-2026-11/tableau-1/COMPTE-RENDU.md`.

> **Bilan en une ligne.** Code TABLEAU-1 déployé et vert sur `fcd545595` ; **`/readyz` 200 stable
> 25/25, `NRestarts=0`**, unit AUTONOMIE-2 (heal `ExecStartPre`, workers `SKIP_BOOT_HEAL=1`) et gate
> `LABUSE_CALCUL_NUIT_PROMEUT=0` conservés, served run **q_v20** intact. **Décisions de Vic appliquées** :
> **BDNB retirée** (statut `retiree`, veille désactivée → plus de sonde ni de carte) ; **FRR ex-ZRR
> injectée** par sa commande du registre (`dispositifs-build`), contrôlée (23 aplats, géométries
> valides, 974 à 100 %) et vérifiée sur la fiche de Salazie (« commune classée en totalité »). **La
> liste « à injecter » est vide** (l'incident obsolète « 2 sources structurantes » refermé). **Aucun
> retour arrière.** Deux réserves honnêtes au §3 (3 sondes Overpass en panne amont réelle ;
> 1 avertissement de réchauffage, sans conséquence).

---

## 0. Note de branche — « sur main » vs la réalité servie

Le mandat dit « sur main ». La prod **ne suit pas `main`** : elle est déployée par **rsync de la copie
de travail** (le VPS n'a pas de git). `main` (`ddb266041`) est en retard de quatre commits ; **basculer
sur `main` ferait RÉGRESSER la prod** (perte d'OPS-NUIT-1, OPS-NUIT-2 ET TABLEAU-1). Le code déployé est
donc le HEAD courant **`fcd545595`** (`fix/ops-nuit-1` avec `fix/ops-nuit-2` puis `fix/tableau-1`
mergés, poussé sur `origin/fix/ops-nuit-1`). Le **merge `fix/ops-nuit-1` → `main` par PR reste la
dette** (push direct sur `main` gardé par le harnais), indépendante de ce déploiement.

---

## 1. Étape 0 — pré-vol (garde-fou)

- **~22 h 29 Réunion** (`TZ=Indian/Reunion`). Go de Vic en direct.
- **Aucune sauvegarde / dump / rsync / passe Radar / calcul-nuit / injection / flux-run en cours**
  (`pgrep` : rien). **0 VACUUM** (hors self), **0 backend client non-idle**.
- **Sauvegarde < 24 h** : `GARDE-labuse-labuse-20261103-133003.dump` **6 559,8 Mo**, âge ~9 h (dump du
  midi, terminé). `/readyz` 200, `NRestarts=0`, disque **32 G libres / 67 %**.
- **Cible** : HEAD local == `origin/fix/ops-nuit-1` == **`fcd545595`** ; prod **`3ec35e7bf`** (confirmé
  `config/deploiement.json`), ancêtre strict ; served run **q_v20**.

### Filets (`cp -al`, hardlinks ≈ 0 octet — disque inchangé, 32 G avant/après)
- `/opt/labuse/app` → **`app-avant-tableau1`** (inode partagé 4517014 vérifié sur `cli.py`).
- `/opt/labuse/venv` → **`venv-avant-tableau1`**.
- `/etc/caddy/Caddyfile` → **`Caddyfile.avant-tableau1`** ; `/etc/labuse/labuse.env` →
  **`labuse.env.avant-tableau1`** (640 root:labuse préservé).

### Environnement & schéma — inchangés
`LABUSE_CALCUL_NUIT_PROMEUT=0` **présent avant ET après** (vérifié `sudo grep`). `SKIP_BOOT_HEAL=1`
vit dans le unit systemd (AUTONOMIE-2). `deploy_app.sh` n'expédie PAS `labuse.env` (exclu du rsync) →
gate intouchée. **TABLEAU-1 ne pose aucune migration** (config/code + données existantes).

---

## 2. Déploiement — `deploy/scripts/deploy_app.sh labuse-vps`

Déroulé **exit 0** (1 min 30) : garde manifeste (q_v20 présent, **433 229 l. score_labuse**) ✓ → rsync →
venv (chaîne importable ✓) → **2bis deps calcul-nuit** (pandas/numpy/joblib/sklearn ✓) → front (vite sur
VPS) → systemd (unit AUTONOMIE-2 reposé) → crontab reposé **== registre** (tz=reunion, 0 écart) →
`config/deploiement.json = fcd545595e06` → manifeste prod **q_v20** (433 229 l.) intact → `fiche_cache`
vidé → restart → **`/readyz` 200 STABLE 25/25 (33 essais)** → réchauffage détaché.

### Unit vérifié actif (AUTONOMIE-2 conservé)
`systemctl cat labuse` : **`ExecStartPre=/opt/labuse/venv/bin/labuse schema-heal`**,
**`Environment=LABUSE_SKIP_BOOT_HEAL=1`**, `TimeoutStartSec=180`. Journal du redémarrage :
`✓ heal schéma OK (18 steps, en série, hors service)` à 22:42:52, puis 5 workers
`heal schéma : joué AVANT le port — worker ne touche pas au schéma`. **`NRestarts=0`**, `/readyz` 200.

---

## 3. Décisions de Vic (appliquées APRÈS le déploiement)

### 3.1 BDNB — retirée des sources
Constat prod : BDNB (`data_sources` id 89) était **déjà `status=retiree`** (`retiree_le` 2026-09-07,
donc déjà hors vitrine et hors cartes — `WHERE_AFFICHEES` l'exclut), mais **sa veille était encore
ACTIVE** (`source_veille` id 66, `actif=true`, `dernier_statut='nouvelle_version'` sur l'export amont
`2026-02-b` du 2026-10-05) : elle continuait d'être **sondée** chaque nuit (`sonde-sources` 07:00) et de
**compter** comme « source B à injecter » pour `injection-nuit`.

Appliqué (transaction, prod) :
- `data_sources` : `status='retiree'`, `retiree_le` conservé, **`retiree_raison` = le motif de Vic**
  (« aucun chiffre servi n'en dépend — emprise = max BD TOPO/CoSIA, hauteur = BD TOPO, tables `bdnb_*`
  absentes ; couverture 974 non prouvée — amont France `2026-02-b`, DROM annoncé « en développement » ;
  plus aucune sonde ni carte »).
- `source_veille` : **`actif=false`** (plus jamais sondée par `sonde-sources`) + `dernier_statut='ok'`
  (pour qu'une source retirée ne soit plus comptée « B en attente d'injection »).

**Résultat** : plus aucune sonde ni carte pour BDNB (vérifié §4). Aucun `DROP` : les tables `bdnb_*`
restent absentes comme avant ; **0 chiffre servi changé** (c'était déjà le cas).

### 3.2 FRR ex-ZRR — injectée maintenant
Commande du registre (`config/sources_ingestion.yaml`, label `frr_ex_zrr`) = **`labuse
dispositifs-build`** ; sa donnée amont vit dans le seed versionné `data/fiscal/territoire_fiscal.csv`
(chargé par `labuse territoire-fiscal`). Les deux lancés en prod (`labuse`, env chargé, cwd
`/opt/labuse/app`), idempotents :

```
✓ territoire fiscal (ZFANG/FRR) : {'communes': 24, 'zfang_renforcees': 6}
dispositifs : QPV 57 · ANRU 8 · TVA(500m) 13 · ZFANG 24 · FRR 23
```

**Contrôles (tous verts)** :
- **Comptes** : 24 communes au référentiel (3 `totalite`, 20 `partie`, 1 `hors`) ; **23 aplats FRR**
  dessinés (`totalite`+`partie` ; « hors » ne se peint pas, c'est l'absence).
- **Géométries** : **23/23 valides** (`ST_IsValid`), SRID **4326** unique, **23/23** avec `geom_2975`
  posé par le trigger.
- **Couverture 974** : **23/23** communes en `insee` `974xxx`, **0 hors 974**.
- **Fiche d'une commune classée FRR** : **Salazie** (97421, `totalite`) →
  *« Commune classée en totalité (zone spéciale d'action rurale — décret n° 78-690 ; FRR depuis le
  1ᵉʳ juillet 2024). »* Témoin « partie » (Les Avirons 97401) → `frr_position` = `None` → libellé
  *« position non déterminée »* (conforme : la ZSAR « les Hauts » est infra-communale, l'aplat servi est
  commune-entière — pas de contour parcellable, par construction).

**Acquittement de la veille (pour vider la carte « à injecter »)** : la veille FRR
(`source_veille` id 101, `methode='agent'`) voyait `Arrêté du 14 avril 2025` plus récent que le servi
(`réf. ZRR 2017`). Vic ayant décidé d'injecter, la veille passe `dernier_statut='ok'` avec la trace du
geste (`injection_lancee_at=now()`, `injection_vu='Arrêté du 14 avril 2025'`) — l'équivalent serveur du
bouton « Injecter cette version ». **La donnée servie et le millésime affiché au client restent
inchangés** (`réf. ZRR 2017`, la délimitation ZSAR 1978 ne bouge pas) : seul l'état de veille admin est
acquitté. *(Réserve honnête, §5-dette : la veille IA repasse tous les 15 j le dimanche ; comme la
commande d'ingestion FRR écrit un millésime FIXE, l'agent pourrait re-signaler ce même arrêté tant que
l'effet du texte 2025 sur La Réunion n'est pas tranché et nommé dans le millésime servi — décision/
donnée, pas ce déploiement.)*

---

## 4. Fumée (les 6 points du mandat)

| Point du mandat | Résultat |
|---|---|
| **Le tableau ne montre que les décisions humaines + « à valider » vide** | ✅ `/admin/circuit` : **aucune action `injecter`** (balayage récursif). `a_faire.lignes` = 2 vraies décisions (**Calculer le score**, **Déposer VRD/SPANC**), **aucune carte « Injecter »**. L'incident obsolète **« 2 source(s) structurante(s) à injecter »** (FRR+BDNB) a été **refermé** (`ops_alertes.resoudre` : 0 source B en `nouvelle_version` après les 2 décisions). Le reste de « Qu'est-ce que je dois faire » = incidents **légitimes pré-existants** (calcul-nuit échoué d'hier, `verite-sources` 3 écarts risques, `restore-test` ancien, couches MVT en retard, **87 petits écarts** = acceptation-avec-raison TABLEAU-1, 1 source manuelle SPANC). |
| **Plus de « à l'arrêt » pour un job pas encore dû** | ✅ `/admin/usine` résumé : **34 postes · 26 vert · 1 échec · 3 à l'arrêt · 4 pas encore dûs** — `pas_encore_du` est un **bucket distinct** d'`arret` (`cockpit_resume:526` : planifié + jamais parti + échéance non venue → « pas encore dû », jamais « à l'arrêt »). |
| **Mise à jour sans bouton pour ce qui tourne la nuit** | ✅ `cockpit.mise_a_jour` : 4 étapes (Injecter / Calculer / Promotion / Envoyer en prod), **`bouton=null` partout**. **Aucun « Calcul lancé sur le Mac » ni « se fait depuis le Mac »** dans les charges utiles `/admin/circuit` et `/admin/cockpit/etat-prod` (la seule occurrence « Mac » du cockpit est le détail de l'incident `restore-test`, pré-existant et légitime). |
| **injection-nuit armé avec les commandes des sources A** | ✅ les **4 sources de classe A** en nouvelle version résolvent leur commande (dry `_relance_pour`) : Annuaire→`ingest-annuaire-services`, Population légale→`population-legale-sync`, SUP GPU→`ingest-sup`, OFB/APER→`enr-exclue-toiture-build`. `injection-nuit` armé **01:00** (crontab tz Réunion). |
| **Les 6 sondes vertes ou en grâce** | ⚠️ **3/6 vertes** après re-sonde avec le code déployé : **OCS GE** (`ok`, empreinte atom), **SIS** (`ok`, Content-Length 8151737), **SCOT GPU** (`ok`, 2024-09-17) — le recâblage TABLEAU-1 **prouvé en direct**. **3/6 Overpass** (Parkings OSM, OSM transport, TCSP) **injoignables** : `overpass-api.de` répond mais ne sert pas la requête 974 (saturé), **et les 2 miroirs `kumi.systems`/`private.coffee` sont hors-ligne** (HTTP 000) au moment du contrôle → panne amont réelle (echecs 12-14, > fenêtre de grâce 7 j). Elles rendent une **tuile ambre non bloquante « Veille des sources » ("3 amont ne répondent plus")**, **jamais une carte de décision** — donnée servie intacte (doctrine : une sonde en panne n'a jamais rendu la donnée fausse). Elles repasseront vertes seules dès qu'un endpoint Overpass répondra (le repli miroir est déployé). |
| **10 min de journaux propres** | ✅ pour le service : **0 5xx, 0 heal échoué, 0 erreur de service**, `/health` & `/readyz` **200**, `NRestarts=0`. ⚠️ **un seul avertissement de fond** (`labuse.rechauffage`) : le réchauffage post-déploiement a recalculé **24/24 communes en 767 s**, puis le `pg_advisory_unlock` final a buté sur l'`idle-in-transaction timeout` (120 s). **Sans conséquence** : les 24 communes sont calculées, la connexion terminée a **libéré le verrou** (0 verrou advisory résiduel, 0 connexion idle-in-transaction), service 200 / `NRestarts=0`. *(Même famille idle-tx qu'OPS-NUIT-1 — dette §5.)* |

---

## 5. État final prod

Served run **q_v20** · SHA **`fcd545595`** · `NRestarts=0` · `/readyz` 200 stable · gate
`PROMEUT=0`. **Filets conservés** : `app-avant-tableau1`, `venv-avant-tableau1`,
`Caddyfile.avant-tableau1`, `labuse.env.avant-tableau1` + dump `GARDE-…-20261103-133003.dump`.
**Aucun retour arrière.**

### Pour Vic — l'écart C13 (TVA financier), en une phrase
**L'écart C13 n'est pas un bug** : `regime_tva_saisi` ne décide que **HT vs TTC** (pas le taux), et le
8,5 %↔2,1 % (locatif social) passe correctement par `part_sociale_pct` avec le bon libellé —
**aucune décision requise**, sauf si tu veux un vrai **sélecteur de taux par régime**, auquel cas c'est
un correctif à spécifier (et non un bug à corriger).

### Dette / suites
1. **Merge `fix/ops-nuit-1` → `main` par PR** (OPS-NUIT-1 + OPS-NUIT-2 + TABLEAU-1), puis la prod suit —
   push direct sur `main` gardé par le harnais, indépendant de ce déploiement.
2. **Veille FRR (IA, 15 j dim)** : la commande d'ingestion FRR écrit un millésime FIXE ; pour que
   l'agent ne re-signale pas l'`Arrêté du 14 avril 2025` déjà acquitté, soit confirmer qu'il ne change
   rien au classement 974 et **avancer le millésime servi** pour le nommer, soit apprendre à l'agent à
   respecter `injection_vu`. **Décision/donnée de Vic**, pas ce déploiement.
3. **Réchauffage idle-tx** : `labuse.rechauffage` tient une session ouverte pendant le recalcul long
   (767 s) → `pg_advisory_unlock` bute sur le timeout 120 s. À traiter comme OPS-NUIT-1 l'a fait pour
   `calcul-nuit` (sessions courtes, verrou relâché hors transaction longue). Sans impact aujourd'hui.
4. **Overpass** : les 3 sondes reviendront vertes seules quand un endpoint répondra ; si la panne dure,
   brancher d'autres miroirs (les 2 actuels, `kumi.systems`/`private.coffee`, étaient hors-ligne).
5. **Retirer les filets `*-avant-tableau1` + hardlinks `GARDE-`** après un cycle sain.

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-tableau1  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-tableau1 /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-tableau1 /etc/labuse/labuse.env
sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload && sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma inchangé (aucune migration). Les 2 décisions de Vic (BDNB retiree, FRR injectée/acquittée) sont
# des écritures DE DONNÉES indépendantes du code : un recul de code ne les défait pas (et c'est voulu).
```
